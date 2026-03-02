"""Flask web application for browsing and running code."""

import json
import os
import shutil
from pathlib import Path

from flask import Flask, render_template, request, jsonify, abort, redirect, url_for, send_file
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_for_filename, TextLexer

from src.code_runner import run_code
from src.config import PROJECTS_DIR, CATALOG_JSON, PROJECT_ROOT, is_binary, get_language, DEFAULT_PORT


# Programming language names recognized in enrichment topics
_KNOWN_LANGUAGES = {
    "Assembly", "AWK", "Bash", "C", "C#", "C++", "Clojure", "COBOL",
    "CSS", "Dart", "Delphi", "Elixir", "Erlang", "F#", "Fortran", "Go",
    "Groovy", "Haskell", "HTML", "Java", "JavaScript", "JSON", "Julia",
    "Kotlin", "Lisp", "Lua", "MATLAB", "Nim", "OCaml", "OpenGL",
    "Pascal", "Perl", "PHP", "Prolog", "Python", "R", "Racket", "Ruby",
    "Rust", "Scala", "Scheme", "Shell", "SQL", "Swift", "Tcl",
    "TypeScript", "VHDL", "Verilog", "Zig",
}


def _project_topics(project):
    """Return the set of enrichment topics for a project."""
    return set((project.get("enrichment") or {}).get("topics", []))


def _project_languages(project):
    """Return languages from both the languages field and enrichment topics."""
    langs = set(project.get("languages", []))
    for topic in _project_topics(project):
        if topic in _KNOWN_LANGUAGES:
            langs.add(topic)
    return langs


def _project_categories(project):
    """Return non-language enrichment topics."""
    return {t for t in _project_topics(project) if t not in _KNOWN_LANGUAGES}


