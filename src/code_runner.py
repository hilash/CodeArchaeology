"""Sandboxed code execution for the web simulator."""

import os
import shutil
import subprocess
import tempfile
import logging
from pathlib import Path

from src.config import RUNNER_TIMEOUT, RUNNER_MAX_OUTPUT

logger = logging.getLogger(__name__)


def run_python(code: str, stdin_input: str = "") -> dict:
    """
    Run Python code in a sandboxed subprocess.

    Returns dict with: success, stdout, stderr, error
    """
    with tempfile.TemporaryDirectory(prefix="coderun_") as tmpdir:
        script_path = Path(tmpdir) / "script.py"
        script_path.write_text(code)

        try:
            result = subprocess.run(
                ["python3", str(script_path)],
                capture_output=True,
                text=True,
                input=stdin_input,
                timeout=RUNNER_TIMEOUT,
                cwd=tmpdir,
                env={
                    "PATH": os.environ.get("PATH", "/usr/bin:/usr/local/bin"),
                    "HOME": tmpdir,
                    "TMPDIR": tmpdir,
                },
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:RUNNER_MAX_OUTPUT],
                "stderr": result.stderr[:RUNNER_MAX_OUTPUT],
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {RUNNER_TIMEOUT} seconds.",
                "return_code": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
            }


def run_c_cpp(code: str, language: str = "c", stdin_input: str = "") -> dict:
    """
    Compile and run C/C++ code in a sandboxed subprocess.

    Args:
        code: Source code string
        language: "c" or "cpp"
    """
    compiler = "gcc" if language == "c" else "g++"

    # Check compiler availability
    if not shutil.which(compiler):
        return {
            "success": False,
            "stdout": "",
            "stderr": f"{compiler} not found. Install it to run {language.upper()} code.",
            "return_code": -1,
        }

    with tempfile.TemporaryDirectory(prefix="coderun_") as tmpdir:
        ext = ".c" if language == "c" else ".cpp"
        source_path = Path(tmpdir) / f"program{ext}"
        binary_path = Path(tmpdir) / "program"
        source_path.write_text(code)

        # Compile
        try:
            compile_result = subprocess.run(
                [compiler, str(source_path), "-o", str(binary_path), "-lm"],
                capture_output=True,
                text=True,
                timeout=RUNNER_TIMEOUT,
                cwd=tmpdir,
            )
            if compile_result.returncode != 0:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Compilation failed:\n{compile_result.stderr[:RUNNER_MAX_OUTPUT]}",
                    "return_code": compile_result.returncode,
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Compilation timed out after {RUNNER_TIMEOUT} seconds.",
                "return_code": -1,
            }

        # Run
        try:
            result = subprocess.run(
                [str(binary_path)],
                capture_output=True,
                text=True,
                input=stdin_input,
                timeout=RUNNER_TIMEOUT,
                cwd=tmpdir,
                env={
                    "PATH": "/usr/bin:/usr/local/bin",
                    "HOME": tmpdir,
                    "TMPDIR": tmpdir,
                },
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:RUNNER_MAX_OUTPUT],
                "stderr": result.stderr[:RUNNER_MAX_OUTPUT],
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {RUNNER_TIMEOUT} seconds.",
                "return_code": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
            }


def run_code(code: str, filename: str, stdin_input: str = "") -> dict:
    """
    Run code based on file extension.

    Returns dict with: success, stdout, stderr, return_code, runnable
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext in (".py", ".pyw"):
        result = run_python(code, stdin_input)
        result["runnable"] = True
        return result
    elif ext == ".c":
        result = run_c_cpp(code, "c", stdin_input)
        result["runnable"] = True
        return result
    elif ext in (".cpp", ".cc", ".cxx"):
        result = run_c_cpp(code, "cpp", stdin_input)
        result["runnable"] = True
        return result
    else:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Running {ext} files is not supported. View-only mode.",
            "return_code": -1,
            "runnable": False,
        }
