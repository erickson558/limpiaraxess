from __future__ import annotations

import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from backend.paths import get_runtime_dir

StatusCallback = Callable[[str], None]


@dataclass
class CleanResult:
    files_deleted: int
    dirs_deleted: int
    errors: int
    elapsed_seconds: float


class CleanerService:
    def __init__(self, runtime_dir: Path | None = None) -> None:
        self._runtime_dir = (runtime_dir or get_runtime_dir()).resolve()

    def validate_target(self, target_path: str) -> tuple[bool, str]:
        if not target_path.strip():
            return False, "Selecciona una carpeta válida."

        target = Path(target_path).expanduser()
        try:
            resolved = target.resolve(strict=True)
        except FileNotFoundError:
            return False, "La ruta no existe."
        except OSError:
            return False, "No se pudo resolver la ruta."

        if not resolved.is_dir():
            return False, "La ruta seleccionada no es una carpeta."

        if self._is_root_path(resolved):
            return False, "Por seguridad no se permite limpiar la raíz del disco."

        if resolved == Path.home().resolve():
            return False, "Por seguridad no se permite limpiar el HOME del usuario."

        if resolved == self._runtime_dir:
            return False, "Por seguridad no se permite limpiar la carpeta de la aplicación."

        forbidden = self._forbidden_windows_paths()
        if any(resolved == entry for entry in forbidden):
            return False, "Por seguridad no se permite limpiar carpetas críticas del sistema."

        return True, "Ruta validada."

    def clear_directory_contents(self, target_path: str, status_cb: StatusCallback | None = None) -> CleanResult:
        status_cb = status_cb or (lambda _: None)
        valid, reason = self.validate_target(target_path)
        if not valid:
            raise ValueError(reason)

        target = Path(target_path).resolve(strict=True)
        start = time.perf_counter()
        files_deleted = 0
        dirs_deleted = 0
        errors = 0
        status_cb(f"Iniciando limpieza segura en: {target}")

        for entry in target.iterdir():
            try:
                fd, dd, err = self._delete_entry(entry)
                files_deleted += fd
                dirs_deleted += dd
                errors += err
                total = files_deleted + dirs_deleted
                if total % 100 == 0 and total > 0:
                    status_cb(f"Progreso: {files_deleted} archivos, {dirs_deleted} carpetas eliminadas.")
            except OSError as exc:
                errors += 1
                status_cb(f"Error en '{entry}': {exc}")

        elapsed = time.perf_counter() - start
        status_cb(
            "Limpieza finalizada. "
            f"Archivos: {files_deleted}, Carpetas: {dirs_deleted}, Errores: {errors}, "
            f"Tiempo: {elapsed:.2f}s"
        )
        return CleanResult(
            files_deleted=files_deleted,
            dirs_deleted=dirs_deleted,
            errors=errors,
            elapsed_seconds=elapsed,
        )

    def _delete_entry(self, path: Path) -> tuple[int, int, int]:
        if path.is_symlink():
            if self._unlink_with_retry(path):
                return 1, 0, 0
            return 0, 0, 1

        if path.is_file():
            if self._unlink_with_retry(path):
                return 1, 0, 0
            return 0, 0, 1

        if not path.is_dir():
            if self._unlink_with_retry(path):
                return 1, 0, 0
            return 0, 0, 1

        files_deleted = 0
        dirs_deleted = 0
        errors = 0

        try:
            with os.scandir(path) as iterator:
                for item in iterator:
                    child = Path(item.path)
                    fd, dd, err = self._delete_entry(child)
                    files_deleted += fd
                    dirs_deleted += dd
                    errors += err
        except OSError:
            return files_deleted, dirs_deleted, errors + 1

        if self._rmdir_with_retry(path):
            dirs_deleted += 1
        else:
            errors += 1

        return files_deleted, dirs_deleted, errors

    @staticmethod
    def _make_writable(path: Path) -> None:
        current_mode = path.stat(follow_symlinks=False).st_mode
        path.chmod(current_mode | stat.S_IWUSR)

    def _unlink_with_retry(self, path: Path) -> bool:
        try:
            path.unlink(missing_ok=False)
            return True
        except OSError:
            try:
                self._make_writable(path)
                path.unlink(missing_ok=False)
                return True
            except OSError:
                return False

    def _rmdir_with_retry(self, path: Path) -> bool:
        try:
            path.rmdir()
            return True
        except OSError:
            try:
                self._make_writable(path)
                path.rmdir()
                return True
            except OSError:
                return False

    @staticmethod
    def _is_root_path(path: Path) -> bool:
        return str(path) == path.anchor

    @staticmethod
    def _forbidden_windows_paths() -> set[Path]:
        candidates = []
        for env_name in ("WINDIR", "ProgramFiles", "ProgramData", "SystemDrive"):
            value = os.environ.get(env_name)
            if value:
                try:
                    candidates.append(Path(value).resolve())
                except OSError:
                    continue
        users_dir = os.environ.get("SystemDrive")
        if users_dir:
            try:
                candidates.append((Path(users_dir) / "Users").resolve())
            except OSError:
                pass
        return set(candidates)
