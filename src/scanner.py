"""Email scanning and filtering module."""

import base64
import email.utils
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime

from src.body_code_extractor import extract_code_from_body
from src.config import (
    GMAIL_MAX_RESULTS,
    build_body_search_queries,
    build_filename_queries,
    matches_programming_extension,
)

logger = logging.getLogger(__name__)


@dataclass
class Attachment:
    """Represents a matching email attachment."""
    filename: str
    attachment_id: str
    message_id: str
    size: int = 0
    is_body_extract: bool = False
    body_code: str = ""


@dataclass
class EmailMessage:
    """Represents an email with programming attachments."""
    message_id: str
    thread_id: str
    subject: str = ""
    sender: str = ""
    recipients: str = ""
    date: str = ""
    date_parsed: datetime | None = None
    body: str = ""
    attachments: list[Attachment] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "thread_id": self.thread_id,
            "subject": self.subject,
            "sender": self.sender,
            "recipients": self.recipients,
            "date": self.date,
            "body": self.body,
            "labels": self.labels,
            "attachments": [
                {
                    "filename": a.filename,
                    "attachment_id": a.attachment_id,
                    "size": a.size,
                    "is_body_extract": a.is_body_extract,
                }
                for a in self.attachments
            ],
        }


def _get_header(headers: list[dict], name: str) -> str:
    """Extract a header value by name."""
    for h in headers:
        if h["name"].lower() == name.lower():
            return h.get("value", "")
    return ""


def _extract_body(payload: dict) -> str:
    """Extract plain text body from message payload."""
    # Direct body
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    # Multipart — recurse into parts
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

    # Nested multipart
    for part in parts:
        if part.get("mimeType", "").startswith("multipart/"):
            result = _extract_body(part)
            if result:
                return result

    return ""


def _extract_attachments(payload: dict, message_id: str) -> list[Attachment]:
    """Extract attachment info from message payload."""
    attachments = []

    def _walk_parts(parts):
        for part in parts:
            filename = part.get("filename", "")
            body = part.get("body", {})
            if filename and body.get("attachmentId"):
                if matches_programming_extension(filename):
                    attachments.append(Attachment(
                        filename=filename,
                        attachment_id=body["attachmentId"],
                        message_id=message_id,
                        size=body.get("size", 0),
                    ))
            # Recurse into nested parts
            if part.get("parts"):
                _walk_parts(part["parts"])

    if payload.get("parts"):
        _walk_parts(payload["parts"])
    elif payload.get("filename") and payload.get("body", {}).get("attachmentId"):
        filename = payload["filename"]
        body = payload["body"]
        if matches_programming_extension(filename):
            attachments.append(Attachment(
                filename=filename,
                attachment_id=body["attachmentId"],
                message_id=message_id,
                size=body.get("size", 0),
            ))

    return attachments


def _list_messages_for_query(service, query: str, label: str | None = None) -> list[dict]:
    """List all message stubs matching a single Gmail query."""
    message_ids = []
    page_token = None

    while True:
        kwargs = {
            "userId": "me",
            "q": query,
            "maxResults": GMAIL_MAX_RESULTS,
        }
        if label:
            kwargs["labelIds"] = [label]
        if page_token:
            kwargs["pageToken"] = page_token

        response = service.users().messages().list(**kwargs).execute()
        messages = response.get("messages", [])
        message_ids.extend(messages)

        page_token = response.get("nextPageToken")
        if not page_token:
            break

        time.sleep(0.1)  # Light rate limiting

    return message_ids


def scan_emails(service, label: str | None = None, progress_callback=None) -> list[EmailMessage]:
    """
    Scan Gmail for all emails with programming-related attachments.

    Uses Gmail's filename: search operator for server-side filtering
    instead of downloading every email with any attachment.

    Args:
        service: Authenticated Gmail API service
        label: Optional label to filter (e.g. "INBOX")
        progress_callback: Optional callable(scanned, found) for progress updates

    Returns:
        List of EmailMessage objects with matching attachments
    """
    results = []
    queries = build_filename_queries()

    # Search with filename: queries (batched to stay under query length limit)
    seen_ids = set()
    message_ids = []

    logger.info(f"Searching for code attachments ({len(queries)} query batch(es))...")
    for qi, query in enumerate(queries):
        logger.info(f"  Batch {qi + 1}/{len(queries)}: {query[:80]}...")
        batch_msgs = _list_messages_for_query(service, query, label)
        for msg_stub in batch_msgs:
            if msg_stub["id"] not in seen_ids:
                seen_ids.add(msg_stub["id"])
                message_ids.append(msg_stub)
        logger.info(f"  {len(message_ids)} unique messages so far")

    # Search for code keywords in email bodies
    body_queries = build_body_search_queries()
    logger.info(f"Searching for code in email bodies ({len(body_queries)} query batch(es))...")
    for qi, query in enumerate(body_queries):
        logger.info(f"  Body batch {qi + 1}/{len(body_queries)}: {query[:80]}...")
        batch_msgs = _list_messages_for_query(service, query, label)
        for msg_stub in batch_msgs:
            if msg_stub["id"] not in seen_ids:
                seen_ids.add(msg_stub["id"])
                message_ids.append(msg_stub)
        logger.info(f"  {len(message_ids)} unique messages so far (including body matches)")

    total = len(message_ids)
    logger.info(f"Found {total} candidate emails. Fetching details...")

    # Fetch full message details
    for i, msg_stub in enumerate(message_ids):
        msg_id = msg_stub["id"]

        try:
            msg = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to fetch message {msg_id}: {e}")
            continue

        payload = msg.get("payload", {})
        headers = payload.get("headers", [])

        # Extract file attachments (still filter client-side for exact extension match)
        attachments = _extract_attachments(payload, msg_id)

        # Extract code from email body
        body_text = _extract_body(payload)
        body_extracts = extract_code_from_body(body_text)
        for extract in body_extracts:
            attachments.append(Attachment(
                filename=extract["filename"],
                attachment_id="",
                message_id=msg_id,
                size=len(extract["code"]),
                is_body_extract=True,
                body_code=extract["code"],
            ))

        # Skip emails with no attachments and no body code
        if not attachments:
            if progress_callback:
                progress_callback(i + 1, len(results))
            continue

        # Parse date
        date_str = _get_header(headers, "Date")
        date_parsed = None
        if date_str:
            try:
                parsed = email.utils.parsedate_to_datetime(date_str)
                date_parsed = parsed
            except Exception:
                pass

        email_msg = EmailMessage(
            message_id=msg_id,
            thread_id=msg.get("threadId", ""),
            subject=_get_header(headers, "Subject") or "(No Subject)",
            sender=_get_header(headers, "From"),
            recipients=_get_header(headers, "To"),
            date=date_str,
            date_parsed=date_parsed,
            body=body_text,
            attachments=attachments,
            labels=msg.get("labelIds", []),
        )

        file_count = sum(1 for a in attachments if not a.is_body_extract)
        body_count = sum(1 for a in attachments if a.is_body_extract)
        detail_parts = []
        if file_count:
            detail_parts.append(f"{file_count} file(s)")
        if body_count:
            detail_parts.append(f"{body_count} body extract(s)")

        results.append(email_msg)
        logger.info(
            f"  [{i+1}/{total}] Found {', '.join(detail_parts)} in: "
            f"{email_msg.subject[:60]}"
        )

        if progress_callback:
            progress_callback(i + 1, len(results))

        # Rate limiting
        if (i + 1) % 50 == 0:
            time.sleep(0.5)

    logger.info(f"Scan complete. {len(results)} emails with code found.")
    return results
