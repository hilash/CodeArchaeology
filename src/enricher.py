"""Project enrichment utilities — clean titles, descriptions, and metadata."""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from src.config import BINARY_EXTENSIONS, PROJECTS_DIR

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenAI client (lazy singleton)
# ---------------------------------------------------------------------------

_openai_client = None


def _get_openai_client():
    """Return a cached OpenAI client. Requires OPENAI_API_KEY env var."""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable is not set. "
                "Set it to enable auto-enrichment."
            )
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_MAX_CONTENT_BYTES = 50_000  # cap total content sent to the model


def _build_enrichment_prompt(project: dict) -> str:
    """Build a prompt from project emails and file contents."""
    parts: list[str] = []
    budget = _MAX_CONTENT_BYTES

    # Email metadata + body
    for em in project.get("emails", []):
        block = (
            f"Subject: {em.get('subject', '')}\n"
            f"From: {em.get('sender', '')}\n"
            f"Date: {em.get('date', '')}\n"
            f"Body:\n{em.get('body', '')}\n"
        )
        if len(block) > budget:
            block = block[:budget]
        parts.append(block)
        budget -= len(block)
        if budget <= 0:
            break

    # File contents (skip binaries)
    if budget > 0:
        for f in project.get("files", []):
            fname = f.get("filename", "")
            ext = os.path.splitext(fname)[1].lower()
            if ext in BINARY_EXTENSIONS:
                continue
            fpath = Path(f.get("path", ""))
            if not fpath.exists():
                continue
            try:
                content = fpath.read_text(errors="replace")
            except Exception:
                continue
            header = f"\n--- File: {fname} ---\n"
            snippet = content[: budget - len(header)]
            parts.append(header + snippet)
            budget -= len(header) + len(snippet)
            if budget <= 0:
                break

    context = "\n".join(parts)
    return (
        "You are analyzing a student programming assignment submitted via email.\n"
        "Based on the email and attached source code below, return a JSON object with:\n"
        '  "summary": a 1-2 sentence summary of the project,\n'
        '  "explanation": a paragraph explaining what the code does,\n'
        '  "clean_title": a short, human-readable project title (no student IDs),\n'
        '  "topics": a list of 2-5 topic tags (e.g. ["sorting", "C++", "linked list"])\n'
        "\n"
        "Return ONLY valid JSON, no markdown fences or extra text.\n"
        "\n"
        f"{context}"
    )


# ---------------------------------------------------------------------------
# Per-project auto enrichment
# ---------------------------------------------------------------------------


def auto_enrich_project(project: dict, *, force: bool = False) -> bool:
    """Enrich a single project via OpenAI. Returns True if enrichment was applied."""
    if not force and project.get("enrichment"):
        logger.debug(f"Skipping already-enriched project: {project.get('name')}")
        return False

    prompt = _build_enrichment_prompt(project)
    client = _get_openai_client()

    last_err = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.choices[0].message.content.strip()
            # Strip markdown fences if the model wraps them anyway
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
            enrichment = json.loads(text)
            break
        except json.JSONDecodeError as e:
            logger.warning(
                f"Invalid JSON from model for {project.get('name')}: {e}"
            )
            last_err = e
            break  # retrying won't help for bad JSON
        except Exception as e:
            last_err = e
            wait = 2 ** attempt
            logger.warning(
                f"Enrichment attempt {attempt + 1}/3 failed for "
                f"{project.get('name')}: {e}  — retrying in {wait}s"
            )
            time.sleep(wait)
    else:
        logger.error(
            f"Failed to enrich {project.get('name')} after 3 attempts: {last_err}"
        )
        return False

    # Validate expected keys
    for key in ("summary", "explanation", "clean_title", "topics"):
        if key not in enrichment:
            logger.warning(
                f"Enrichment for {project.get('name')} missing key '{key}'"
            )

    save_enrichment(project, enrichment)
    return True


# ---------------------------------------------------------------------------
# Batch wrapper
# ---------------------------------------------------------------------------


