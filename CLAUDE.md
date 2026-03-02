# CLAUDE.md - Project Guidelines

## Project Overview
Gmail code archaeology tool: scans Gmail for code attachments, organizes into projects by thread ID, auto-enriches with OpenAI, and serves a web UI for browsing.

## PII Scrubbing Rules
The `output/` directory contains real email data. Before any public sharing, ALL of the following must be scrubbed:

### Already Scrubbed
1. **Israeli ID numbers (Teudat Zehut)** — 9-digit personal IDs removed:
   - Multiple student IDs replaced with empty string in all file contents (code, metadata, README, catalog)
   - Directory names were also renamed to remove IDs

2. **Email addresses** — ALL email addresses removed using regex `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`:
   - Owner email and obfuscated email patterns removed
   - All other personal emails: classmates, professors, colleagues (~140 unique addresses)
   - Third-party library author emails in vendored JS were also removed
   - Total: ~2,700+ email occurrences removed across ~700 files

3. **Phone numbers** — Found in a non-code payment form file
   - This file also contains other PII (consider deleting the entire project)

### Scrubbing Process
- Text-based replacement was used (`str.replace` and `re.sub`)
- **CAUTION**: This corrupted binary files (zip, rar) whose internal filenames contained the scrubbed strings. The catalog.json also broke due to invalid JSON escapes after removal. Both were fixed by re-downloading from Gmail and rebuilding catalog from metadata.json files.
- After scrubbing, always verify: `python3 -c "import json; json.loads(open('output/catalog.json').read()); print('OK')"`

### Before Publishing — Check For
- Run email regex scan: `grep -rP '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' output/`
- Run 9-digit ID scan: `grep -rP '\b\d{9}\b' output/` (filter out false positives like constants)
- Check for phone numbers: `grep -rP '05\d{8}' output/`
- Check for full names near identifying info
- The BTL payment form project should probably be deleted entirely

## Tech Stack
- Python 3.13, Flask, Jinja2, Pygments
- OpenAI GPT-4o-mini for enrichment (requires `OPENAI_API_KEY` env var)
- Gmail API for scanning (requires `credentials.json` + `token.json`)
- highlight.js (CDN) for client-side syntax highlighting
- Web UI styled to match hilash.github.io console theme

## Key Architecture
- `src/scanner.py` — Gmail API scanning (all labels by default, use `--label` to filter)
- `src/organizer.py` — Groups emails by thread ID only (no subject-based merging)
- `src/enricher.py` — OpenAI auto-enrichment with retry logic
- `src/web/app.py` — Flask app with JSON API endpoints
- `output/` is gitignored — contains actual email/project data
- `output/catalog.json` is the central index, rebuilt from individual `metadata.json` files

## Commands
- `python3 -m src.main fetch` — scan, download, organize, enrich
- `python3 -m src.main serve --port 8081` — start web UI
- `python3 -m src.main enrich --auto` — re-run enrichment only
- Add `--force` to re-enrich already-enriched projects
