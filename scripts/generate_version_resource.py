from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "backend" / "version.py"
VERSION_RE = re.compile(r'VERSION\s*=\s*"(\d+\.\d+\.\d+)"')


def read_version() -> str:
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = VERSION_RE.search(content)
    if not match:
        raise ValueError("No se encontró VERSION en backend/version.py")
    return match.group(1)


def build_resource(version: str) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', 'Synyster Rick'),
            StringStruct('FileDescription', 'LimpiarAxess'),
            StringStruct('FileVersion', '{version}'),
            StringStruct('InternalName', 'LimpiarAxess'),
            StringStruct('OriginalFilename', 'LimpiarAxess.exe'),
            StringStruct('ProductName', 'LimpiarAxess'),
            StringStruct('ProductVersion', '{version}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el recurso de versión de Windows para PyInstaller")
    parser.add_argument("output", help="Ruta de salida para el archivo version_info.txt")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_resource(read_version()), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
