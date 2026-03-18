from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "backend" / "version.py"
CONFIG_TEMPLATE_FILE = ROOT / "config.example.json"
PYPROJECT_FILE = ROOT / "pyproject.toml"
README_FILE = ROOT / "README.md"

VERSION_RE = re.compile(r'VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"')
PYPROJECT_VERSION_RE = re.compile(r'(?m)^(version\s*=\s*")(\d+\.\d+\.\d+)(")$')
README_VERSION_RE = re.compile(r"(?m)^(#\s+LimpiarAxess\s+v)(\d+\.\d+\.\d+)$")


def _replace_version(path: Path, pattern: re.Pattern[str], replacement: str, label: str) -> None:
    content = path.read_text(encoding="utf-8")
    updated, count = pattern.subn(replacement, content, count=1)
    if count != 1:
        raise ValueError(f"No se pudo actualizar la versión en {label}")
    path.write_text(updated, encoding="utf-8", newline="\n")


def bump_version(bump_type: str = "patch") -> str:
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = VERSION_RE.search(content)
    if not match:
        raise ValueError("No se encontró VERSION en backend/version.py")

    major, minor, patch = (int(part) for part in match.groups())

    if bump_type == "major":
        new_version = f"{major + 1}.0.0"
    elif bump_type == "minor":
        new_version = f"{major}.{minor + 1}.0"
    else:
        new_version = f"{major}.{minor}.{patch + 1}"

    _replace_version(VERSION_FILE, VERSION_RE, f'VERSION = "{new_version}"', "backend/version.py")

    if CONFIG_TEMPLATE_FILE.exists():
        data = json.loads(CONFIG_TEMPLATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data["version"] = new_version
            CONFIG_TEMPLATE_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
                newline="\n",
            )

    if PYPROJECT_FILE.exists():
        _replace_version(PYPROJECT_FILE, PYPROJECT_VERSION_RE, rf'\g<1>{new_version}\g<3>', "pyproject.toml")

    if README_FILE.exists():
        _replace_version(README_FILE, README_VERSION_RE, rf'\g<1>{new_version}', "README.md")

    return new_version


def main() -> None:
    parser = argparse.ArgumentParser(description="Incrementar versión semántica")
    parser.add_argument(
        "bump_type",
        nargs="?",
        default="patch",
        choices=["major", "minor", "patch"],
        help="Tipo de incremento: major, minor o patch",
    )
    args = parser.parse_args()

    new_version = bump_version(args.bump_type)
    print(new_version)


if __name__ == "__main__":
    main()
