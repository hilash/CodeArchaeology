# Code Archaeology Skill

Build your own "20 Years of Code" — scan your Gmail for every piece of code you ever emailed yourself, organize it into projects, and browse it in a local retro-Gmail web UI.

## What You'll Get

A local website that shows every code attachment you ever sent or received via Gmail — organized by date, enriched with AI-generated summaries, and browsable in a 2006 Gmail-themed interface.

---

## Step 1: Create Your Project

```bash
mkdir code-archaeology && cd code-archaeology
git clone https://github.com/hilash/CodeArchaeology.git .
```

Or start from scratch — the repo gives you the scanner, organizer, enricher, and web UI out of the box.

## Step 2: Set Up Google Cloud Console + Gmail API

This is the longest step, but you only do it once.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Code Archaeology")
3. Enable the **Gmail API**:
   - Go to **APIs & Services > Library**
   - Search for "Gmail API" and click **Enable**
4. Create OAuth credentials:
   - Go to **APIs & Services > Credentials**
   - Click **Create Credentials > OAuth client ID**
   - If prompted, configure the OAuth consent screen first:
     - Choose **External** (or Internal if using Google Workspace)
     - Fill in app name (e.g., "Code Archaeology"), your email, and save
     - Add yourself as a **test user** under the consent screen settings
   - For Application type, choose **Desktop app**
   - Download the JSON file
5. Rename the downloaded file to `credentials.json` and place it in the project root

## Step 3: Install Dependencies

```bash
python3 -m pip install -r requirements.txt
```

If you're on macOS with Homebrew Python, you may need:

```bash
python3 -m pip install -r requirements.txt --break-system-packages
```

## Step 4: Run the First Scan

```bash
python3 -m src.main fetch
```

The first time you run this, a browser window will open asking you to authorize Gmail access. Sign in and allow — this creates a `token.json` file for future runs.

The scanner will:
- Search all your Gmail labels for emails with code attachments
- Download attachments to `output/projects/`
- Organize them by thread ID
- Build a `output/catalog.json` index

This may take a few minutes depending on how many emails you have.

### Filter by label (optional)

To scan only a specific Gmail label:

```bash
python3 -m src.main fetch --label "INBOX"
```

## Step 5: Browse Your Code

```bash
python3 -m src.main serve --port 8081
```

Open [http://localhost:8081](http://localhost:8081) in your browser. You'll see your code history in a retro Gmail inbox view.

---

## Optional: AI Enrichment

Add AI-generated titles, summaries, and topic tags to each project using OpenAI.

1. Get an [OpenAI API key](https://platform.openai.com/api-keys)
2. Set the environment variable:

```bash
export OPENAI_API_KEY="sk-..."
```

3. Run enrichment:

```bash
python3 -m src.main enrich --auto
```

To re-enrich already-enriched projects:

```bash
python3 -m src.main enrich --auto --force
```

---

## Optional: PII Scrubbing

Before sharing your site publicly, you should scrub personally identifiable information.

### What to look for

- **Email addresses**: yours, classmates', professors', colleagues'
- **ID numbers**: student IDs, national IDs, any 9+ digit numbers
- **Phone numbers**: mobile numbers in code comments or metadata
- **Names**: full names near identifying context

### Scan for PII

```bash
# Find email addresses
grep -rP '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' output/

# Find 9-digit numbers (filter false positives like constants)
grep -rP '\b\d{9}\b' output/

# Find phone numbers (adjust pattern for your country)
grep -rP '05\d{8}' output/
```

### Important warnings

- **NEVER** do text-based find/replace on binary files (zip, rar, etc.) — it corrupts them. Only scrub text files.
- After modifying `catalog.json`, validate it: `python3 -c "import json; json.loads(open('output/catalog.json').read()); print('OK')"`
- If you corrupt binary files, re-download them by running `fetch` again

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `python3 -m src.main fetch` | Scan Gmail, download, organize |
| `python3 -m src.main fetch --label "INBOX"` | Scan specific label only |
| `python3 -m src.main serve --port 8081` | Start web UI |
| `python3 -m src.main enrich --auto` | AI enrichment (needs OpenAI key) |
| `python3 -m src.main enrich --auto --force` | Re-enrich all projects |

---

## Troubleshooting

- **"token.json not found"**: Run `fetch` first — it triggers the OAuth flow
- **Port already in use**: Try a different port: `--port 8082`
- **No projects found**: Check your Gmail actually has code attachments. Try scanning all labels (default) rather than filtering
- **Binary files corrupted after scrubbing**: Re-run `fetch` to re-download from Gmail

---

Built with Python, Flask, Gmail API, and optionally OpenAI. Inspired by 20 years of emailing code to yourself.
