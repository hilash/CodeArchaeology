# Email Code Extractor

Download all programming-related attachments from your Gmail, organize them into projects, generate Markdown documentation, and browse/run them in a web viewer.

## Setup

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up Gmail API credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Navigate to **APIs & Services > Library**
4. Search for and enable **Gmail API**
5. Go to **APIs & Services > Credentials**
6. Click **Create Credentials > OAuth 2.0 Client ID**
7. Choose **Desktop application** as the type
8. Download the JSON file
9. Save it as `credentials.json` in this project's root directory

### 3. First run (authentication)

```bash
source .venv/bin/activate
python -m src.main fetch
```

A browser window will open asking you to grant read-only access to your Gmail. After granting access, the tool will start scanning and downloading.

## Usage

```bash
# Activate virtualenv
source .venv/bin/activate

# Download all programming attachments from Gmail
python -m src.main fetch

# Filter by label
python -m src.main fetch --label "INBOX"

# Regenerate docs without re-downloading
python -m src.main catalog

# Launch web viewer
python -m src.main serve
python -m src.main serve --port 3000

# Full pipeline: fetch + catalog + serve
python -m src.main all

# Verbose logging
python -m src.main -v fetch
```

## What it downloads

Any email attachment with these extensions:

- **C/C++**: `.c`, `.h`, `.cpp`, `.hpp`, `.cc`, `.cxx`
- **Python**: `.py`, `.pyw`, `.ipynb`
- **C#**: `.cs`
- **Java**: `.java`, `.jar`
- **JavaScript/TypeScript**: `.js`, `.ts`, `.jsx`, `.tsx`
- **Go, Rust, Ruby, Swift, Kotlin** and more
- **Shell scripts**: `.sh`, `.bat`, `.ps1`
- **Web**: `.html`, `.css`
- **Archives** (extracted): `.zip`, `.tar.gz`, `.7z`
- **Binaries**: `.exe`, `.bin`, `.elf`

## Output structure

```
output/
├── projects/
│   ├── 2024-03-15_matrix-multiplication/
│   │   ├── metadata.json
│   │   ├── files/
│   │   │   ├── matrix.cpp
│   │   │   └── matrix.h
│   │   └── README.md
│   └── ...
├── catalog.md          # Master index of all projects
└── catalog.json        # Machine-readable index
```

## Web viewer features

- Browse all projects with search and language filter
- Syntax-highlighted code viewer
- Run Python and C/C++ code directly (sandboxed with 5s timeout)
- Keyboard shortcut: `Ctrl+Enter` to run code

## Security

- **Read-only**: Gmail API scope is read-only — the tool never modifies or deletes emails
- **Local only**: OAuth tokens stored locally with restricted file permissions
- **Sandboxed execution**: Code runs in isolated temp directories with timeouts
- **Credentials gitignored**: `credentials.json` and `token.json` are in `.gitignore`
