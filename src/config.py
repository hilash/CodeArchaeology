"""Configuration constants for email-extractor."""

import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
PROJECTS_DIR = OUTPUT_DIR / "projects"
LOGS_DIR = PROJECT_ROOT / "logs"
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"
CHECKPOINT_FILE = PROJECT_ROOT / "checkpoint.json"
CATALOG_MD = OUTPUT_DIR / "catalog.md"
CATALOG_JSON = OUTPUT_DIR / "catalog.json"

# Gmail API
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
GMAIL_BATCH_SIZE = 100  # messages per batch request
GMAIL_MAX_RESULTS = 500  # messages per list page

# Programming file extensions (lowercase, with dot)
CODE_EXTENSIONS = {
    # C/C++
    ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hh",
    # Python
    ".py", ".pyw", ".ipynb",
    # C#
    ".cs",
    # Java
    ".java", ".jar",
    # JavaScript / TypeScript
    ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
    # Go
    ".go",
    # Rust
    ".rs",
    # Ruby
    ".rb",
    # Swift / Kotlin
    ".swift", ".kt", ".kts",
    # Shell / Scripts
    ".sh", ".bat", ".ps1", ".bash", ".zsh",
    # Web
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    # SQL
    ".sql",
    # Assembly
    ".asm", ".s",
    # Build files
    ".cmake", ".makefile", ".mk",
    # Hardware / Embedded
    ".ino", ".vhd", ".vhdl", ".v", ".sv",
    # Binaries / Executables
    ".exe", ".com", ".bin", ".elf", ".hex", ".o", ".a", ".so", ".dll", ".out",
    # Data / Config
    ".json", ".yaml", ".yml", ".xml", ".toml", ".ini", ".cfg",
    # R / MATLAB
    ".r", ".m",
    # Prolog
    ".pro", ".P",
    # Lisp / Scheme / Functional
    ".lisp", ".lsp", ".cl", ".el", ".scm", ".ss", ".rkt",
    ".hs", ".lhs", ".ml", ".mli", ".fs", ".fsx", ".fsi",
    ".erl", ".hrl", ".ex", ".exs", ".clj", ".cljs",
    # Pascal / Delphi
    ".pas", ".pp", ".dpr",
    # Fortran
    ".f", ".f90", ".f95", ".f03", ".for", ".ftn",
    # COBOL
    ".cob", ".cbl",
    # Ada
    ".adb", ".ads",
    # D
    ".d",
    # Nim / Zig / Odin
    ".nim", ".zig",
    # TCL / AWK / Sed
    ".tcl", ".awk", ".sed",
    # Groovy
    ".groovy", ".gvy",
    # Misc
    ".lua", ".pl", ".pm", ".php", ".dart", ".scala",
    # Jupyter / Notebooks
    ".nb", ".wl",
}

# Archive extensions (will be extracted)
ARCHIVE_EXTENSIONS = {
    ".zip", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz",
    ".rar", ".7z", ".gz",
}

# All extensions we care about
ALL_EXTENSIONS = CODE_EXTENSIONS | ARCHIVE_EXTENSIONS

