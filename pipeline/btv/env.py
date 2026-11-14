"""env.py - read settings such as API keys from pipeline/.env.

The file holds one NAME=value per line; blank lines and lines starting with # are skipped.
A variable already set in the environment (for example a GitHub Actions secret) wins.
pipeline/.env is never committed (.gitignore); pipeline/.env.example shows the names.
"""

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip().strip('"').strip("'")
        if value and not os.environ.get(name):
            os.environ[name] = value
