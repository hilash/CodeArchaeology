"""Project organization and grouping logic."""

import json
import logging
import re
from collections import defaultdict
from pathlib import Path

from src.archive_handler import process_archives_in_directory
from src.config import PROJECTS_DIR, get_language
from src.scanner import EmailMessage

logger = logging.getLogger(__name__)


def group_emails(emails: list[EmailMessage]) -> dict[str, list[EmailMessage]]:
    """
    Group emails into projects by thread ID.

    Each unique thread ID becomes its own project — no subject-based merging.
    """
    thread_groups: dict[str, list[EmailMessage]] = defaultdict(list)
    for email_msg in emails:
        thread_groups[email_msg.thread_id].append(email_msg)

    logger.info(
        f"Grouped {len(emails)} emails into {len(thread_groups)} projects."
    )
    return dict(thread_groups)


def _project_dirname(emails: list[EmailMessage]) -> str:
    """Generate a directory name for a project."""
    # Use earliest email date
    dated = [e for e in emails if e.date_parsed]
    if dated:
        dated.sort(key=lambda e: e.date_parsed)
        date_prefix = dated[0].date_parsed.strftime("%Y-%m-%d")
    else:
        date_prefix = "unknown-date"

    # Use subject from first email
    subject = emails[0].subject
    slug = re.sub(r"^(re|fw|fwd)\s*:\s*", "", subject, flags=re.IGNORECASE).strip()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()
    slug = slug[:80] or "unnamed"

    return f"{date_prefix}_{slug}"


def organize_projects(
    service,
    emails: list[EmailMessage],
    download_results: list[dict],
) -> list[dict]:
    """
    Organize downloaded files into project directories.

    Returns list of project info dicts.
    """
    groups = group_emails(emails)
    projects = []

    # Build lookup: message_id -> download result
    dl_lookup = {r["message_id"]: r for r in download_results}

    used_dirnames: set[str] = set()

    for group_key, group_emails_list in groups.items():
        dir_name = _project_dirname(group_emails_list)

        # Handle directory name collisions
        if dir_name in used_dirnames:
            counter = 2
            while f"{dir_name}-{counter}" in used_dirnames:
                counter += 1
            dir_name = f"{dir_name}-{counter}"

        used_dirnames.add(dir_name)
        project_dir = PROJECTS_DIR / dir_name
        files_dir = project_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        # Collect all files for this project
        # Files may already be in the right place from downloader,
        # or we may need to consolidate from multiple email dirs
        all_files = []
        all_email_data = []

        for email_msg in group_emails_list:
            dl = dl_lookup.get(email_msg.message_id)
            if dl and dl.get("files"):
                # Move files from original download location if different
                src_dir = Path(dl["dir"]) / "files"
                if src_dir.resolve() != files_dir.resolve():
                    for file_info in dl["files"]:
                        src_path = Path(file_info["path"])
                        if src_path.exists():
                            dest = files_dir / src_path.name
                            # Handle duplicates
                            counter = 1
                            while dest.exists() and dest.name != src_path.name:
                                stem = src_path.stem
                                dest = files_dir / f"{stem}_{counter}{src_path.suffix}"
                                counter += 1
                            if not dest.exists():
                                src_path.rename(dest)
                                file_info["path"] = str(dest)

                all_files.extend(dl.get("files", []))
            all_email_data.append(email_msg.to_dict())

        # Extract any archives
        extracted = process_archives_in_directory(files_dir)
        for ex_file in extracted:
            ex_path = files_dir / ex_file
            if ex_path.exists():
                all_files.append({
                    "filename": ex_path.name,
                    "original_filename": ex_file,
                    "path": str(ex_path),
                    "size": ex_path.stat().st_size,
                    "extracted_from_archive": True,
                })

        # Detect languages
        languages = set()
        for f in all_files:
            lang = get_language(f["filename"])
            if lang != "Unknown":
                languages.add(lang)

        # Write metadata
        project_info = {
            "name": dir_name,
            "dir": str(project_dir),
            "emails": all_email_data,
            "files": all_files,
            "languages": sorted(languages),
            "date": group_emails_list[0].date,
        }

        metadata_path = project_dir / "metadata.json"
        metadata_path.write_text(json.dumps(project_info, indent=2, default=str))

        projects.append(project_info)
        logger.info(
            f"Organized project: {dir_name} "
            f"({len(all_files)} files, {len(languages)} languages)"
        )

    # Clean up empty directories
    _cleanup_empty_dirs(PROJECTS_DIR)

    return projects


def _cleanup_empty_dirs(root: Path):
    """Remove empty subdirectories."""
    for d in sorted(root.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()


def load_existing_projects() -> list[dict]:
    """Load all existing project metadata from disk."""
    projects = []
    if not PROJECTS_DIR.exists():
        return projects

    for metadata_file in sorted(PROJECTS_DIR.glob("*/metadata.json")):
        try:
            data = json.loads(metadata_file.read_text())
            projects.append(data)
        except Exception as e:
            logger.warning(f"Failed to load {metadata_file}: {e}")

    return projects
