from __future__ import annotations

from pathlib import Path
import os


def load_dotenv(
    dotenv_path: str | os.PathLike[str] | None = None,
    *,
    override: bool = False,
) -> None:
    """Load environment variables from a .env file (minimal, stdlib-only).

    - Lines like KEY=VALUE are supported.
    - Blank lines and comments starting with # are ignored.
    - Values may be wrapped in single/double quotes.
        - By default, existing os.environ keys are NOT overwritten.
            Set override=True to make the .env file take precedence for this process.

    This intentionally avoids third-party deps (e.g., python-dotenv).
    """

    path = Path(dotenv_path) if dotenv_path is not None else (Path.cwd() / ".env")
    if not path.exists() or not path.is_file():
        return

    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]

        if override:
            os.environ[key] = value
        else:
            os.environ.setdefault(key, value)
