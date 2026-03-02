"""Static site generator — renders Flask app to dist/ for static deployment (GitHub Pages / S3)."""

import json
import re
import shutil
from pathlib import Path

from src.config import PROJECTS_DIR, CATALOG_JSON, PROJECT_ROOT


DIST_DIR = PROJECT_ROOT / "dist"


def _load_projects():
    if CATALOG_JSON.exists():
        return json.loads(CATALOG_JSON.read_text())
    return []


def _patch_html(html):
    """Post-process rendered HTML for static mode."""
    # Inject generator meta tag
    html = html.replace(
        '<meta charset="UTF-8">',
        '<meta charset="UTF-8">\n    <meta name="generator" content="static">',
    )
    # Add static-mode class to body
    html = html.replace("<body>", '<body class="static-mode">')
    # Fix static asset paths: /static/ -> relative static/
    # Fix link patterns for S3-style routing
    # /project/X -> /project/X/ (trailing slash for S3 index.html)
    html = re.sub(
        r'href="/project/([^"]+)"',
        lambda m: 'href="/project/' + m.group(1) + '/"',
        html,
    )
    # /view/X/F -> /view/X/F.html
    html = re.sub(
        r'href="/view/([^"]+)"',
        lambda m: 'href="/view/' + m.group(1) + '.html"',
        html,
    )
    # Patch inline fetch URLs for API calls: /api/project/NAME -> /api/project/NAME.json
    html = html.replace(
        "fetch('/api/project/' + encodeURIComponent(name))",
        "fetch('/api/project/' + encodeURIComponent(name) + '.json')",
    )
    html = html.replace(
        "fetch('/api/project/' + encodeURIComponent(projectName))",
        "fetch('/api/project/' + encodeURIComponent(projectName) + '.json')",
    )
    return html


def _patch_app_js(js_content):
    """Patch app.js for static mode."""
    # Prepend static mode detection
    header = (
        "/* Static mode detection */\n"
        "var STATIC_MODE = !!document.querySelector('meta[name=\"generator\"][content=\"static\"]');\n"
        "function staticApiUrl(name) {\n"
        "    return STATIC_MODE\n"
        "        ? '/api/project/' + encodeURIComponent(name) + '.json'\n"
        "        : '/api/project/' + encodeURIComponent(name);\n"
        "}\n\n"
    )
    js_content = header + js_content

    # Replace API fetch calls to use staticApiUrl
    js_content = js_content.replace(
        "fetch('/api/project/' + encodeURIComponent(name))",
        "fetch(staticApiUrl(name))",
    )

    # Guard server-side run: skip execution for server-runnable exts in static mode
    js_content = js_content.replace(
        "if (RUNNABLE_SERVER.indexOf(ext) !== -1) {",
        "if (RUNNABLE_SERVER.indexOf(ext) !== -1 && !STATIC_MODE) {",
    )

    # Skip creating run buttons for server-only files in static mode
    js_content = js_content.replace(
        "function addRunButton(container, projectName, filename, code) {\n"
        "    if (!isRunnable(filename)) return;",
        "function addRunButton(container, projectName, filename, code) {\n"
        "    if (!isRunnable(filename)) return;\n"
        "    if (STATIC_MODE && RUNNABLE_CLIENT.indexOf(getFileExt(filename)) === -1) return;",
    )

    # Add view link fixer for static mode
    js_content += (
        "\n\n/* Static mode: fix view links */\n"
        "if (STATIC_MODE) {\n"
        "    document.addEventListener('DOMContentLoaded', function() {\n"
        "        document.querySelectorAll('a[href*=\"/view/\"]').forEach(function(a) {\n"
        "            if (a.href && !a.href.endsWith('.html')) {\n"
        "                a.href = a.href + '.html';\n"
        "            }\n"
        "        });\n"
        "        document.querySelectorAll('a[href*=\"/project/\"]').forEach(function(a) {\n"
        "            if (a.href && !a.href.endsWith('/')) {\n"
        "                a.href = a.href + '/';\n"
        "            }\n"
        "        });\n"
        "    });\n"
        "}\n"
    )

    return js_content


def build():
    """Build the static site into dist/."""
    from src.web.app import create_app

    projects = _load_projects()
    if not projects:
        print("No projects found. Run 'python3 -m src.main fetch' first.")
        return

    print(f"Building static site for {len(projects)} projects...")

    # Clean and create dist/
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    app = create_app()
    client = app.test_client()

    # 1. Render index.html (unfiltered, all projects)
    print("  Rendering index.html...")
    resp = client.get("/?view=table")
    index_html = _patch_html(resp.data.decode())
    (DIST_DIR / "index.html").write_text(index_html)

    # 2. Generate API JSON files
    api_dir = DIST_DIR / "api" / "project"
    api_dir.mkdir(parents=True)
    print(f"  Generating {len(projects)} API JSON files...")
    for p in projects:
        name = p["name"]
        resp = client.get(f"/api/project/{name}")
        if resp.status_code == 200:
            (api_dir / f"{name}.json").write_text(resp.data.decode())

    # 3. Render project detail pages
    project_dir = DIST_DIR / "project"
    print(f"  Rendering {len(projects)} project pages...")
    for p in projects:
        name = p["name"]
        resp = client.get(f"/project/{name}")
        if resp.status_code == 200:
            page_dir = project_dir / name
            page_dir.mkdir(parents=True)
            html = _patch_html(resp.data.decode())
            (page_dir / "index.html").write_text(html)

    # 4. Render file viewer pages and copy raw files
    view_dir = DIST_DIR / "view"
    raw_dir = DIST_DIR / "raw"
    file_count = 0
    print("  Rendering viewer pages and copying raw files...")
    for p in projects:
        name = p["name"]
        for f in p.get("files", []):
            fname = f["filename"]
            # Viewer page
            resp = client.get(f"/view/{name}/{fname}")
            if resp.status_code == 200:
                vdir = view_dir / name
                vdir.mkdir(parents=True, exist_ok=True)
                html = _patch_html(resp.data.decode())
                (vdir / f"{fname}.html").write_text(html)
                file_count += 1

            # Raw file copy
            src_path = PROJECT_ROOT / f.get("path", "")
            if src_path.exists():
                rdir = raw_dir / name
                rdir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, rdir / fname)

    print(f"  Rendered {file_count} viewer pages.")

    # 5. Copy and patch static assets
    static_dir = DIST_DIR / "static"
    static_dir.mkdir(parents=True)

    # Copy style.css as-is
    src_css = Path(__file__).parent / "web" / "static" / "style.css"
    shutil.copy2(src_css, static_dir / "style.css")

    # Patch and write app.js
    src_js = Path(__file__).parent / "web" / "static" / "app.js"
    js_content = src_js.read_text()
    (static_dir / "app.js").write_text(_patch_app_js(js_content))

    # 6. Copy skill.md
    skill_src = PROJECT_ROOT / "skill.md"
    if skill_src.exists():
        shutil.copy2(skill_src, DIST_DIR / "skill.md")

    # 7. GitHub Pages files
    (DIST_DIR / "CNAME").write_text("codearchaeology.ai\n")
    (DIST_DIR / ".nojekyll").write_text("")

    # Summary
    total_files = sum(1 for _ in DIST_DIR.rglob("*") if _.is_file())
    print(f"\nBuild complete! {total_files} files written to dist/")
    print(f"  Serve locally: python3 -m http.server 9000 -d dist")
