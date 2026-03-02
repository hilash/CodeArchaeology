"""CLI entry point for email-extractor."""

import logging
import sys
from pathlib import Path

import click

from src.config import LOGS_DIR, OUTPUT_DIR, PROJECTS_DIR, DEFAULT_PORT


def setup_logging(verbose: bool = False):
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "email-extractor.log"

    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose/debug logging")
def cli(verbose):
    """Email Code Extractor — download programming files from Gmail."""
    setup_logging(verbose)


@cli.command()
@click.option("--label", default=None, help="Gmail label to filter (e.g. INBOX)")
@click.option("--force", is_flag=True, help="Force re-enrichment of already-enriched projects")
def fetch(label, force):
    """Download all programming attachments from Gmail."""
    logger = logging.getLogger("fetch")

    logger.info("Starting email fetch...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    # Authenticate
    from src.auth import get_gmail_service
    logger.info("Authenticating with Gmail...")
    service = get_gmail_service()
    logger.info("Authenticated successfully.")

    # Scan
    from src.scanner import scan_emails
    def scan_progress(scanned, found):
        print(f"\r  Scanned {scanned} emails, found {found} with code...", end="", flush=True)

    emails = scan_emails(service, label=label, progress_callback=scan_progress)
    print()  # newline after progress

    if not emails:
        logger.info("No emails with programming attachments found.")
        return

    logger.info(f"Found {len(emails)} emails with code attachments.")

    # Download
    from src.downloader import download_all
    def dl_progress(current, total, filename):
        print(f"\r  Downloading [{current}/{total}] {filename[:50]}...", end="", flush=True)

    download_results = download_all(service, emails, progress_callback=dl_progress)
    print()

    # Organize
    from src.organizer import organize_projects
    projects = organize_projects(service, emails, download_results)

    # Auto-enrich
    import os
    if os.environ.get("OPENAI_API_KEY"):
        from src.enricher import auto_enrich_all_projects
        logger.info("Auto-enriching projects with AI...")
        enriched = auto_enrich_all_projects(projects, force=force)
        logger.info(f"Enriched {enriched} projects.")
    else:
        logger.info(
            "Skipping auto-enrichment (OPENAI_API_KEY not set). "
            "Set it to enable AI-powered summaries."
        )

    # Generate docs
    from src.docs_generator import write_all_docs
    write_all_docs(projects)

    logger.info(f"Done! {len(projects)} projects organized in {PROJECTS_DIR}")
    logger.info(f"View catalog: {OUTPUT_DIR / 'catalog.md'}")
    logger.info(f"Run 'python -m src.main serve' to browse in the web viewer.")


@cli.command()
def catalog():
    """Regenerate Markdown docs from existing downloads."""
    logger = logging.getLogger("catalog")

    from src.organizer import load_existing_projects
    from src.docs_generator import write_all_docs

    projects = load_existing_projects()
    if not projects:
        logger.info("No projects found. Run 'fetch' first.")
        return

    write_all_docs(projects)
    logger.info(f"Catalog regenerated for {len(projects)} projects.")


@cli.command()
@click.option("--port", "-p", default=DEFAULT_PORT, help="Port to run the web server on")
def serve(port):
    """Launch the web code viewer."""
    from src.web.app import run_server
    run_server(port=port)


@cli.command()
@click.option(
    "--file", "-f", "enrichments_file",
    type=click.Path(exists=True, path_type=Path),
    help="JSON file mapping project names to enrichment data",
)
@click.option("--auto", "use_auto", is_flag=True, help="Auto-enrich all projects using AI")
@click.option("--force", is_flag=True, help="Force re-enrichment of already-enriched projects")
def enrich(enrichments_file, use_auto, force):
    """Apply enrichment data (summaries, clean titles) to projects."""
    logger = logging.getLogger("enrich")

    from src.organizer import load_existing_projects
    from src.docs_generator import write_all_docs

    if use_auto:
        from src.enricher import auto_enrich_all_projects

        projects = load_existing_projects()
        if not projects:
            logger.info("No projects found. Run 'fetch' first.")
            return

        count = auto_enrich_all_projects(projects, force=force)
        if count > 0:
            write_all_docs(projects)
            logger.info(f"Auto-enriched {count} projects and regenerated docs.")
        else:
            logger.info("No projects were enriched.")
        return

    if enrichments_file:
        from src.enricher import enrich_projects_from_file

        count = enrich_projects_from_file(enrichments_file)
        if count > 0:
            projects = load_existing_projects()
            write_all_docs(projects)
            logger.info(f"Enriched {count} projects and regenerated docs.")
        else:
            logger.info("No projects were enriched.")
        return

    logger.error("Usage: python -m src.main enrich --auto  OR  --file enrichments.json")


@cli.command()
def build():
    """Build static site into dist/ for deployment."""
    from src.builder import build as run_build
    run_build()


@cli.command()
@click.option("--no-rebuild", is_flag=True, help="Skip rebuilding dist/ (use existing build)")
def deploy(no_rebuild):
    """Build static site and deploy to GitHub Pages."""
    import re
    import shutil
    import subprocess

    from src.builder import DIST_DIR

    REPO = "hilash/codearchaeology.ai"

    # 1. Build (unless --no-rebuild)
    if not no_rebuild:
        ctx = click.get_current_context()
        ctx.invoke(build)
    elif not DIST_DIR.exists():
        click.echo("Error: dist/ does not exist. Run without --no-rebuild first.")
        raise SystemExit(1)

    # 2. PII checks
    click.echo("\nRunning PII checks on dist/...")
    pii_found = False

    email_re = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    # Phone: word-boundary, not preceded by '.' (filters decimal coords like 0.537109375)
    phone_re = re.compile(r'(?<![.\d])05[0-8]\d{7}\b')
    # Known real TLDs — emails with other "TLDs" are code references (n@brick.squarelen)
    real_tlds = {
        'com', 'org', 'net', 'edu', 'gov', 'io', 'co', 'il', 'ac', 'uk',
        'de', 'fr', 'ru', 'jp', 'cn', 'au', 'ca', 'br', 'in', 'us', 'eu',
        'info', 'biz', 'me', 'tv', 'cc', 'ly', 'ai', 'dev', 'app',
    }

    # Only scan text files
    text_exts = {'.html', '.json', '.js', '.css', '.txt', '.md', '.htm', '.xml', '.csv'}
    for f in DIST_DIR.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in text_exts:
            continue
        try:
            content = f.read_text(errors='ignore')
        except Exception:
            continue
        rel = f.relative_to(DIST_DIR)
        for match in email_re.finditer(content):
            addr = match.group()
            # Skip image refs, noreply, and code-like patterns
            tld = addr.rsplit('.', 1)[-1].lower()
            if tld not in real_tlds:
                continue
            if 'noreply' in addr or '@example.' in addr:
                continue
            click.echo(f"  EMAIL: {rel}: {addr}")
            pii_found = True
        for match in phone_re.finditer(content):
            click.echo(f"  PHONE: {rel}: {match.group()}")
            pii_found = True

    if pii_found:
        click.echo("\nPII found! Aborting deploy. Clean the data first.")
        raise SystemExit(1)
    click.echo("  PII checks passed.")

    # 3. Create repo if needed
    result = subprocess.run(
        ["gh", "repo", "view", REPO],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        click.echo(f"\nCreating GitHub repo {REPO}...")
        subprocess.run(
            ["gh", "repo", "create", REPO.split("/")[1],
             "--public",
             "--description", "20 Years of //TODO — Code Archaeology from Gmail"],
            check=True,
        )

    # 4. Git init in dist/, commit, force-push
    click.echo(f"\nDeploying to {REPO}...")
    git_dir = DIST_DIR / ".git"
    try:
        subprocess.run(["git", "init"], cwd=DIST_DIR, check=True, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=DIST_DIR, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Deploy static site"],
            cwd=DIST_DIR, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", f"git@github.com:{REPO}.git"],
            cwd=DIST_DIR, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "push", "--force", "origin", "HEAD:main"],
            cwd=DIST_DIR, check=True,
        )
    finally:
        if git_dir.exists():
            shutil.rmtree(git_dir)

    click.echo(f"\nDeployed! Configure GitHub Pages at https://github.com/{REPO}/settings/pages")
    click.echo("DNS records needed:")
    click.echo("  A     @ -> 185.199.108.153, .109., .110., .111.")
    click.echo("  CNAME www -> hilash.github.io.")


@cli.command()
@click.option("--label", default=None, help="Gmail label to filter")
@click.option("--port", "-p", default=DEFAULT_PORT, help="Port for the web viewer")
@click.option("--force", is_flag=True, help="Force re-enrichment of already-enriched projects")
def all(label, port, force):
    """Full pipeline: fetch + catalog + serve."""
    ctx = click.get_current_context()

    # Run fetch (with force pass-through)
    ctx.invoke(fetch, label=label, force=force)

    # Launch server
    ctx.invoke(serve, port=port)


if __name__ == "__main__":
    cli()
