"""Attachment downloading with checkpoint/resume support."""

import base64
import json
import logging
import time
from pathlib import Path

from src.config import CHECKPOINT_FILE, PROJECTS_DIR
from src.scanner import EmailMessage

logger = logging.getLogger(__name__)


def load_checkpoint() -> set[str]:
    """Load set of already-processed message IDs."""
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text())
        return set(data.get("processed_ids", []))
    return set()


def save_checkpoint(processed_ids: set[str]):
    """Save checkpoint with processed message IDs."""
    CHECKPOINT_FILE.write_text(json.dumps({
        "processed_ids": sorted(processed_ids),
    }, indent=2))


def _save_body_code(code: str, dest_path: Path) -> bool:
    """Write extracted body code to a file."""
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(code, encoding="utf-8")
        logger.info(f"  Saved body extract: {dest_path.name} ({len(code)} bytes)")
        return True
    except Exception as e:
        logger.error(f"Failed to save body code to {dest_path.name}: {e}")
        return False


def download_attachment(service, message_id: str, attachment_id: str, dest_path: Path) -> bool:
    """
    Download a single attachment from Gmail.

    Returns True on success, False on failure.
    """
    try:
        att = service.users().messages().attachments().get(
            userId="me", messageId=message_id, id=attachment_id
        ).execute()

        data = att.get("data", "")
        if not data:
            logger.warning(f"Empty attachment data for {dest_path.name}")
            return False

        file_data = base64.urlsafe_b64decode(data)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(file_data)
        logger.info(f"  Downloaded: {dest_path.name} ({len(file_data)} bytes)")
        return True

    except Exception as e:
        logger.error(f"Failed to download attachment {dest_path.name}: {e}")
        return False


def download_all(
    service,
    emails: list[EmailMessage],
    progress_callback=None,
) -> list[dict]:
    """
    Download all attachments from matched emails.

    Args:
        service: Authenticated Gmail API service
        emails: List of EmailMessage objects to download from
        progress_callback: Optional callable(current, total, filename)

    Returns:
        List of dicts with download info per email
    """
    processed_ids = load_checkpoint()
    download_results = []
    total = len(emails)

    # Filter out already-processed emails
    to_process = [e for e in emails if e.message_id not in processed_ids]
    skipped = total - len(to_process)
    if skipped > 0:
        logger.info(f"Skipping {skipped} already-processed emails (checkpoint).")

    for i, email_msg in enumerate(to_process):
        msg_id = email_msg.message_id
        logger.info(
            f"[{i+1}/{len(to_process)}] Processing: {email_msg.subject[:60]}"
        )

        # Create a staging directory for this email's files
        safe_subject = _slugify(email_msg.subject)
        date_prefix = ""
        if email_msg.date_parsed:
            date_prefix = email_msg.date_parsed.strftime("%Y-%m-%d") + "_"

        dir_name = f"{date_prefix}{safe_subject}"
        email_dir = PROJECTS_DIR / dir_name / "files"
        email_dir.mkdir(parents=True, exist_ok=True)

        downloaded_files = []
        for att in email_msg.attachments:
            dest = email_dir / _safe_filename(att.filename, email_dir)

            if progress_callback:
                progress_callback(i + 1, len(to_process), att.filename)

            if att.is_body_extract:
                success = _save_body_code(att.body_code, dest)
                if success:
                    downloaded_files.append({
                        "filename": dest.name,
                        "original_filename": att.filename,
                        "path": str(dest),
                        "size": dest.stat().st_size,
                        "extracted_from_body": True,
                    })
            else:
                success = download_attachment(service, msg_id, att.attachment_id, dest)
                if success:
                    downloaded_files.append({
                        "filename": dest.name,
                        "original_filename": att.filename,
                        "path": str(dest),
                        "size": dest.stat().st_size,
                    })

                time.sleep(0.1)  # Rate limiting between attachments

        download_results.append({
            "message_id": msg_id,
            "subject": email_msg.subject,
            "dir": str(email_dir.parent),
            "files": downloaded_files,
        })

        # Mark as processed
        processed_ids.add(msg_id)
        save_checkpoint(processed_ids)

    logger.info(f"Download complete. Processed {len(to_process)} emails.")
    return download_results


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    import re
    # Remove Re:, Fw:, Fwd: prefixes
    text = re.sub(r"^(re|fw|fwd)\s*:\s*", "", text, flags=re.IGNORECASE)
    text = text.strip()
    # Replace non-alphanum with hyphens
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text)
    # Clean up
    text = text.strip("-").lower()
    return text[:80] or "unnamed"


def _safe_filename(filename: str, directory: Path) -> str:
    """
    Return a safe filename, appending a counter if it already exists.
    """
    name = Path(filename).stem
    ext = Path(filename).suffix
    # Sanitize
    import re
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    candidate = f"{name}{ext}"

    counter = 1
    while (directory / candidate).exists():
        candidate = f"{name}_{counter}{ext}"
        counter += 1

    return candidate
