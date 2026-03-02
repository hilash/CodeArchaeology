"""Archive extraction with security checks."""

import logging
import os
import tarfile
import zipfile
from pathlib import Path

from src.config import matches_programming_extension

logger = logging.getLogger(__name__)


def _is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """Check for zip-slip / path traversal attacks."""
    try:
        target_path.resolve().relative_to(base_dir.resolve())
        return True
    except ValueError:
        return False


def extract_zip(archive_path: Path, dest_dir: Path) -> list[str]:
    """Extract a ZIP archive, returning list of extracted filenames."""
    extracted = []
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                target = dest_dir / info.filename
                if not _is_safe_path(dest_dir, target):
                    logger.warning(f"Skipping unsafe path in zip: {info.filename}")
                    continue
                if matches_programming_extension(info.filename):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    zf.extract(info, dest_dir)
                    extracted.append(info.filename)
                    logger.info(f"  Extracted from zip: {info.filename}")
    except Exception as e:
        logger.error(f"Failed to extract {archive_path.name}: {e}")
    return extracted


def extract_tar(archive_path: Path, dest_dir: Path) -> list[str]:
    """Extract a tar archive (.tar.gz, .tar.bz2, .tar.xz)."""
    extracted = []
    try:
        with tarfile.open(archive_path, "r:*") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                target = dest_dir / member.name
                if not _is_safe_path(dest_dir, target):
                    logger.warning(f"Skipping unsafe path in tar: {member.name}")
                    continue
                if matches_programming_extension(member.name):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    # Extract to specific path to avoid traversal
                    with tf.extractfile(member) as src:
                        if src:
                            target.write_bytes(src.read())
                    extracted.append(member.name)
                    logger.info(f"  Extracted from tar: {member.name}")
    except Exception as e:
        logger.error(f"Failed to extract {archive_path.name}: {e}")
    return extracted


def extract_7z(archive_path: Path, dest_dir: Path) -> list[str]:
    """Extract a 7z archive."""
    extracted = []
    try:
        import py7zr
        with py7zr.SevenZipFile(archive_path, mode="r") as sz:
            for name, bio in sz.readall().items():
                target = dest_dir / name
                if not _is_safe_path(dest_dir, target):
                    logger.warning(f"Skipping unsafe path in 7z: {name}")
                    continue
                if matches_programming_extension(name):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(bio.read())
                    extracted.append(name)
                    logger.info(f"  Extracted from 7z: {name}")
    except Exception as e:
        logger.error(f"Failed to extract {archive_path.name}: {e}")
    return extracted


def extract_archive(archive_path: Path, dest_dir: Path) -> list[str]:
    """
    Extract an archive, auto-detecting the format.

    Returns list of extracted filenames (relative to dest_dir).
    """
    name = archive_path.name.lower()

    if name.endswith(".zip"):
        return extract_zip(archive_path, dest_dir)
    elif name.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
        return extract_tar(archive_path, dest_dir)
    elif name.endswith(".7z"):
        return extract_7z(archive_path, dest_dir)
    else:
        logger.warning(f"Unsupported archive format: {archive_path.name}")
        return []


def process_archives_in_directory(directory: Path) -> list[str]:
    """
    Find and extract all archives in a directory.
    Returns list of newly extracted files.
    """
    archive_extensions = {".zip", ".7z"}
    tar_patterns = {".tar.gz", ".tgz", ".tar.bz2", ".tar.xz"}
    all_extracted = []

    for f in list(directory.iterdir()):
        if not f.is_file():
            continue
        name_lower = f.name.lower()

        is_archive = any(name_lower.endswith(ext) for ext in archive_extensions)
        is_tar = any(name_lower.endswith(ext) for ext in tar_patterns)

        if is_archive or is_tar:
            logger.info(f"Extracting archive: {f.name}")
            extracted = extract_archive(f, directory)
            all_extracted.extend(extracted)

    return all_extracted
