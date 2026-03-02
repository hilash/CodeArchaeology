"""Markdown documentation generator."""

import json
import logging
from pathlib import Path

from src.config import (
    CATALOG_JSON,
    CATALOG_MD,
    OUTPUT_DIR,
    PROJECTS_DIR,
    get_language,
    is_binary,
)

logger = logging.getLogger(__name__)

CODE_PREVIEW_LINES = 50


def generate_project_readme(project: dict) -> str:
    """Generate a README.md for a single project."""
    lines = []
    enrichment = project.get("enrichment")

    # Title — use enrichment clean_title if available
    if enrichment and enrichment.get("clean_title"):
        title = enrichment["clean_title"]
    else:
        name = project.get("name", "Unnamed Project")
        title = name.split("_", 1)[1] if "_" in name else name
        title = title.replace("-", " ").title()
    lines.append(f"# {title}")
    lines.append("")

    # Enrichment summary (prominent position)
    if enrichment and enrichment.get("summary"):
        lines.append(f"> {enrichment['summary']}")
        lines.append("")

    # Topics as tags
    if enrichment and enrichment.get("topics"):
        tags = " ".join(f"`{topic}`" for topic in enrichment["topics"])
        lines.append(f"**Topics:** {tags}")
        lines.append("")

    # Metadata
    emails = project.get("emails", [])
    if emails:
        first_email = emails[0]
        lines.append(f"**Date:** {first_email.get('date', 'Unknown')}")
        lines.append(f"**From:** {first_email.get('sender', 'Unknown')}")
        if first_email.get("recipients"):
            lines.append(f"**To:** {first_email['recipients']}")
        lines.append("")

    # Languages
    languages = project.get("languages", [])
    if languages:
        tags = " ".join(f"`{lang}`" for lang in languages)
        lines.append(f"**Languages:** {tags}")
        lines.append("")

    # Description — use enrichment explanation if available, else email body
    if enrichment and enrichment.get("explanation"):
        lines.append("## Description")
        lines.append("")
        lines.append(enrichment["explanation"])
        lines.append("")
    elif emails:
        body = emails[0].get("body", "").strip()
        if body:
            lines.append("## Description")
            lines.append("")
            body_clean = body[:2000]
            lines.append(body_clean)
            lines.append("")

    # Files
    files = project.get("files", [])
    if files:
        lines.append("## Files")
        lines.append("")
        lines.append("| File | Language | Size |")
        lines.append("|------|----------|------|")
        for f in files:
            fname = f.get("filename", "unknown")
            lang = get_language(fname)
            size = f.get("size", 0)
            size_str = _format_size(size)
            lines.append(f"| `{fname}` | {lang} | {size_str} |")
        lines.append("")

        # Code previews
        for f in files:
            fname = f.get("filename", "unknown")
            fpath = Path(f.get("path", ""))

            if is_binary(fname) or not fpath.exists():
                continue

            try:
                content = fpath.read_text(errors="replace")
            except Exception:
                continue

            if not content.strip():
                continue

            # Get language for syntax highlighting
            lang = get_language(fname)
            lang_hint = _lang_hint(fname)

            preview_lines = content.splitlines()[:CODE_PREVIEW_LINES]
            preview = "\n".join(preview_lines)
            truncated = len(content.splitlines()) > CODE_PREVIEW_LINES

            lines.append(f"### `{fname}`")
            lines.append("")
            lines.append(f"```{lang_hint}")
            lines.append(preview)
            lines.append("```")
            if truncated:
                total = len(content.splitlines())
                lines.append(f"*... ({total - CODE_PREVIEW_LINES} more lines)*")
            lines.append("")

    # Additional emails in thread
    if len(emails) > 1:
        lines.append("## Email Thread")
        lines.append("")
        for i, em in enumerate(emails):
            lines.append(f"### Email {i+1}")
            lines.append(f"- **Subject:** {em.get('subject', '')}")
            lines.append(f"- **From:** {em.get('sender', '')}")
            lines.append(f"- **Date:** {em.get('date', '')}")
            lines.append("")

    return "\n".join(lines)


