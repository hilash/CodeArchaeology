# Email Code Extractor & Project Catalog

## Product Requirements Document (PRD)

---

## 1. Overview

A Python tool that connects to a Gmail account, downloads all emails containing programming-related attachments, organizes them into projects, generates Markdown documentation for each, and optionally provides a web-based simulator to view/run the code.

---

## 2. Problem Statement

Over time, programming assignments, projects, and code snippets accumulate in email (sent as attachments). There is no easy way to:
- Bulk-download only programming-related attachments from Gmail
- Organize them by project/problem
- Generate documentation describing what each project does
- View or run the code in one place

---

## 3. Target User

- The Gmail account owner who has programming files (.h, .py, .cpp, .c, .cs, .exe, .java, .js, .ts, .rb, .go, .rs, .swift, .kt, .sh, .bat, .ps1, .sql, .html, .css, .ipynb, .r, .m, .asm, .s, .makefile, .cmake, .ino, .vhd, .v, .sv, .hex, .bin, .elf, .zip, .tar.gz, .rar, .7z) spread across emails.

---

## 4. Functional Requirements

### 4.1 Gmail Authentication & Connection
- Use Gmail API (OAuth 2.0) via Google Cloud credentials
- Support first-time auth flow (browser-based consent)
- Store refresh token locally for reuse
- Scope: read-only access to Gmail messages and attachments

### 4.2 Email Scanning & Filtering
- Scan ALL emails (inbox, sent, all labels) for attachments
- Filter attachments by programming-related file extensions:
  - **C/C++**: `.c`, `.h`, `.cpp`, `.hpp`, `.cc`, `.cxx`
  - **Python**: `.py`, `.pyw`, `.ipynb`
  - **C#**: `.cs`
  - **Java**: `.java`, `.jar`
  - **JavaScript/TypeScript**: `.js`, `.ts`, `.jsx`, `.tsx`
  - **Go**: `.go`
  - **Rust**: `.rs`
  - **Ruby**: `.rb`
  - **Swift/Kotlin**: `.swift`, `.kt`
  - **Shell/Scripts**: `.sh`, `.bat`, `.ps1`
  - **Web**: `.html`, `.css`
  - **SQL**: `.sql`
  - **Assembly**: `.asm`, `.s`
  - **Build files**: `Makefile`, `CMakeLists.txt`, `.cmake`
  - **Hardware**: `.ino`, `.vhd`, `.v`, `.sv`
  - **Binaries/Executables**: `.exe`, `.bin`, `.elf`, `.hex`
  - **Archives** (containing code): `.zip`, `.tar.gz`, `.rar`, `.7z`
  - **Data/Config**: `.json`, `.yaml`, `.yml`, `.xml`, `.toml`, `.ini`, `.cfg`
- Extract metadata per email:
  - Subject, sender, recipients, date
  - Email body (plain text)
  - All matching attachment filenames and sizes

### 4.3 Download & Organization
- Download all matching attachments to local filesystem
- Directory structure:
  ```
  output/
  ├── projects/
  │   ├── 2024-03-15_matrix-multiplication/
  │   │   ├── metadata.json          # email metadata
  │   │   ├── files/
  │   │   │   ├── matrix.cpp
  │   │   │   └── matrix.h
  │   │   └── README.md              # auto-generated
  │   ├── 2024-04-02_snake-game/
  │   │   ├── metadata.json
  │   │   ├── files/
  │   │   │   └── snake.py
  │   │   └── README.md
  │   └── ...
  ├── catalog.md                     # master index
  └── catalog.json                   # machine-readable index
  ```
- Group emails into "projects" using heuristics:
  - Same subject line (normalized) = same project
  - Multiple attachments in one email = one project
  - Emails in the same thread = one project
- Automatically extract archives (.zip, .tar.gz) and include contents
- Handle duplicate filenames (append counter)
- Store a progress checkpoint so interrupted runs can resume

### 4.4 Markdown Documentation Generation
- For each project, generate a `README.md` containing:
  - **Title**: derived from email subject
  - **Date**: email date
  - **From/To**: sender and recipients
  - **Description**: email body (cleaned up)
  - **Files**: list of attached files with:
    - Filename, size, language detected
    - For text-based source files: inline code preview (first 50 lines)
  - **Language/Tech tags**: auto-detected from file extensions
- Generate a master `catalog.md`:
  - Table of all projects sorted by date
  - Columns: Date | Project Name | Languages | Files | Description snippet
  - Links to each project's README.md

### 4.5 Code Simulator / Viewer (Web UI)
- A local web server (Flask or FastAPI) that provides:
  - **Browse**: list all projects with search/filter
  - **View**: syntax-highlighted code viewer for each file
  - **Run** (sandboxed, optional):
    - Python files: execute in subprocess with timeout (5s) and capture stdout/stderr
    - C/C++ files: compile with gcc/g++ and run (if available)
    - Other files: display only (no execution)
  - **Security**: all execution in subprocess with timeout, no network access, temp directory isolation
- Static fallback: if no server desired, generate a self-contained HTML file with syntax highlighting (using highlight.js)

---

## 5. Non-Functional Requirements

- **Resumable**: checkpoint progress so re-running skips already-downloaded emails
- **Rate limiting**: respect Gmail API quotas (250 quota units/second)
- **Error handling**: skip corrupted/inaccessible emails, log errors, continue
- **Logging**: verbose log file for debugging
- **No data loss**: never modify or delete emails on the server
- **Privacy**: credentials and tokens stored locally, never committed to git

---