def auto_enrich_all_projects(
    projects: list[dict], *, force: bool = False
) -> int:
    """Enrich all projects, with a 1-second delay between API calls.

    Returns the number of projects that were enriched.
    """
    count = 0
    for i, project in enumerate(projects):
        try:
            if auto_enrich_project(project, force=force):
                count += 1
            # Delay between API calls (skip after last)
            if i < len(projects) - 1:
                time.sleep(1)
        except Exception as e:
            logger.error(f"Error enriching {project.get('name')}: {e}")
    logger.info(f"Auto-enriched {count}/{len(projects)} projects.")
    return count

# Pattern: 7-9 consecutive digits (student IDs)
_ID_PATTERN = re.compile(r"\b\d{7,9}\b")

# Re:/Fw:/Fwd: prefixes (possibly chained)
_REPLY_PREFIX = re.compile(r"^(re|fw|fwd)\s*:\s*", flags=re.IGNORECASE)


def strip_ids(text: str) -> str:
    """Remove 7-9 digit numbers (student IDs) from text."""
    result = _ID_PATTERN.sub("", text)
    # Clean up leftover separators (e.g. "hw1-" or "hw1_")
    result = re.sub(r"[-_]+$", "", result.strip())
    # Collapse multiple spaces/separators
    result = re.sub(r"[\s]+", " ", result).strip()
    return result


def clean_project_title(project: dict) -> str:
    """Generate a clean display title from project data.

    Strips Re:/Fw: prefixes and student IDs from the email subject.
    Falls back to the directory name if no subject is available.
    """
    # Try email subject first
    emails = project.get("emails", [])
    if emails:
        subject = emails[0].get("subject", "")
        if subject:
            # Strip reply/forward prefixes
            title = _REPLY_PREFIX.sub("", subject).strip()
            # Strip student IDs
            title = strip_ids(title)
            # Clean separators
            title = re.sub(r"^[-_]+|[-_]+$", "", title).strip()
            if title:
                return title

    # Fall back to directory name
    name = project.get("name", "Unnamed Project")
    title = name.split("_", 1)[1] if "_" in name else name
    title = strip_ids(title)
    title = title.replace("-", " ").replace("_", " ").strip().title()
    return title or "Unnamed Project"


def load_enrichment(project_dir: Path) -> dict | None:
    """Load existing enrichment data from a project's metadata.json."""
    metadata_path = project_dir / "metadata.json"
    if not metadata_path.exists():
        return None

    try:
        data = json.loads(metadata_path.read_text())
        return data.get("enrichment")
    except Exception as e:
        logger.warning(f"Failed to load enrichment from {metadata_path}: {e}")
        return None


def save_enrichment(project: dict, enrichment: dict):
    """Save enrichment data into a project's metadata.json.

    Updates the project dict in-place and writes to disk.
    """
    enrichment["enriched_at"] = datetime.now(timezone.utc).isoformat()
    project["enrichment"] = enrichment

    project_dir = Path(project.get("dir", ""))
    if not project_dir.exists():
        project_dir = PROJECTS_DIR / project.get("name", "unknown")

    metadata_path = project_dir / "metadata.json"
    metadata_path.write_text(json.dumps(project, indent=2, default=str))
    logger.info(f"Saved enrichment for {project.get('name', 'unknown')}")


def enrich_projects_from_file(enrichments_file: Path) -> int:
    """Batch-apply enrichments from a JSON file.

    The JSON file should map project directory names to enrichment dicts:
    {
        "2006-03-14_hw1": {
            "summary": "...",
            "explanation": "...",
            "clean_title": "...",
            "topics": ["...", "..."]
        }
    }

    Returns the number of projects enriched.
    """
    if not enrichments_file.exists():
        logger.error(f"Enrichments file not found: {enrichments_file}")
        return 0

    enrichments = json.loads(enrichments_file.read_text())
    count = 0

    for project_name, enrichment_data in enrichments.items():
        metadata_path = PROJECTS_DIR / project_name / "metadata.json"
        if not metadata_path.exists():
            logger.warning(f"Project not found: {project_name}")
            continue

        try:
            project = json.loads(metadata_path.read_text())
            save_enrichment(project, enrichment_data)
            count += 1
        except Exception as e:
            logger.error(f"Failed to enrich {project_name}: {e}")

    logger.info(f"Enriched {count}/{len(enrichments)} projects from {enrichments_file}")
    return count
