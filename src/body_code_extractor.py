"""Extract code snippets from email body text."""

import logging
import re

from src.config import LANGUAGE_SIGNATURES, LANGUAGE_TO_EXTENSION

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str | None:
    """
    Score body text against LANGUAGE_SIGNATURES patterns.

    Returns the best-matching language key, or None if no confident match.
    """
    if not text:
        return None

    scores: dict[str, int] = {}
    for lang, patterns in LANGUAGE_SIGNATURES.items():
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, text)
            score += len(matches)
        if score > 0:
            scores[lang] = score

    if not scores:
        return None

    # C and C++ share many patterns — if both match, prefer the higher score.
    # If C++ scores >= C, pick C++ (C++ is a superset).
    if "c" in scores and "cpp" in scores and scores["cpp"] >= scores["c"]:
        del scores["c"]

    best = max(scores, key=scores.get)
    # Require at least 2 pattern matches for confidence
    if scores[best] < 2:
        return None

    return best


def extract_code_from_body(body: str) -> list[dict]:
    """
    Detect language and extract code from an email body.

    Returns a list of dicts:
        [{"code": str, "language": str, "extension": str, "filename": str}]
    Returns empty list if no code detected.
    """
    if not body or len(body.strip()) < 20:
        return []

    language = detect_language(body)
    if not language:
        return []

    code = _extract_code_block(body, language)
    if not code or len(code.strip()) < 10:
        return []

    extension = LANGUAGE_TO_EXTENSION.get(language, ".txt")
    filename = f"body_code{extension}"

    return [{
        "code": code,
        "language": language,
        "extension": extension,
        "filename": filename,
    }]


def _extract_code_block(body: str, language: str) -> str:
    """
    Find the contiguous block of code-like lines in the body.

    Strategy: find the first and last lines that look like code,
    then return everything between them (inclusive).
    """
    lines = body.split("\n")
    code_indices = []

    for i, line in enumerate(lines):
        if _is_code_line(line, language):
            code_indices.append(i)

    if not code_indices:
        return ""

    first = code_indices[0]
    last = code_indices[-1]

    # Extract the block, filtering out obvious email prose lines
    block_lines = []
    for i in range(first, last + 1):
        line = lines[i]
        # Skip obvious email signature / prose lines within the block
        if _is_email_noise(line):
            continue
        block_lines.append(line)

    return "\n".join(block_lines)


def _is_code_line(line: str, language: str) -> bool:
    """
    Heuristic: does this line look like code?

    Checks for language-specific patterns, structural markers (braces,
    semicolons, indentation), and common code constructs.
    """
    stripped = line.strip()

    # Empty lines are not evidence of code on their own
    if not stripped:
        return False

    # Check language-specific signatures
    for pattern in LANGUAGE_SIGNATURES.get(language, []):
        if re.search(pattern, line):
            return True

    # Common C/C++/Java structural markers
    if language in ("c", "cpp", "java"):
        if stripped in ("{", "}", "};", "});"):
            return True
        if stripped.endswith(";") and len(stripped) > 2:
            return True
        if stripped.startswith("//"):
            return True
        if stripped.startswith("/*") or stripped.startswith("*") or stripped.endswith("*/"):
            return True
        if re.match(r"^\s*(int|char|float|double|long|void|bool|unsigned|auto|const)\s+", line):
            return True
        if re.match(r"^\s*(for|while|if|else|return|switch|case|break|continue)\s*[\({]?", line):
            return True

    # C++ specific
    if language == "cpp":
        if re.match(r"^\s*(class|struct|namespace|template|typename|virtual)\s+", line):
            return True

    # Python structural markers
    if language == "python":
        if re.match(r"^\s+(pass|return|yield|raise|break|continue)\b", line):
            return True
        if re.match(r"^\s*(for|while|if|elif|else|try|except|finally|with)\s+.*:", line):
            return True
        if stripped.startswith("#") and len(stripped) > 1:
            return True
        # Indented lines (4 spaces or tab) suggest code
        if re.match(r"^(\t|    )\S", line):
            return True

    # Java specific
    if language == "java":
        if re.match(r"^\s*(public|private|protected|static|final|abstract)\s+", line):
            return True

    # Prolog structural markers
    if language == "prolog":
        if stripped.endswith(".") and len(stripped) > 2:
            return True
        if ":-" in stripped:
            return True
        if stripped.startswith("%"):
            return True
        if stripped.startswith("/*") or stripped.startswith("*") or stripped.endswith("*/"):
            return True

    return False


def _is_email_noise(line: str) -> bool:
    """Detect email prose, signatures, and other non-code noise."""
    stripped = line.strip()

    if not stripped:
        return False  # Keep blank lines for formatting

    # Email signature markers
    if stripped.startswith("--"):
        # Could be a comment too, so only match the exact signature marker
        if stripped == "--" or stripped == "-- ":
            return True

    # Common email patterns
    noise_patterns = [
        r"^Sent from my ",
        r"^On .+ wrote:$",
        r"^From:\s",
        r"^To:\s",
        r"^Subject:\s",
        r"^Date:\s",
        r"^>+\s",  # Quoted text
        r"^Begin forwarded message",
    ]
    for pattern in noise_patterns:
        if re.match(pattern, stripped, re.IGNORECASE):
            return True

    return False
