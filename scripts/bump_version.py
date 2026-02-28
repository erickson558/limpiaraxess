from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "backend" / "version.py"
CONFIG_FILE = ROOT / "config.json"

VERSION_RE = re.compile(r'VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"')


def main() -> None:
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = VERSION_RE.search(content)
    if not match:
        raise ValueError("No se encontró VERSION en backend/version.py")

    major, minor, patch = (int(part) for part in match.groups())
    new_version = f"{major}.{minor}.{patch + 1}"
    new_content = VERSION_RE.sub(f'VERSION = "{new_version}"', content, count=1)
    VERSION_FILE.write_text(new_content, encoding="utf-8", newline="\n")

    if CONFIG_FILE.exists():
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data["version"] = new_version
            CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")

    print(new_version)


if __name__ == "__main__":
    main()
