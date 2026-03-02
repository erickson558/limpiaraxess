import stat
import tempfile
import unittest
from pathlib import Path

from backend.cleaner_service import CleanerService


class CleanerServiceTests(unittest.TestCase):
    def test_clear_directory_contents_deletes_nested_tree_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "target"
            runtime = Path(root) / "runtime"
            target.mkdir()
            runtime.mkdir()

            nested = target / "a" / "b" / "c"
            nested.mkdir(parents=True)
            (target / "root.txt").write_text("x", encoding="utf-8")
            (target / "a" / "a.txt").write_text("x", encoding="utf-8")
            (target / "a" / "b" / "b.txt").write_text("x", encoding="utf-8")
            (nested / "c.txt").write_text("x", encoding="utf-8")

            service = CleanerService(runtime_dir=runtime)
            result = service.clear_directory_contents(str(target))

            self.assertEqual(result.files_deleted, 4)
            self.assertEqual(result.dirs_deleted, 3)
            self.assertEqual(result.errors, 0)
            self.assertTrue(target.exists())
            self.assertEqual(list(target.iterdir()), [])

    def test_clear_directory_contents_deletes_readonly_file(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "target"
            runtime = Path(root) / "runtime"
            target.mkdir()
            runtime.mkdir()

            readonly_file = target / "readonly.txt"
            readonly_file.write_text("x", encoding="utf-8")
            readonly_file.chmod(stat.S_IREAD)

            service = CleanerService(runtime_dir=runtime)
            result = service.clear_directory_contents(str(target))

            self.assertEqual(result.files_deleted, 1)
            self.assertEqual(result.dirs_deleted, 0)
            self.assertEqual(result.errors, 0)
            self.assertTrue(target.exists())
            self.assertEqual(list(target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