## 6. Tech Stack

| Component          | Technology                        |
|--------------------|-----------------------------------|
| Language           | Python 3.13                       |
| Gmail Access       | `google-api-python-client`, OAuth2|
| Web UI             | Flask + Jinja2                    |
| Syntax Highlighting| Pygments (backend) / highlight.js |
| Code Execution     | `subprocess` with sandboxing      |
| Data Storage       | JSON files (no database needed)   |
| Archive Handling   | `zipfile`, `tarfile`, `py7zr`     |
| CLI                | `argparse` or `click`             |

---

## 7. Task Breakdown

### Phase 1: Project Setup & Gmail Auth
| Task | Description | Est. |
|------|-------------|------|
| 1.1 | Init git repo, create project structure, virtualenv, requirements.txt | S |
| 1.2 | Set up Google Cloud project & download `credentials.json` (manual, with instructions) | S |
| 1.3 | Implement Gmail OAuth2 authentication module (`auth.py`) | M |
| 1.4 | Write auth test — verify token retrieval and refresh | S |

### Phase 2: Email Scanning & Downloading
| Task | Description | Est. |
|------|-------------|------|
| 2.1 | Implement email scanner — list all messages with attachments (`scanner.py`) | M |
| 2.2 | Implement attachment filter — match against programming extensions | S |
| 2.3 | Implement attachment downloader — fetch and save to disk (`downloader.py`) | M |
| 2.4 | Implement checkpoint/resume system (track processed message IDs) | S |
| 2.5 | Implement archive extraction (.zip, .tar.gz, .7z) | S |
| 2.6 | Add rate limiting and error handling | S |

### Phase 3: Project Organization & Grouping
| Task | Description | Est. |
|------|-------------|------|
| 3.1 | Implement email-to-project grouping logic (`organizer.py`) | M |
| 3.2 | Create directory structure and write `metadata.json` per project | S |
| 3.3 | Handle duplicates and edge cases | S |

### Phase 4: Markdown Generation
| Task | Description | Est. |
|------|-------------|------|
| 4.1 | Implement per-project `README.md` generator (`docs_generator.py`) | M |
| 4.2 | Implement master `catalog.md` generator | S |
| 4.3 | Add inline code previews with language detection | S |

### Phase 5: Web Simulator / Viewer
| Task | Description | Est. |
|------|-------------|------|
| 5.1 | Set up Flask app with project listing page | M |
| 5.2 | Implement code viewer with syntax highlighting | M |
| 5.3 | Implement sandboxed Python runner | M |
| 5.4 | Implement sandboxed C/C++ compile & run | M |
| 5.5 | Add search and filter to UI | S |

### Phase 6: CLI & Polish
| Task | Description | Est. |
|------|-------------|------|
| 6.1 | Build CLI entry point with commands: `fetch`, `catalog`, `serve` | M |
| 6.2 | Add logging throughout | S |
| 6.3 | Write README.md with setup instructions | S |
| 6.4 | Add `.gitignore` (tokens, credentials, output/) | S |

---

## 8. Directory Structure (Source Code)

```
email-extractor/
├── .gitignore
├── requirements.txt
├── README.md                    # setup & usage instructions
├── PRD.md                       # this document
├── credentials.json             # Google OAuth (gitignored)
├── token.json                   # stored auth token (gitignored)
├── src/
│   ├── __init__.py
│   ├── main.py                  # CLI entry point
│   ├── auth.py                  # Gmail OAuth2 authentication
│   ├── scanner.py               # Email scanning & filtering
│   ├── downloader.py            # Attachment downloading
│   ├── organizer.py             # Project grouping logic
│   ├── docs_generator.py        # Markdown generation
│   ├── archive_handler.py       # .zip/.tar.gz/.7z extraction
│   ├── code_runner.py           # Sandboxed code execution
│   ├── config.py                # Constants, extensions list, paths
│   └── web/
│       ├── app.py               # Flask web server
│       ├── templates/
│       │   ├── base.html
│       │   ├── index.html       # Project listing
│       │   ├── project.html     # Single project view
│       │   └── viewer.html      # Code viewer + runner
│       └── static/
│           ├── style.css
│           └── app.js
├── output/                      # Downloaded & organized projects (gitignored)
│   ├── projects/
│   ├── catalog.md
│   └── catalog.json
├── logs/                        # Log files (gitignored)
└── checkpoint.json              # Resume state (gitignored)
```

---

## 9. Setup Prerequisites (User Action Required)

Before running the tool, the user must:

1. **Create a Google Cloud Project** at https://console.cloud.google.com/
2. **Enable the Gmail API** for that project
3. **Create OAuth 2.0 credentials** (Desktop application type)
4. **Download `credentials.json`** and place it in the project root
5. On first run, a browser window will open for consent — grant read-only Gmail access

---

## 10. Commands (CLI)

```bash
# Download all programming attachments from Gmail
python -m src.main fetch

# Download with specific label filter
python -m src.main fetch --label "INBOX"

# Generate/regenerate markdown catalog only (no download)
python -m src.main catalog

# Launch web viewer
python -m src.main serve --port 8080

# Full pipeline: fetch + catalog + serve
python -m src.main all
```

---

## 11. Security Considerations

- OAuth tokens stored locally with file permissions 600
- `.gitignore` excludes all secrets (`credentials.json`, `token.json`, `output/`)
- Code execution sandboxed: timeout, no network, temp directory, resource limits
- No email modification — read-only API scope
- Archives scanned for path traversal before extraction (zip slip prevention)