def generate_catalog(projects: list[dict]) -> str:
    """Generate the master catalog.md."""
    lines = []
    lines.append("# Email Code Catalog")
    lines.append("")
    lines.append(f"**Total Projects:** {len(projects)}")
    lines.append("")

    # Collect all languages
    all_langs = set()
    for p in projects:
        all_langs.update(p.get("languages", []))
    if all_langs:
        lines.append(f"**Languages:** {', '.join(sorted(all_langs))}")
        lines.append("")

    # Table
    lines.append("| Date | Project | Languages | Files | Description |")
    lines.append("|------|---------|-----------|-------|-------------|")

    # Sort by date (newest first)
    sorted_projects = sorted(
        projects,
        key=lambda p: p.get("name", ""),
        reverse=True,
    )

    for p in sorted_projects:
        name = p.get("name", "unknown")
        date = name.split("_")[0] if "_" in name else "?"
        enrichment = p.get("enrichment")

        # Use enrichment clean_title if available
        if enrichment and enrichment.get("clean_title"):
            title_display = enrichment["clean_title"]
        else:
            title = name.split("_", 1)[1] if "_" in name else name
            title_display = title.replace("-", " ").title()

        langs = ", ".join(p.get("languages", [])[:3])
        file_count = len(p.get("files", []))

        # Use enrichment summary for description, else fall back to email body
        if enrichment and enrichment.get("summary"):
            desc = enrichment["summary"][:120].replace("|", "/")
        else:
            desc = ""
            emails = p.get("emails", [])
            if emails:
                body = emails[0].get("body", "").strip()
                desc = body[:100].replace("\n", " ").replace("|", "/")
                if len(body) > 100:
                    desc += "..."

        link = f"[{title_display}](projects/{name}/README.md)"
        lines.append(f"| {date} | {link} | {langs} | {file_count} | {desc} |")

    lines.append("")
    return "\n".join(lines)


def write_all_docs(projects: list[dict]):
    """Generate all documentation files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    # Per-project READMEs
    for project in projects:
        project_dir = Path(project.get("dir", ""))
        if not project_dir.exists():
            project_dir = PROJECTS_DIR / project.get("name", "unknown")

        project_dir.mkdir(parents=True, exist_ok=True)
        readme_path = project_dir / "README.md"
        content = generate_project_readme(project)
        readme_path.write_text(content)
        logger.info(f"Generated: {readme_path}")

    # Master catalog
    catalog_content = generate_catalog(projects)
    CATALOG_MD.write_text(catalog_content)
    logger.info(f"Generated: {CATALOG_MD}")

    # JSON catalog for web UI
    CATALOG_JSON.write_text(json.dumps(projects, indent=2, default=str))
    logger.info(f"Generated: {CATALOG_JSON}")

    logger.info(f"Documentation complete. {len(projects)} project READMEs + catalog.")


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _lang_hint(filename: str) -> str:
    """Get a markdown code fence language hint."""
    import os
    ext = os.path.splitext(filename)[1].lower()
    hints = {
        ".py": "python", ".pyw": "python",
        ".c": "c", ".h": "c",
        ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
        ".cs": "csharp",
        ".java": "java",
        ".js": "javascript", ".jsx": "javascript",
        ".ts": "typescript", ".tsx": "typescript",
        ".go": "go", ".rs": "rust", ".rb": "ruby",
        ".swift": "swift", ".kt": "kotlin",
        ".sh": "bash", ".bash": "bash", ".zsh": "zsh",
        ".bat": "batch", ".ps1": "powershell",
        ".html": "html", ".htm": "html", ".css": "css",
        ".sql": "sql", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".xml": "xml", ".toml": "toml",
        ".asm": "asm", ".s": "asm",
        ".lua": "lua", ".php": "php", ".dart": "dart",
        ".r": "r", ".m": "matlab",
        ".ino": "cpp",
    }
    return hints.get(ext, "")