# Extension to language mapping for display
EXTENSION_LANGUAGE = {
    ".c": "C", ".h": "C/C++ Header", ".cpp": "C++", ".hpp": "C++ Header",
    ".cc": "C++", ".cxx": "C++", ".hh": "C++ Header",
    ".py": "Python", ".pyw": "Python", ".ipynb": "Jupyter Notebook",
    ".cs": "C#",
    ".java": "Java", ".jar": "Java Archive",
    ".js": "JavaScript", ".ts": "TypeScript", ".jsx": "React JSX",
    ".tsx": "React TSX", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
    ".swift": "Swift", ".kt": "Kotlin", ".kts": "Kotlin Script",
    ".sh": "Shell", ".bat": "Batch", ".ps1": "PowerShell",
    ".bash": "Bash", ".zsh": "Zsh",
    ".html": "HTML", ".htm": "HTML", ".css": "CSS",
    ".scss": "SCSS", ".sass": "Sass", ".less": "Less",
    ".sql": "SQL", ".asm": "Assembly", ".s": "Assembly",
    ".cmake": "CMake", ".makefile": "Makefile", ".mk": "Makefile",
    ".ino": "Arduino", ".vhd": "VHDL", ".vhdl": "VHDL",
    ".v": "Verilog", ".sv": "SystemVerilog",
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
    ".xml": "XML", ".toml": "TOML", ".ini": "INI", ".cfg": "Config",
    ".r": "R", ".m": "MATLAB/Objective-C",
    ".lua": "Lua", ".pro": "Prolog", ".pl": "Perl", ".pm": "Perl",
    ".php": "PHP", ".dart": "Dart", ".scala": "Scala",
    ".pro": "Prolog", ".P": "Prolog",
    ".lisp": "Lisp", ".lsp": "Lisp", ".cl": "Common Lisp",
    ".el": "Emacs Lisp", ".scm": "Scheme", ".ss": "Scheme", ".rkt": "Racket",
    ".hs": "Haskell", ".lhs": "Literate Haskell",
    ".ml": "OCaml", ".mli": "OCaml Interface",
    ".fs": "F#", ".fsx": "F# Script", ".fsi": "F# Signature",
    ".erl": "Erlang", ".hrl": "Erlang Header",
    ".ex": "Elixir", ".exs": "Elixir Script",
    ".clj": "Clojure", ".cljs": "ClojureScript",
    ".pas": "Pascal", ".pp": "Pascal", ".dpr": "Delphi",
    ".f": "Fortran", ".f90": "Fortran", ".f95": "Fortran",
    ".f03": "Fortran", ".for": "Fortran", ".ftn": "Fortran",
    ".cob": "COBOL", ".cbl": "COBOL",
    ".adb": "Ada", ".ads": "Ada",
    ".d": "D",
    ".nim": "Nim", ".zig": "Zig",
    ".tcl": "Tcl", ".awk": "AWK", ".sed": "Sed",
    ".groovy": "Groovy", ".gvy": "Groovy",
    ".nb": "Mathematica", ".wl": "Wolfram Language",
    ".exe": "Executable", ".com": "COM Executable", ".out": "Executable",
    ".bin": "Binary", ".elf": "ELF Binary",
    ".hex": "Hex File",
}

# Binary extensions (don't try to preview these)
BINARY_EXTENSIONS = {
    ".exe", ".com", ".out", ".bin", ".elf", ".hex", ".o", ".a", ".so", ".dll",
    ".jar", ".class", ".pyc", ".pyo",
    ".zip", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".rar", ".7z", ".gz",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
}

# Code runner settings
RUNNER_TIMEOUT = 5  # seconds
RUNNER_MAX_OUTPUT = 10000  # characters

# Web server
DEFAULT_PORT = 8080


def get_language(filename: str) -> str:
    """Get the language name from a filename."""
    ext = os.path.splitext(filename)[1].lower()
    # Handle special cases like Makefile
    base = os.path.basename(filename).lower()
    if base in ("makefile", "cmakelists.txt"):
        return "Makefile"
    return EXTENSION_LANGUAGE.get(ext, "Unknown")