def create_app():
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    def _load_projects():
        if CATALOG_JSON.exists():
            return json.loads(CATALOG_JSON.read_text())
        return []

    @app.after_request
    def add_no_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

    @app.route("/")
    def index():
        projects = _load_projects()
        query = request.args.get("q", "").lower()
        lang_filter = request.args.get("lang", "")
        cat_filter = request.args.get("cat", "")
        notes_filter = request.args.get("notes", "")
        sort_order = request.args.get("sort", "newest")
        view_mode = request.args.get("view", "table")

        if query:
            projects = [
                p for p in projects
                if query in p.get("name", "").lower()
                or query in ((p.get("enrichment") or {}).get("clean_title") or "").lower()
                or query in json.dumps(p.get("emails", [{}])).lower()
            ]
        if lang_filter:
            projects = [
                p for p in projects
                if lang_filter in _project_languages(p)
            ]
        if cat_filter:
            projects = [
                p for p in projects
                if cat_filter in _project_categories(p)
            ]
        if notes_filter == "has_notes":
            projects = [p for p in projects if p.get("notes")]

        # Sort by date prefix (YYYY-MM-DD_...)
        projects.sort(
            key=lambda p: p.get("name", "").split("_")[0],
            reverse=(sort_order == "newest"),
        )

        # Collect languages and categories across all projects
        all_languages = set()
        all_categories = set()
        for p in _load_projects():
            all_languages.update(_project_languages(p))
            all_categories.update(_project_categories(p))

        # Count projects with notes
        notes_count = sum(1 for p in _load_projects() if p.get("notes"))

        return render_template(
            "index.html",
            projects=projects,
            project_count=len(projects),
            query=query,
            lang_filter=lang_filter,
            cat_filter=cat_filter,
            notes_filter=notes_filter,
            all_languages=sorted(all_languages),
            all_categories=sorted(all_categories),
            notes_count=notes_count,
            sort_order=sort_order,
            view_mode=view_mode,
        )

    @app.route("/project/<path:name>")
    def project_detail(name):
        projects = _load_projects()
        projects.sort(key=lambda p: p.get("name", "").split("_")[0], reverse=True)
        idx = next((i for i, p in enumerate(projects) if p.get("name") == name), None)
        if idx is None:
            abort(404)
        project = projects[idx]
        prev_name = projects[idx - 1]["name"] if idx > 0 else None
        next_name = projects[idx + 1]["name"] if idx < len(projects) - 1 else None
        return render_template("project.html", project=project, prev_name=prev_name, next_name=next_name)

    @app.route("/api/project/<path:name>")
    def api_project_detail(name):
        projects = _load_projects()
        project = next((p for p in projects if p.get("name") == name), None)
        if not project:
            return jsonify({"error": "not found"}), 404

        # Read file contents (non-binary, capped at 100KB each)
        file_previews = []
        for f in project.get("files", []):
            fname = f.get("filename", "")
            if is_binary(fname):
                file_previews.append({"filename": fname, "binary": True, "content": ""})
                continue
            fpath = PROJECT_ROOT / f.get("path", "")
            content = ""
            if fpath.exists():
                try:
                    content = fpath.read_text(errors="replace")[:100_000]
                except Exception:
                    content = "[Could not read file]"
            file_previews.append({
                "filename": fname,
                "binary": False,
                "content": content,
                "language": get_language(fname),
            })

        enrichment = project.get("enrichment") or {}
        emails = project.get("emails", [])
        first_email = emails[0] if emails else {}

        return jsonify({
            "name": project.get("name"),
            "clean_title": enrichment.get("clean_title", ""),
            "summary": enrichment.get("summary", ""),
            "explanation": enrichment.get("explanation", ""),
            "topics": enrichment.get("topics", []),
            "languages": project.get("languages", []),
            "date": first_email.get("date", ""),
            "sender": first_email.get("sender", ""),
            "subject": first_email.get("subject", ""),
            "body": (first_email.get("body") or "")[:2000],
            "notes": project.get("notes", ""),
            "euler_links": enrichment.get("euler_links", []),
            "euler_problems": enrichment.get("euler_problems", ""),
            "files": file_previews,
        })

    @app.route("/view/<path:name>/<path:filename>")
    def view_file(name, filename):
        projects = _load_projects()
        project = next((p for p in projects if p.get("name") == name), None)
        if not project:
            abort(404)

        # Find the file
        file_info = next(
            (f for f in project.get("files", []) if f.get("filename") == filename),
            None,
        )
        if not file_info:
            abort(404)

        file_path = PROJECT_ROOT / file_info.get("path", "")
        if not file_path.exists():
            abort(404)

        binary = is_binary(filename)
        ext = os.path.splitext(filename)[1].lower()
        is_image = ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp")
        code = ""
        highlighted = ""
        language = get_language(filename)

        if not binary:
            try:
                code = file_path.read_text(errors="replace")
                try:
                    lexer = get_lexer_for_filename(filename)
                except Exception:
                    lexer = TextLexer()
                formatter = HtmlFormatter(
                    linenos=True,
                    cssclass="highlight",
                    style="monokai",
                )
                highlighted = highlight(code, lexer, formatter)
            except Exception:
                code = "[Could not read file]"

        # Check if runnable
        runnable = ext in (".py", ".pyw", ".c", ".cpp", ".cc", ".cxx")

        return render_template(
            "viewer.html",
            project=project,
            file_info=file_info,
            code=code,
            highlighted=highlighted,
            language=language,
            binary=binary,
            is_image=is_image,
            runnable=runnable,
            pygments_css=HtmlFormatter(style="monokai").get_style_defs(".highlight"),
        )

    @app.route("/raw/<path:name>/<path:filename>")
    def raw_file(name, filename):
        """Serve raw project files (images, etc.)."""
        projects = _load_projects()
        project = next((p for p in projects if p.get("name") == name), None)
        if not project:
            abort(404)
        file_info = next(
            (f for f in project.get("files", []) if f.get("filename") == filename),
            None,
        )
        if not file_info:
            abort(404)
        file_path = PROJECT_ROOT / file_info.get("path", "")
        if not file_path.exists():
            abort(404)
        return send_file(file_path)

    @app.route("/delete-bulk", methods=["POST"])
    def delete_bulk():
        names = request.form.getlist("selected")
        if not names:
            return redirect(url_for("index"))

        projects = _load_projects()
        for name in names:
            project_dir = PROJECTS_DIR / name
            if project_dir.exists():
                shutil.rmtree(project_dir)

        remaining = [p for p in projects if p.get("name") not in names]
        CATALOG_JSON.write_text(json.dumps(remaining, indent=2, default=str))

        return redirect(url_for("index"))

    @app.route("/notes/<path:name>", methods=["POST"])
    def save_notes(name):
        projects = _load_projects()
        project = next((p for p in projects if p.get("name") == name), None)
        if not project:
            abort(404)

        notes_text = request.form.get("notes", "").strip()
        project["notes"] = notes_text

        # Persist to metadata.json
        project_dir = PROJECTS_DIR / name
        metadata_path = project_dir / "metadata.json"
        if metadata_path.exists():
            meta = json.loads(metadata_path.read_text())
            meta["notes"] = notes_text
            metadata_path.write_text(json.dumps(meta, indent=2, default=str))

        # Update catalog.json
        for p in projects:
            if p.get("name") == name:
                p["notes"] = notes_text
                break
        CATALOG_JSON.write_text(json.dumps(projects, indent=2, default=str))

        return redirect(f"/project/{name}")

    @app.route("/delete/<path:name>", methods=["POST"])
    def delete_project(name):
        projects = _load_projects()
        project = next((p for p in projects if p.get("name") == name), None)
        if not project:
            abort(404)

        # Remove project directory from disk
        project_dir = PROJECTS_DIR / name
        if project_dir.exists():
            shutil.rmtree(project_dir)

        # Update catalog.json
        remaining = [p for p in projects if p.get("name") != name]
        CATALOG_JSON.write_text(json.dumps(remaining, indent=2, default=str))

        return redirect(url_for("index"))

    @app.route("/run/<path:name>/<path:filename>", methods=["POST"])
    def run_file(name, filename):
        projects = _load_projects()
        project = next((p for p in projects if p.get("name") == name), None)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        file_info = next(
            (f for f in project.get("files", []) if f.get("filename") == filename),
            None,
        )
        if not file_info:
            return jsonify({"error": "File not found"}), 404

        file_path = PROJECT_ROOT / file_info.get("path", "")
        if not file_path.exists():
            return jsonify({"error": "File not found on disk"}), 404

        try:
            code = file_path.read_text(errors="replace")
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        stdin_input = ""
        if request.is_json and request.json:
            stdin_input = request.json.get("stdin", "")
        result = run_code(code, filename, stdin_input)
        return jsonify(result)

    @app.route("/skill")
    def download_skill():
        skill_path = PROJECT_ROOT / "skill.md"
        if not skill_path.exists():
            abort(404)
        return send_file(skill_path, as_attachment=True, download_name="code-archaeology-skill.md")

    return app


def run_server(port: int = DEFAULT_PORT):
    app = create_app()
    print(f"Starting web viewer at http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
