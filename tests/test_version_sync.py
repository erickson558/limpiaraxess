import json
import re
import unittest
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "backend" / "version.py"
README_FILE = ROOT / "README.md"
PYPROJECT_FILE = ROOT / "pyproject.toml"
CONFIG_TEMPLATE_FILE = ROOT / "config.example.json"
VERSION_RE = re.compile(r'VERSION\s*=\s*"(\d+\.\d+\.\d+)"')
README_RE = re.compile(r"^#\s+LimpiarAxess\s+v(\d+\.\d+\.\d+)$", re.MULTILINE)


class VersionSyncTests(unittest.TestCase):
    def test_version_is_synchronized_across_project_metadata(self) -> None:
        version_content = VERSION_FILE.read_text(encoding="utf-8")
        version_match = VERSION_RE.search(version_content)
        self.assertIsNotNone(version_match)
        version = version_match.group(1)

        pyproject = tomllib.loads(PYPROJECT_FILE.read_text(encoding="utf-8"))
        self.assertEqual(version, pyproject["project"]["version"])

        config_template = json.loads(CONFIG_TEMPLATE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(version, config_template["version"])

        readme_match = README_RE.search(README_FILE.read_text(encoding="utf-8"))
        self.assertIsNotNone(readme_match)
        self.assertEqual(version, readme_match.group(1))


if __name__ == "__main__":
    unittest.main()
