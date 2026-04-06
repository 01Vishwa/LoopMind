"""CodeExecutor — sandboxed subprocess-based Python code runner.

Executes generated Python scripts in a temporary directory with a timeout.
Captures stdout, stderr, return code, and any artifact files written to
the ``./outputs/`` sub-directory (fix #4).

Docker-based sandbox is available in Steps 3 of the refactor when Docker
Desktop is present; this module falls back to subprocess automatically.
"""

import base64
import logging
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict

from core.config import EXECUTION_TIMEOUT_SECONDS

logger = logging.getLogger("uvicorn.info")


class ExecutionResult:
    """Result of a sandboxed code execution.

    Attributes:
        stdout: Captured standard output.
        stderr: Captured standard error.
        success: True if the process exited with code 0.
        returncode: The raw subprocess return code.
        artifacts: Dict mapping filename → base64-encoded content for every
            file written to the script's ``./outputs/`` directory.
    """

    def __init__(self, stdout: str, stderr: str, returncode: int) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.success = returncode == 0
        self.artifacts: Dict[str, str] = {}

    def combined_output(self) -> str:
        """Returns stdout and stderr concatenated for LLM consumption."""
        parts = []
        if self.stdout.strip():
            parts.append(f"[STDOUT]\n{self.stdout.strip()}")
        if self.stderr.strip():
            parts.append(f"[STDERR]\n{self.stderr.strip()}")
        if not parts:
            return "(no output)"
        return "\n\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Serialises the result to a plain dictionary.

        Returns:
            Serialisable execution result (artifacts excluded for brevity).
        """
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "success": self.success,
            "returncode": self.returncode,
            "artifact_count": len(self.artifacts),
        }


class CodeExecutor:
    """Runs Python scripts in a sandboxed subprocess with a strict timeout.

    Creates an ``outputs/`` sub-directory inside the temp working directory
    so generated code can write plots and CSVs there.  After execution, all
    files in ``outputs/`` are base64-encoded and attached to ``ExecutionResult.artifacts``.
    """

    def run(self, code: str) -> ExecutionResult:
        """Writes code to a temp file and executes it.

        The script runs under the same Python interpreter that is hosting
        FastAPI so that all installed packages (pandas, matplotlib, etc.)
        are available.

        Args:
            code: Python source code to execute.

        Returns:
            ExecutionResult: Captured outputs, success flag, and any artifacts.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Pre-create outputs/ so generated code can always write there
            outputs_dir = os.path.join(tmpdir, "outputs")
            os.makedirs(outputs_dir, exist_ok=True)

            script_path = os.path.join(tmpdir, "ds_star_script.py")
            with open(script_path, "w", encoding="utf-8") as fh:
                fh.write(code)

            logger.info(
                "[Executor] Running script (%d chars) in %s", len(code), tmpdir
            )

            try:
                proc = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=EXECUTION_TIMEOUT_SECONDS,
                    cwd=tmpdir,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
                result = ExecutionResult(
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    returncode=proc.returncode,
                )
            except subprocess.TimeoutExpired:
                logger.warning(
                    "[Executor] Script timed out after %ds.", EXECUTION_TIMEOUT_SECONDS
                )
                result = ExecutionResult(
                    stdout="",
                    stderr=f"Execution timed out after {EXECUTION_TIMEOUT_SECONDS} seconds.",
                    returncode=1,
                )
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("[Executor] Unexpected error: %s", exc)
                result = ExecutionResult(
                    stdout="",
                    stderr=f"Executor error: {str(exc)}",
                    returncode=1,
                )

            # ── Collect artifact files from outputs/ ──────────────────────────
            result.artifacts = _collect_artifacts(outputs_dir)

            logger.info(
                "[Executor] Done — success=%s, stdout=%d chars, stderr=%d chars, artifacts=%d",
                result.success,
                len(result.stdout),
                len(result.stderr),
                len(result.artifacts),
            )
            return result


def _collect_artifacts(outputs_dir: str) -> Dict[str, str]:
    """Reads every file in ``outputs_dir`` and base64-encodes it.

    Args:
        outputs_dir: Absolute path to the outputs directory.

    Returns:
        Dict mapping filename (no path) → base64-encoded string.
    """
    artifacts: Dict[str, str] = {}
    if not os.path.isdir(outputs_dir):
        return artifacts

    for fname in os.listdir(outputs_dir):
        fpath = os.path.join(outputs_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "rb") as fh:
                artifacts[fname] = base64.b64encode(fh.read()).decode("utf-8")
            logger.info("[Executor] Collected artifact: %s", fname)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("[Executor] Could not read artifact %s: %s", fname, exc)

    return artifacts
