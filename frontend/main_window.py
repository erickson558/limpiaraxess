from __future__ import annotations

import datetime as dt
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any

from backend.cleaner_service import CleanResult, CleanerService
from backend.config_manager import ConfigManager
from backend.logger_service import build_logger
from backend.security import hash_password, verify_password
from backend.version import VERSION


class MainWindow:
    def __init__(self) -> None:
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get()
        self.logger = build_logger()
        self.cleaner = CleanerService()

        self.root = tk.Tk()
        self.root.title(f"LimpiarAxess v{VERSION}")
        self.root.geometry(self.config.window_geometry)
        self.root.minsize(760, 360)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        self._queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._is_running = False
        self._show_password = False
        self._base_status = "Aplicación lista."
        self._configure_job: str | None = None
        self._save_job: str | None = None
        self._countdown_job: str | None = None
        self._countdown_remaining = int(self.config.auto_close_seconds)

        self.target_var = tk.StringVar(value=self.config.target_path)
        self.auto_start_var = tk.BooleanVar(value=self.config.auto_start)
        self.auto_close_enabled_var = tk.BooleanVar(value=self.config.auto_close_enabled)
        self.auto_close_seconds_var = tk.IntVar(value=self.config.auto_close_seconds)
        self.password_required_var = tk.BooleanVar(value=self.config.password_required)
        self.password_var = tk.StringVar(value="")

        self._build_menu()
        self._build_ui()
        self._bind_shortcuts()
        self._bind_autosave()

        self.root.bind("<Configure>", self._on_window_configure)
        self._process_queue()
        self._sync_countdown_state(force_reset=True)

        if self.auto_start_var.get():
            self.root.after(700, self.start_cleanup)

    def run(self) -> None:
        self.logger.info("Aplicación iniciada. Versión %s", VERSION)
        self.root.mainloop()

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Iniciar limpieza", accelerator="F5", command=self.start_cleanup)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", accelerator="Ctrl+Q", command=self.on_exit)
        menu_bar.add_cascade(label="Archivo", menu=file_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="About", accelerator="F1", command=self.show_about_dialog)
        menu_bar.add_cascade(label="Ayuda", menu=help_menu)

        self.root.config(menu=menu_bar)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        title = ttk.Label(
            outer,
            text=f"LimpiarAxess | Versión {VERSION}",
            font=("Segoe UI", 12, "bold"),
        )
        title.pack(anchor="w", pady=(0, 10))

        path_frame = ttk.Frame(outer)
        path_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(path_frame, text="Carpeta a limpiar:").pack(anchor="w")
        path_row = ttk.Frame(path_frame)
        path_row.pack(fill="x", pady=(4, 0))
        self.path_entry = ttk.Entry(path_row, textvariable=self.target_var)
        self.path_entry.pack(side="left", fill="x", expand=True)
        self.browse_button = ttk.Button(path_row, text="Examinar...", command=self.select_folder)
        self.browse_button.pack(side="left", padx=(8, 0))

        options_frame = ttk.LabelFrame(outer, text="Parámetros")
        options_frame.pack(fill="x", pady=(0, 10))

        self.auto_start_check = ttk.Checkbutton(
            options_frame,
            text="Auto iniciar al abrir",
            variable=self.auto_start_var,
            command=self._schedule_save,
        )
        self.auto_start_check.grid(row=0, column=0, sticky="w", padx=8, pady=6)

        self.auto_close_check = ttk.Checkbutton(
            options_frame,
            text="Habilitar autocierre",
            variable=self.auto_close_enabled_var,
            command=self._on_auto_close_toggle,
        )
        self.auto_close_check.grid(row=0, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(options_frame, text="Segundos de autocierre:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.auto_close_spin = ttk.Spinbox(
            options_frame,
            from_=5,
            to=86400,
            textvariable=self.auto_close_seconds_var,
            width=10,
            command=self._on_auto_close_seconds_changed,
        )
        self.auto_close_spin.grid(row=1, column=1, sticky="w", padx=8, pady=6)

        self.password_required_check = ttk.Checkbutton(
            options_frame,
            text="Requerir password para limpiar",
            variable=self.password_required_var,
            command=self._schedule_save,
        )
        self.password_required_check.grid(row=2, column=0, sticky="w", padx=8, pady=6)

        password_row = ttk.Frame(options_frame)
        password_row.grid(row=2, column=1, sticky="we", padx=8, pady=6)

        self.password_entry = ttk.Entry(password_row, textvariable=self.password_var, show="*")
        self.password_entry.pack(side="left", fill="x", expand=True)

        self.show_password_btn = ttk.Button(password_row, text="Mostrar", width=10, command=self.toggle_password_visibility)
        self.show_password_btn.pack(side="left", padx=(6, 0))

        self.save_password_btn = ttk.Button(password_row, text="Guardar password", command=self.save_password_hash)
        self.save_password_btn.pack(side="left", padx=(6, 0))

        options_frame.columnconfigure(1, weight=1)

        actions_frame = ttk.Frame(outer)
        actions_frame.pack(fill="x", pady=(0, 10))

        self.start_button = ttk.Button(actions_frame, text="Iniciar limpieza", command=self.start_cleanup)
        self.start_button.pack(side="left")

        self.exit_button = ttk.Button(actions_frame, text="Salir", command=self.on_exit)
        self.exit_button.pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 10))

        self.status_label = ttk.Label(outer, text="", anchor="w")
        self.status_label.pack(fill="x")

        self._set_status("Configuración cargada.")

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-o>", lambda _: self.select_folder())
        self.root.bind("<Control-q>", lambda _: self.on_exit())
        self.root.bind("<F5>", lambda _: self.start_cleanup())
        self.root.bind("<F1>", lambda _: self.show_about_dialog())
        self.root.bind("<Control-g>", lambda _: self.save_password_hash())
        self.root.bind("<Alt-s>", lambda _: self.start_cleanup())
        self.root.bind("<Alt-x>", lambda _: self.on_exit())

    def _bind_autosave(self) -> None:
        self.target_var.trace_add("write", lambda *_: self._schedule_save())
        self.auto_start_var.trace_add("write", lambda *_: self._schedule_save())
        self.auto_close_enabled_var.trace_add("write", lambda *_: self._schedule_save())
        self.auto_close_seconds_var.trace_add("write", lambda *_: self._on_auto_close_seconds_changed())
        self.password_required_var.trace_add("write", lambda *_: self._schedule_save())

    def _schedule_save(self) -> None:
        if self._save_job:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(180, self._persist_config)

    def _persist_config(self) -> None:
        self._save_job = None
        geometry = self.root.winfo_geometry()
        self.config = self.config_manager.update(
            target_path=self.target_var.get().strip(),
            auto_start=self.auto_start_var.get(),
            auto_close_enabled=self.auto_close_enabled_var.get(),
            auto_close_seconds=self._safe_seconds(),
            window_geometry=geometry,
            password_required=self.password_required_var.get(),
        )

    def _on_window_configure(self, _event: tk.Event) -> None:
        if self._configure_job:
            self.root.after_cancel(self._configure_job)
        self._configure_job = self.root.after(400, self._schedule_save)

    def _on_auto_close_toggle(self) -> None:
        self._schedule_save()
        self._sync_countdown_state(force_reset=True)

    def _on_auto_close_seconds_changed(self) -> None:
        self._schedule_save()
        self._sync_countdown_state(force_reset=True)

    def _safe_seconds(self) -> int:
        try:
            value = int(self.auto_close_seconds_var.get())
        except (TypeError, tk.TclError, ValueError):
            value = 60
        clamped = max(5, min(value, 86_400))
        if clamped != value:
            self.auto_close_seconds_var.set(clamped)
        return clamped

    def _sync_countdown_state(self, force_reset: bool = False) -> None:
        if self._countdown_job:
            self.root.after_cancel(self._countdown_job)
            self._countdown_job = None

        if not self.auto_close_enabled_var.get():
            self._refresh_status_text()
            return

        seconds = self._safe_seconds()
        if force_reset or self._countdown_remaining <= 0:
            self._countdown_remaining = seconds

        self._tick_countdown()

    def _tick_countdown(self) -> None:
        if not self.auto_close_enabled_var.get():
            self._refresh_status_text()
            return

        if self._is_running:
            self._refresh_status_text(extra="Autocierre pausado durante limpieza.")
            self._countdown_job = self.root.after(1000, self._tick_countdown)
            return

        if self._countdown_remaining <= 0:
            self._set_status("Autocierre ejecutado.")
            self.logger.info("Autocierre ejecutado.")
            self.root.after(200, self.root.destroy)
            return

        self._refresh_status_text(extra=f"Autocierre en {self._countdown_remaining}s")
        self._countdown_remaining -= 1
        self._countdown_job = self.root.after(1000, self._tick_countdown)

    def select_folder(self) -> None:
        selected = filedialog.askdirectory(title="Selecciona carpeta para limpiar")
        if not selected:
            return
        self.target_var.set(str(Path(selected)))
        self._set_status(f"Carpeta seleccionada: {selected}")

    def toggle_password_visibility(self) -> None:
        self._show_password = not self._show_password
        self.password_entry.configure(show="" if self._show_password else "*")
        self.show_password_btn.configure(text="Ocultar" if self._show_password else "Mostrar")

    def save_password_hash(self) -> None:
        plain = self.password_var.get()
        if len(plain) < 4:
            self._set_status("El password debe tener al menos 4 caracteres.")
            return

        hashed, salt = hash_password(plain)
        self.config = self.config_manager.update(password_hash=hashed, password_salt=salt)
        self.password_var.set("")
        self._set_status("Password guardado de forma segura.")
        self.logger.info("Password de protección actualizado.")

    def start_cleanup(self) -> None:
        if self._is_running:
            self._set_status("La limpieza ya está en ejecución.")
            return

        target = self.target_var.get().strip()
        is_valid, reason = self.cleaner.validate_target(target)
        if not is_valid:
            self._set_status(reason)
            return

        cfg = self.config_manager.get()
        if self.password_required_var.get():
            if not cfg.password_hash or not cfg.password_salt:
                self._set_status("Activa protección por password, pero no hay password guardado.")
                return
            if not verify_password(self.password_var.get(), cfg.password_hash, cfg.password_salt):
                self._set_status("Password inválido.")
                return

        self._is_running = True
        self.start_button.state(["disabled"])
        self.progress.start(10)
        self._set_status("Limpieza iniciada en segundo plano...")
        self.logger.info("Limpieza iniciada. Ruta objetivo: %s", target)

        self._worker_thread = threading.Thread(
            target=self._worker_clean,
            args=(target,),
            daemon=True,
        )
        self._worker_thread.start()

    def _worker_clean(self, target: str) -> None:
        def status_cb(text: str) -> None:
            self._queue.put({"type": "status", "message": text})

        try:
            result = self.cleaner.clear_directory_contents(target, status_cb=status_cb)
            self._queue.put({"type": "result", "result": result})
        except Exception as exc:  # noqa: BLE001
            self._queue.put({"type": "error", "error": str(exc)})

    def _process_queue(self) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break

            event_type = item.get("type")
            if event_type == "status":
                message = str(item.get("message", "")).strip()
                if message:
                    self._set_status(message)
                    self.logger.info(message)
                continue

            if event_type == "result":
                result: CleanResult = item["result"]
                self._finish_cleanup(result=result, error="")
                continue

            if event_type == "error":
                self._finish_cleanup(result=None, error=str(item.get("error", "Error desconocido")))

        self.root.after(120, self._process_queue)

    def _finish_cleanup(self, result: CleanResult | None, error: str) -> None:
        self._is_running = False
        self.start_button.state(["!disabled"])
        self.progress.stop()

        if error:
            self._set_status(f"Error: {error}")
            self.logger.error("Fallo de limpieza: %s", error)
        elif result:
            summary = (
                f"Finalizado: {result.files_deleted} archivos, "
                f"{result.dirs_deleted} carpetas, {result.errors} errores."
            )
            self._set_status(summary)
            self.logger.info(summary)

        self.password_var.set("")
        self._sync_countdown_state(force_reset=True)

    def show_about_dialog(self) -> None:
        about_win = tk.Toplevel(self.root)
        about_win.title("About")
        about_win.transient(self.root)
        about_win.resizable(False, False)
        about_win.grab_set()

        year = dt.datetime.now().year
        text = f"{VERSION} x.x creado por Synyster Rick, {year} Derechos Reservados"

        frame = ttk.Frame(about_win, padding=18)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=text, wraplength=420, justify="center").pack(pady=(0, 12))
        ttk.Button(frame, text="Cerrar", command=about_win.destroy).pack()

    def _set_status(self, text: str) -> None:
        self._base_status = text
        self._refresh_status_text()

    def _refresh_status_text(self, extra: str | None = None) -> None:
        if extra:
            display = f"{self._base_status} | {extra}"
        else:
            display = self._base_status
        self.status_label.configure(text=display)

    def on_exit(self) -> None:
        if self._is_running:
            self._set_status("Espera a que termine la limpieza antes de salir.")
            return

        if self._countdown_job:
            self.root.after_cancel(self._countdown_job)
            self._countdown_job = None
        if self._configure_job:
            self.root.after_cancel(self._configure_job)
            self._configure_job = None
        if self._save_job:
            self.root.after_cancel(self._save_job)
            self._save_job = None

        self._persist_config()
        self.logger.info("Aplicación cerrada.")
        self.root.destroy()


def run() -> None:
    MainWindow().run()