def is_binary(filename: str) -> bool:
    """Check if a file is binary based on extension."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in BINARY_EXTENSIONS


def matches_programming_extension(filename: str) -> bool:
    """Check if a filename has a programming-related extension."""
    name_lower = filename.lower()
    # Check compound extensions like .tar.gz
    for ext in ALL_EXTENSIONS:
        if name_lower.endswith(ext):
            return True
    return False


# Keywords that indicate code pasted in email bodies (Gmail search terms)
BODY_CODE_KEYWORDS = [
    '"#include <stdio.h>"',
    '"#include <stdlib.h>"',
    '"#include <string.h>"',
    '"#include <math.h>"',
    '"#include <iostream>"',
    '"#include <vector>"',
    '"#include <algorithm>"',
    '"#include <bitset>"',
    '"#include <map>"',
    '"#include <set>"',
    '"#include <cstdio>"',
    '"using namespace std"',
    '"int main("',
    '"void main("',
    '"def __init__(self"',
    '"import numpy"',
    '"from collections import"',
    '"public static void main"',
    '"System.out.println"',
    '":-"',
    '"findall("',
    '"assert("',
    '"retract("',
]

# Language detection signatures — regex patterns scored against email bodies
LANGUAGE_SIGNATURES = {
    "cpp": [
        r"#include\s*<\w+(?:\.\w+)?>",
        r"using\s+namespace\s+std",
        r"std::\w+",
        r"cout\s*<<",
        r"cin\s*>>",
        r"int\s+main\s*\(",
        r"nullptr",
        r"template\s*<",
        r"vector\s*<",
        r"class\s+\w+\s*\{",
    ],
    "c": [
        r'#include\s*<stdio\.h>',
        r'#include\s*<stdlib\.h>',
        r'#include\s*<string\.h>',
        r"printf\s*\(",
        r"scanf\s*\(",
        r"malloc\s*\(",
        r"free\s*\(",
        r"int\s+main\s*\(",
        r"typedef\s+struct",
    ],
    "python": [
        r"def\s+\w+\s*\(.*\)\s*:",
        r"class\s+\w+.*:",
        r"import\s+\w+",
        r"from\s+\w+\s+import",
        r"if\s+__name__\s*==\s*['\"]__main__['\"]",
        r"print\s*\(",
        r"self\.\w+",
        r"lambda\s+\w+",
    ],
    "java": [
        r"public\s+static\s+void\s+main",
        r"System\.out\.print",
        r"public\s+class\s+\w+",
        r"private\s+\w+\s+\w+",
        r"import\s+java\.",
        r"@Override",
        r"new\s+\w+\s*\(",
    ],
    "prolog": [
        r"\w+\s*\(.*\)\s*:-",
        r":-\s*(module|use_module|ensure_loaded|dynamic|discontiguous)",
        r"findall\s*\(",
        r"member\s*\(",
        r"append\s*\(",
        r"write\s*\(",
        r"writeln\s*\(",
        r"assert[az]?\s*\(",
        r"retract\s*\(",
        r"not\s*\(",
        r"\w+\s*\(.*\)\s*\.",
    ],
}

# Map language keys to file extensions
LANGUAGE_TO_EXTENSION = {
    "cpp": ".cpp",
    "c": ".c",
    "python": ".py",
    "java": ".java",
    "prolog": ".pro",
}


def build_body_search_queries(max_query_length: int = 800) -> list[str]:
    """Build batched Gmail search queries for code keywords in email bodies."""
    queries = []
    current_parts = []
    current_length = 0

    for keyword in BODY_CODE_KEYWORDS:
        added_length = len(keyword) + (4 if current_parts else 0)  # " OR " separator

        if current_length + added_length > max_query_length and current_parts:
            queries.append(" OR ".join(current_parts))
            current_parts = [keyword]
            current_length = len(keyword)
        else:
            current_parts.append(keyword)
            current_length += added_length

    if current_parts:
        queries.append(" OR ".join(current_parts))

    return queries


# Gmail search terms for filename: queries (extensions without dots)
# Grouped to stay under Gmail's query length limit (~1000 chars)
def build_filename_queries(max_query_length: int = 800) -> list[str]:
    """Build batched Gmail filename: search queries from our extensions."""
    # Deduplicate: strip dots, get unique search terms
    search_terms = set()
    for ext in ALL_EXTENSIONS:
        # e.g. ".tar.gz" -> "tar.gz", ".py" -> "py"
        term = ext.lstrip(".")
        search_terms.add(term)

    queries = []
    current_parts = []
    current_length = 0

    for term in sorted(search_terms):
        part = f"filename:{term}"
        added_length = len(part) + (4 if current_parts else 0)  # " OR " separator

        if current_length + added_length > max_query_length and current_parts:
            queries.append(" OR ".join(current_parts))
            current_parts = [part]
            current_length = len(part)
        else:
            current_parts.append(part)
            current_length += added_length

    if current_parts:
        queries.append(" OR ".join(current_parts))

    return queries
