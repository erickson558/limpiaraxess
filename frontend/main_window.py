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
from backend.paths import get_runtime_dir
from backend.security import hash_password, verify_password
from backend.version import VERSION

APP_NAME = "LimpiarAxess"


class MainWindow:
    def __init__(self) -> None:
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get()
        self.logger = build_logger()
        self.cleaner = CleanerService()

        self.root = tk.Tk()
        self._configure_theme()
        self._set_app_icon()
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry(self.config.window_geometry)
        self.root.minsize(1080, 720)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        self._queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._queue_job: str | None = None
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
        self.status_var = tk.StringVar(value=self._base_status)
        self.path_summary_var = tk.StringVar(value="")
        self.auto_close_summary_var = tk.StringVar(value="")
        self.security_summary_var = tk.StringVar(value="")
        self.files_metric_var = tk.StringVar(value="0")
        self.dirs_metric_var = tk.StringVar(value="0")
        self.errors_metric_var = tk.StringVar(value="0")
        self.elapsed_metric_var = tk.StringVar(value="0.00 s")

        self._build_menu()
        self._build_ui()
        self._bind_shortcuts()
        self._bind_autosave()
        self._refresh_target_summary()
        self._refresh_auto_close_summary()
        self._refresh_security_summary()

        self.root.bind("<Configure>", self._on_window_configure)
        self._process_queue()
        self._sync_countdown_state(force_reset=True)
        self._set_status("Configuración cargada.")

        if self.auto_start_var.get():
            self.root.after(700, self.start_cleanup)

    def run(self) -> None:
        self.logger.info("Aplicación iniciada. Versión %s", VERSION)
        self.root.mainloop()

    def _configure_theme(self) -> None:
        self.colors = {
            "bg": "#09111f",
            "surface": "#122033",
            "surface_alt": "#17283d",
            "panel": "#1b2f47",
            "input": "#0d1727",
            "hero": "#0f2740",
            "hero_border": "#25486d",
            "accent": "#35c6ff",
            "accent_hover": "#52d2ff",
            "accent_soft": "#16344d",
            "warn": "#ffcc5c",
            "danger": "#ff7b7b",
            "success": "#59d39b",
            "text": "#f4f8ff",
            "muted": "#9fb3cc",
            "border": "#27405c",
        }

        self.root.configure(bg=self.colors["bg"])
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("Surface.TCheckbutton", background=self.colors["surface"], foreground=self.colors["text"])
        self.style.map(
            "Surface.TCheckbutton",
            background=[("active", self.colors["surface"])],
            foreground=[("disabled", self.colors["muted"])],
        )
        self.style.configure(
            "Surface.TEntry",
            fieldbackground=self.colors["input"],
            background=self.colors["input"],
            foreground=self.colors["text"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            insertcolor=self.colors["text"],
            padding=9,
        )
        self.style.configure(
            "Surface.TSpinbox",
            fieldbackground=self.colors["input"],
            background=self.colors["input"],
            foreground=self.colors["text"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            padding=8,
        )
        self.style.configure(
            "Primary.TButton",
            background=self.colors["accent"],
            foreground="#02141f",
            borderwidth=0,
            padding=(16, 10),
            font=("Segoe UI Semibold", 10),
        )
        self.style.map(
            "Primary.TButton",
            background=[
                ("pressed", self.colors["accent_hover"]),
                ("active", self.colors["accent_hover"]),
                ("disabled", self.colors["surface_alt"]),
            ],
            foreground=[("disabled", self.colors["muted"])],
        )
        self.style.configure(
            "Secondary.TButton",
            background=self.colors["surface_alt"],
            foreground=self.colors["text"],
            borderwidth=0,
            padding=(14, 10),
            font=("Segoe UI Semibold", 10),
        )
        self.style.map(
            "Secondary.TButton",
            background=[("pressed", self.colors["panel"]), ("active", self.colors["panel"])],
        )
        self.style.configure(
            "Ghost.TButton",
            background=self.colors["surface"],
            foreground=self.colors["text"],
            borderwidth=0,
            padding=(12, 10),
            font=("Segoe UI", 10),
        )
        self.style.map(
            "Ghost.TButton",
            background=[("pressed", self.colors["surface_alt"]), ("active", self.colors["surface_alt"])],
        )
        self.style.configure(
            "App.Horizontal.TProgressbar",
            troughcolor=self.colors["input"],
            bordercolor=self.colors["input"],
            background=self.colors["accent"],
            lightcolor=self.colors["accent"],
            darkcolor=self.colors["accent"],
        )
        self.style.configure(
            "App.Vertical.TScrollbar",
            background=self.colors["surface_alt"],
            troughcolor=self.colors["input"],
            bordercolor=self.colors["input"],
            arrowcolor=self.colors["text"],
        )

    def _set_app_icon(self) -> None:
        icon_path = get_runtime_dir() / "limpiar.ico"
        if not icon_path.exists():
            return
        try:
            self.root.iconbitmap(default=str(icon_path))
        except tk.TclError:
            return

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Iniciar limpieza", accelerator="F5", command=self.start_cleanup)
        file_menu.add_command(label="Seleccionar carpeta", accelerator="Ctrl+O", command=self.select_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", accelerator="Ctrl+Q", command=self.on_exit)
        menu_bar.add_cascade(label="Archivo", menu=file_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="About", accelerator="F1", command=self.show_about_dialog)
        menu_bar.add_cascade(label="Ayuda", menu=help_menu)

        self.root.config(menu=menu_bar)

    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg=self.colors["bg"])
        outer.pack(fill="both", expand=True, padx=24, pady=24)
        outer.grid_columnconfigure(0, weight=2)
        outer.grid_columnconfigure(1, weight=1)
        outer.grid_columnconfigure(2, weight=1)
        outer.grid_rowconfigure(2, weight=1)

        self._build_hero(outer).grid(row=0, column=0, columnspan=3, sticky="ew")
        self._build_path_card(outer).grid(row=1, column=0, sticky="nsew", pady=(18, 16), padx=(0, 16))
        self._build_automation_card(outer).grid(row=1, column=1, sticky="nsew", pady=(18, 16), padx=(0, 16))
        self._build_security_card(outer).grid(row=1, column=2, sticky="nsew", pady=(18, 16))
        self._build_activity_card(outer).grid(row=2, column=0, columnspan=3, sticky="nsew")

    def _build_card(self, parent: tk.Widget) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=self.colors["surface"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            bd=0,
        )

    def _build_stat_tile(self, parent: tk.Widget, title: str, value_var: tk.StringVar, accent: str) -> tk.Frame:
        tile = tk.Frame(parent, bg=self.colors["surface_alt"], highlightthickness=1, highlightbackground=self.colors["border"])
        tk.Frame(tile, bg=accent, height=4).pack(fill="x")
        tk.Label(
            tile,
            text=title.upper(),
            bg=self.colors["surface_alt"],
            fg=self.colors["muted"],
            font=("Segoe UI Semibold", 9),
        ).pack(anchor="w", padx=14, pady=(14, 4))
        tk.Label(
            tile,
            textvariable=value_var,
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            font=("Bahnschrift SemiBold", 20),
        ).pack(anchor="w", padx=14, pady=(0, 14))
        return tile

    def _build_hero(self, parent: tk.Widget) -> tk.Frame:
        hero = tk.Frame(
            parent,
            bg=self.colors["hero"],
            highlightthickness=1,
            highlightbackground=self.colors["hero_border"],
            bd=0,
        )
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_columnconfigure(1, weight=0)

        left = tk.Frame(hero, bg=self.colors["hero"])
        left.grid(row=0, column=0, sticky="nsew", padx=26, pady=26)

        tk.Label(
            left,
            text=f"Version {VERSION}",
            bg=self.colors["accent_soft"],
            fg=self.colors["accent"],
            font=("Segoe UI Semibold", 9),
            padx=10,
            pady=6,
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            left,
            text="Panel de limpieza seguro y con presencia visual",
            bg=self.colors["hero"],
            fg=self.colors["text"],
            font=("Bahnschrift SemiBold", 24),
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(14, 8))
        tk.Label(
            left,
            text=(
                "Selecciona una carpeta, protege la ejecución con contraseña si hace falta y "
                "ejecuta la limpieza con un panel más cercano a un dashboard que a una ventana clásica."
            ),
            bg=self.colors["hero"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=560,
        ).grid(row=2, column=0, sticky="w")
        tk.Label(
            left,
            text="Autocierre, validaciones de seguridad, trazabilidad en log y licencia Apache 2.0.",
            bg=self.colors["hero"],
            fg=self.colors["text"],
            font=("Segoe UI Semibold", 9),
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(16, 0))

        right = tk.Frame(hero, bg=self.colors["hero"])
        right.grid(row=0, column=1, sticky="ne", padx=26, pady=22)

        art = tk.Canvas(right, width=220, height=110, bg=self.colors["hero"], highlightthickness=0, bd=0)
        art.grid(row=0, column=0, sticky="e")
        art.create_oval(118, 8, 208, 98, fill="#1d4d72", outline="")
        art.create_oval(78, 30, 162, 114, fill="#10324f", outline="")
        art.create_oval(24, 12, 112, 100, fill="#1a6f8f", outline="")
        art.create_text(110, 55, text="AX", fill=self.colors["text"], font=("Bahnschrift SemiBold", 24))

        actions = tk.Frame(right, bg=self.colors["hero"])
        actions.grid(row=1, column=0, sticky="e", pady=(10, 0))

        self.start_button = ttk.Button(actions, text="Iniciar limpieza", style="Primary.TButton", command=self.start_cleanup)
        self.start_button.grid(row=0, column=0, padx=(0, 8))
        ttk.Button(actions, text="Examinar carpeta", style="Secondary.TButton", command=self.select_folder).grid(
            row=0,
            column=1,
            padx=(0, 8),
        )
        self.exit_button = ttk.Button(actions, text="Salir", style="Ghost.TButton", command=self.on_exit)
        self.exit_button.grid(row=0, column=2)
        return hero

    def _build_path_card(self, parent: tk.Widget) -> tk.Frame:
        card = self._build_card(parent)
        card.grid_columnconfigure(0, weight=1)

        tk.Label(
            card,
            text="Destino de limpieza",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Bahnschrift SemiBold", 16),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        tk.Label(
            card,
            text="La carpeta raíz se conserva. Solo se elimina su contenido interno.",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=20)
        tk.Label(
            card,
            text="Carpeta a limpiar",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI Semibold", 10),
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(18, 6))

        row = tk.Frame(card, bg=self.colors["surface"])
        row.grid(row=3, column=0, sticky="ew", padx=20)
        row.grid_columnconfigure(0, weight=1)

        self.path_entry = ttk.Entry(row, textvariable=self.target_var, style="Surface.TEntry")
        self.path_entry.grid(row=0, column=0, sticky="ew")
        self.browse_button = ttk.Button(row, text="Examinar", style="Secondary.TButton", command=self.select_folder)
        self.browse_button.grid(row=0, column=1, padx=(10, 0))

        tk.Label(
            card,
            textvariable=self.path_summary_var,
            bg=self.colors["surface"],
            fg=self.colors["accent"],
            font=("Segoe UI Semibold", 9),
            justify="left",
            wraplength=480,
        ).grid(row=4, column=0, sticky="w", padx=20, pady=(12, 0))

        note_box = tk.Frame(card, bg=self.colors["surface_alt"], highlightthickness=1, highlightbackground=self.colors["border"])
        note_box.grid(row=5, column=0, sticky="ew", padx=20, pady=(18, 20))
        note_box.grid_columnconfigure(0, weight=1)

        tk.Label(
            note_box,
            text="Buenas prácticas incluidas",
            bg=self.colors["surface_alt"],
            fg=self.colors["warn"],
            font=("Segoe UI Semibold", 10),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))
        tk.Label(
            note_box,
            text=(
                "Validación contra rutas críticas, manejo de archivos de solo lectura, "
                "guardado automático de configuración y log rotativo con timestamp."
            ),
            bg=self.colors["surface_alt"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            justify="left",
            wraplength=500,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))
        return card

    def _build_automation_card(self, parent: tk.Widget) -> tk.Frame:
        card = self._build_card(parent)
        card.grid_columnconfigure(0, weight=1)

        tk.Label(
            card,
            text="Automatización",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Bahnschrift SemiBold", 16),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        tk.Label(
            card,
            text="Configura el arranque y el cierre sin depender de cuadros modales.",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=250,
        ).grid(row=1, column=0, sticky="w", padx=20)

        self.auto_start_check = ttk.Checkbutton(
            card,
            text="Auto iniciar al abrir",
            variable=self.auto_start_var,
            style="Surface.TCheckbutton",
            command=self._schedule_save,
        )
        self.auto_start_check.grid(row=2, column=0, sticky="w", padx=20, pady=(18, 8))

        self.auto_close_check = ttk.Checkbutton(
            card,
            text="Habilitar autocierre",
            variable=self.auto_close_enabled_var,
            style="Surface.TCheckbutton",
            command=self._on_auto_close_toggle,
        )
        self.auto_close_check.grid(row=3, column=0, sticky="w", padx=20, pady=8)

        tk.Label(
            card,
            text="Segundos para autocierre",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI Semibold", 10),
        ).grid(row=4, column=0, sticky="w", padx=20, pady=(16, 6))
        self.auto_close_spin = ttk.Spinbox(
            card,
            from_=5,
            to=86_400,
            textvariable=self.auto_close_seconds_var,
            width=10,
            style="Surface.TSpinbox",
            command=self._on_auto_close_seconds_changed,
        )
        self.auto_close_spin.grid(row=5, column=0, sticky="w", padx=20)

        tk.Label(
            card,
            textvariable=self.auto_close_summary_var,
            bg=self.colors["surface"],
            fg=self.colors["accent"],
            font=("Segoe UI Semibold", 9),
            justify="left",
            wraplength=250,
        ).grid(row=6, column=0, sticky="w", padx=20, pady=(12, 20))
        return card

    def _build_security_card(self, parent: tk.Widget) -> tk.Frame:
        card = self._build_card(parent)
        card.grid_columnconfigure(0, weight=1)

        tk.Label(
            card,
            text="Seguridad y acceso",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Bahnschrift SemiBold", 16),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        tk.Label(
            card,
            text="Protege la limpieza con una clave hash y usa atajos estilo Windows.",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=250,
        ).grid(row=1, column=0, sticky="w", padx=20)

        self.password_required_check = ttk.Checkbutton(
            card,
            text="Requerir password para limpiar",
            variable=self.password_required_var,
            style="Surface.TCheckbutton",
            command=self._schedule_save,
        )
        self.password_required_check.grid(row=2, column=0, sticky="w", padx=20, pady=(18, 8))

        entry_row = tk.Frame(card, bg=self.colors["surface"])
        entry_row.grid(row=3, column=0, sticky="ew", padx=20)
        entry_row.grid_columnconfigure(0, weight=1)

        self.password_entry = ttk.Entry(entry_row, textvariable=self.password_var, show="*", style="Surface.TEntry")
        self.password_entry.grid(row=0, column=0, sticky="ew")
        self.show_password_btn = ttk.Button(
            entry_row,
            text="Mostrar",
            style="Ghost.TButton",
            width=10,
            command=self.toggle_password_visibility,
        )
        self.show_password_btn.grid(row=0, column=1, padx=(8, 0))

        self.save_password_btn = ttk.Button(
            card,
            text="Guardar password",
            style="Secondary.TButton",
            command=self.save_password_hash,
        )
        self.save_password_btn.grid(row=4, column=0, sticky="w", padx=20, pady=(12, 10))

        tk.Label(
            card,
            textvariable=self.security_summary_var,
            bg=self.colors["surface"],
            fg=self.colors["accent"],
            font=("Segoe UI Semibold", 9),
            justify="left",
            wraplength=250,
        ).grid(row=5, column=0, sticky="w", padx=20)
        tk.Label(
            card,
            text="Atajos: Ctrl+O seleccionar, F5 limpiar, Ctrl+G guardar clave, Ctrl+Q salir, F1 ayuda.",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            justify="left",
            wraplength=250,
        ).grid(row=6, column=0, sticky="w", padx=20, pady=(16, 8))
        ttk.Button(card, text="About", style="Ghost.TButton", command=self.show_about_dialog).grid(
            row=7,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 20),
        )
        return card

    def _build_activity_card(self, parent: tk.Widget) -> tk.Frame:
        card = self._build_card(parent)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(4, weight=1)

        top = tk.Frame(card, bg=self.colors["surface"])
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 6))
        top.grid_columnconfigure(0, weight=1)

        tk.Label(
            top,
            text="Centro de actividad",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Bahnschrift SemiBold", 16),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            top,
            text=f"{APP_NAME} v{VERSION}",
            bg=self.colors["accent_soft"],
            fg=self.colors["accent"],
            font=("Segoe UI Semibold", 9),
            padx=10,
            pady=6,
        ).grid(row=0, column=1, sticky="e")

        tk.Label(
            card,
            textvariable=self.status_var,
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI Semibold", 10),
            justify="left",
            wraplength=960,
        ).grid(row=1, column=0, sticky="ew", padx=20)
        self.progress = ttk.Progressbar(card, mode="indeterminate", style="App.Horizontal.TProgressbar")
        self.progress.grid(row=2, column=0, sticky="ew", padx=20, pady=(14, 14))

        metrics = tk.Frame(card, bg=self.colors["surface"])
        metrics.grid(row=3, column=0, sticky="ew", padx=20)
        for column in range(4):
            metrics.grid_columnconfigure(column, weight=1)

        self._build_stat_tile(metrics, "Archivos", self.files_metric_var, self.colors["accent"]).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 12),
        )
        self._build_stat_tile(metrics, "Carpetas", self.dirs_metric_var, self.colors["success"]).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 12),
        )
        self._build_stat_tile(metrics, "Errores", self.errors_metric_var, self.colors["danger"]).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(0, 12),
        )
        self._build_stat_tile(metrics, "Duración", self.elapsed_metric_var, self.colors["warn"]).grid(
            row=0,
            column=3,
            sticky="ew",
        )

        log_frame = tk.Frame(card, bg=self.colors["input"], highlightthickness=1, highlightbackground=self.colors["border"])
        log_frame.grid(row=4, column=0, sticky="nsew", padx=20, pady=(18, 20))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.activity_text = tk.Text(
            log_frame,
            bg=self.colors["input"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            bd=0,
            wrap="word",
            font=("Consolas", 10),
            height=11,
            padx=14,
            pady=14,
            state="disabled",
        )
        self.activity_text.grid(row=0, column=0, sticky="nsew")
        self.activity_text.tag_configure("time", foreground=self.colors["muted"])
        self.activity_text.tag_configure("message", foreground=self.colors["text"])

        scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.activity_text.yview,
            style="App.Vertical.TScrollbar",
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.activity_text.configure(yscrollcommand=scrollbar.set)
        return card

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-o>", lambda _: self.select_folder())
        self.root.bind("<Control-q>", lambda _: self.on_exit())
        self.root.bind("<F5>", lambda _: self.start_cleanup())
        self.root.bind("<F1>", lambda _: self.show_about_dialog())
        self.root.bind("<Control-g>", lambda _: self.save_password_hash())
        self.root.bind("<Alt-s>", lambda _: self.start_cleanup())
        self.root.bind("<Alt-x>", lambda _: self.on_exit())

    def _bind_autosave(self) -> None:
        self.target_var.trace_add("write", lambda *_: (self._refresh_target_summary(), self._schedule_save()))
        self.auto_start_var.trace_add("write", lambda *_: self._schedule_save())
        self.auto_close_enabled_var.trace_add("write", lambda *_: self._on_auto_close_toggle())
        self.auto_close_seconds_var.trace_add("write", lambda *_: self._on_auto_close_seconds_changed())
        self.password_required_var.trace_add("write", lambda *_: (self._refresh_security_summary(), self._schedule_save()))

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
        self._refresh_security_summary()

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
            self._refresh_auto_close_summary()
            return

        seconds = self._safe_seconds()
        if force_reset or self._countdown_remaining <= 0:
            self._countdown_remaining = seconds

        self._tick_countdown()

    def _tick_countdown(self) -> None:
        if not self.auto_close_enabled_var.get():
            self._refresh_status_text()
            self._refresh_auto_close_summary()
            return

        if self._is_running:
            self._refresh_status_text(extra="Autocierre pausado durante limpieza.")
            self._refresh_auto_close_summary("Autocierre pausado mientras hay trabajo en curso.")
            self._countdown_job = self.root.after(1000, self._tick_countdown)
            return

        if self._countdown_remaining <= 0:
            self._set_status("Autocierre ejecutado.")
            self.logger.info("Autocierre ejecutado.")
            self.root.after(200, self.root.destroy)
            return

        self._refresh_status_text(extra=f"Autocierre en {self._countdown_remaining}s")
        self._refresh_auto_close_summary(
            f"La aplicación se cerrará sola en {self._countdown_remaining}s si permanece inactiva."
        )
        self._countdown_remaining -= 1
        self._countdown_job = self.root.after(1000, self._tick_countdown)

    def _refresh_target_summary(self) -> None:
        target = self.target_var.get().strip()
        if not target:
            self.path_summary_var.set("No hay carpeta seleccionada todavía.")
            return

        path = Path(target)
        name = path.name or str(path)
        self.path_summary_var.set(f"Destino listo: {name} | Ruta completa: {path}")

    def _refresh_auto_close_summary(self, text: str | None = None) -> None:
        if text:
            self.auto_close_summary_var.set(text)
            return

        if not self.auto_close_enabled_var.get():
            self.auto_close_summary_var.set("Autocierre desactivado. La ventana seguirá abierta hasta salir manualmente.")
            return

        seconds = self._safe_seconds()
        self.auto_close_summary_var.set(f"Autocierre activo. Tiempo configurado: {seconds}s.")

    def _refresh_security_summary(self) -> None:
        cfg = self.config_manager.get()
        if not self.password_required_var.get():
            self.security_summary_var.set("Protección opcional desactivada. Puedes iniciar la limpieza directamente.")
            return

        if cfg.password_hash and cfg.password_salt:
            self.security_summary_var.set("Protección activa. Escribe la clave actual y luego ejecuta la limpieza.")
            return

        self.security_summary_var.set("Protección activa, pero todavía no hay password guardado.")

    def _set_running_metrics(self) -> None:
        self.files_metric_var.set("...")
        self.dirs_metric_var.set("...")
        self.errors_metric_var.set("...")
        self.elapsed_metric_var.set("En curso")

    def _refresh_result_metrics(self, result: CleanResult | None = None) -> None:
        if result is None:
            self.files_metric_var.set("0")
            self.dirs_metric_var.set("0")
            self.errors_metric_var.set("0")
            self.elapsed_metric_var.set("0.00 s")
            return

        self.files_metric_var.set(str(result.files_deleted))
        self.dirs_metric_var.set(str(result.dirs_deleted))
        self.errors_metric_var.set(str(result.errors))
        self.elapsed_metric_var.set(f"{result.elapsed_seconds:.2f} s")

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
        self._refresh_security_summary()
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
        self._set_running_metrics()
        self._set_status("Limpieza iniciada en segundo plano...")
        self.logger.info("Limpieza iniciada. Ruta objetivo: %s", target)
        self._refresh_auto_close_summary("Autocierre pausado mientras se completa la limpieza.")

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

        self._queue_job = self.root.after(120, self._process_queue)

    def _finish_cleanup(self, result: CleanResult | None, error: str) -> None:
        self._is_running = False
        self.start_button.state(["!disabled"])
        self.progress.stop()

        if error:
            self._refresh_result_metrics()
            self._set_status(f"Error: {error}")
            self.logger.error("Fallo de limpieza: %s", error)
        elif result:
            self._refresh_result_metrics(result)
            summary = (
                f"Finalizado: {result.files_deleted} archivos, "
                f"{result.dirs_deleted} carpetas, {result.errors} errores."
            )
            self._set_status(summary)
            self.logger.info(summary)

        self.password_var.set("")
        self._sync_countdown_state(force_reset=True)

    def show_about_dialog(self) -> None:
        about_win = tk.Toplevel(self.root, bg=self.colors["bg"])
        about_win.title("About")
        about_win.transient(self.root)
        about_win.resizable(False, False)
        about_win.grab_set()

        frame = tk.Frame(
            about_win,
            bg=self.colors["surface"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            bd=0,
        )
        frame.pack(fill="both", expand=True, padx=18, pady=18)

        year = dt.datetime.now().year
        text = (
            f"{APP_NAME} v{VERSION}\n\n"
            "Herramienta de escritorio para vaciar el contenido de una carpeta con validaciones "
            "de seguridad, log local y automatización opcional.\n\n"
            f"Autor: Synyster Rick\nLicencia: Apache License 2.0\nCopyright {year}"
        )

        tk.Label(
            frame,
            text=text,
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 10),
            wraplength=420,
            justify="center",
        ).pack(padx=22, pady=(22, 16))
        ttk.Button(frame, text="Cerrar", style="Primary.TButton", command=about_win.destroy).pack(pady=(0, 22))

    def _set_status(self, text: str) -> None:
        self._base_status = text
        self._refresh_status_text()
        self._append_activity(text)

    def _refresh_status_text(self, extra: str | None = None) -> None:
        if extra:
            display = f"{self._base_status} | {extra}"
        else:
            display = self._base_status
        self.status_var.set(display)

    def _append_activity(self, text: str) -> None:
        if not hasattr(self, "activity_text"):
            return

        timestamp = dt.datetime.now().strftime("%H:%M:%S")
        self.activity_text.configure(state="normal")
        self.activity_text.insert("end", f"[{timestamp}] ", ("time",))
        self.activity_text.insert("end", f"{text}\n", ("message",))

        line_count = int(self.activity_text.index("end-1c").split(".")[0])
        if line_count > 240:
            self.activity_text.delete("1.0", "40.0")

        self.activity_text.see("end")
        self.activity_text.configure(state="disabled")

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
        if self._queue_job:
            self.root.after_cancel(self._queue_job)
            self._queue_job = None

        self._persist_config()
        self.logger.info("Aplicación cerrada.")
        self.root.destroy()


def run() -> None:
    MainWindow().run()
