from __future__ import annotations

import datetime as dt
import queue
import threading
import tkinter as tk
import webbrowser  # Para abrir el enlace de donaciones en el navegador predeterminado
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any

from backend.cleaner_service import CleanResult, CleanerService
from backend.config_manager import ConfigManager
from backend.i18n import get_language, set_language, t  # Sistema de traducciones ES/EN
from backend.logger_service import build_logger
from backend.paths import get_runtime_dir
from backend.security import hash_password, verify_password
from backend.version import VERSION

APP_NAME = "LimpiarAxess"

# URL del botón de donaciones — PayPal
DONATE_URL = "https://www.paypal.com/donate/?hosted_button_id=ZABFRXC2P3JQN"


class MainWindow:
    def __init__(self) -> None:
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get()
        self.logger = build_logger()
        self.cleaner = CleanerService()

        # Activa el idioma guardado antes de construir la UI
        set_language(self.config.language)

        self.root = tk.Tk()
        self._configure_theme()
        self._set_app_icon()
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry(self.config.window_geometry)
        self.root.minsize(980, 680)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        self._queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._queue_job: str | None = None
        self._worker_thread: threading.Thread | None = None
        self._is_running = False
        self._show_password = False        # True cuando el campo de password es visible
        self.restart_requested = False     # True si se pidió reinicio por cambio de idioma
        self._base_status = t("app_ready")
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
        self._fit_window_to_content()

        self.root.bind("<Configure>", self._on_window_configure)
        self._process_queue()
        self._sync_countdown_state(force_reset=True)
        self._set_status(t("config_loaded"))

        if self.auto_start_var.get():
            self.root.after(700, self.start_cleanup)

    def run(self) -> None:
        self.logger.info(t("app_started"), VERSION)
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
        # Botón de donación: fondo ámbar para destacarlo visualmente
        self.style.configure(
            "Donate.TButton",
            background="#f5a623",
            foreground="#1a0f00",
            borderwidth=0,
            padding=(14, 10),
            font=("Segoe UI Semibold", 10),
        )
        self.style.map(
            "Donate.TButton",
            background=[("pressed", "#e09515"), ("active", "#e09515")],
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

    def _fit_window_to_content(self) -> None:
        self.root.update_idletasks()
        available_width = max(self.root.minsize()[0], self.root.winfo_screenwidth() - 40)
        available_height = max(self.root.minsize()[1], self.root.winfo_screenheight() - 80)
        current_width = self.root.winfo_width()
        current_height = self.root.winfo_height()
        target_width = min(max(current_width, self.root.winfo_reqwidth()), available_width)
        target_height = min(max(current_height, self.root.winfo_reqheight()), available_height)

        if target_width != current_width or target_height != current_height:
            self.root.geometry(f"{target_width}x{target_height}")

    def _build_menu(self) -> None:
        """Construye la barra de menú con Archivo, Idioma y Ayuda."""
        menu_bar = tk.Menu(self.root)

        # Menú Archivo
        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label=t("menu_start_cleanup"), accelerator="F5", command=self.start_cleanup)
        file_menu.add_command(label=t("menu_select_folder"), accelerator="Ctrl+O", command=self.select_folder)
        file_menu.add_separator()
        file_menu.add_command(label=t("menu_exit"), accelerator="Ctrl+Q", command=self.on_exit)
        menu_bar.add_cascade(label=t("menu_file"), menu=file_menu)

        # Menú Idioma — permite cambiar entre Español e Inglés
        lang_menu = tk.Menu(menu_bar, tearoff=False)
        lang_menu.add_command(
            label=("\u2713 " if get_language() == "es" else "  ") + "Español",
            command=lambda: self._change_language("es"),
        )
        lang_menu.add_command(
            label=("\u2713 " if get_language() == "en" else "  ") + "English",
            command=lambda: self._change_language("en"),
        )
        menu_bar.add_cascade(label=t("menu_language"), menu=lang_menu)

        # Menú Ayuda
        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label=t("menu_about"), accelerator="F1", command=self.show_about_dialog)
        help_menu.add_separator()
        # Acceso rápido al enlace de donaciones desde el menú
        help_menu.add_command(label=t("btn_donate"), command=self.open_donate_url)
        menu_bar.add_cascade(label=t("menu_help"), menu=help_menu)

        self.root.config(menu=menu_bar)

    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg=self.colors["bg"])
        outer.pack(fill="both", expand=True, padx=12, pady=18)
        outer.grid_columnconfigure(0, weight=0, minsize=380)
        outer.grid_columnconfigure(1, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        self._build_hero(outer).grid(row=0, column=0, columnspan=2, sticky="ew")
        self._build_settings_card(outer).grid(row=1, column=0, sticky="nsew", pady=(18, 0), padx=(0, 8))
        self._build_activity_card(outer).grid(row=1, column=1, sticky="nsew", pady=(18, 0))

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
        left.grid(row=0, column=0, sticky="nsew", padx=20, pady=16)

        tk.Label(
            left,
            text=f"Version {VERSION}",
            bg=self.colors["accent_soft"],
            fg=self.colors["accent"],
            font=("Segoe UI Semibold", 9),
            padx=10,
            pady=5,
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            left,
            text=t("hero_subtitle"),
            bg=self.colors["hero"],
            fg=self.colors["text"],
            font=("Bahnschrift SemiBold", 20),
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(10, 6))
        tk.Label(
            left,
            text=t("hero_description"),
            bg=self.colors["hero"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            justify="left",
            wraplength=580,
        ).grid(row=2, column=0, sticky="w")

        right = tk.Frame(hero, bg=self.colors["hero"])
        right.grid(row=0, column=1, sticky="ne", padx=20, pady=16)

        art = tk.Canvas(right, width=150, height=78, bg=self.colors["hero"], highlightthickness=0, bd=0)
        art.grid(row=0, column=0, sticky="e")
        art.create_oval(84, 4, 146, 66, fill="#1d4d72", outline="")
        art.create_oval(54, 20, 114, 80, fill="#10324f", outline="")
        art.create_oval(14, 8, 74, 68, fill="#1a6f8f", outline="")
        art.create_text(78, 40, text="AX", fill=self.colors["text"], font=("Bahnschrift SemiBold", 18))

        actions = tk.Frame(right, bg=self.colors["hero"])
        actions.grid(row=1, column=0, sticky="e", pady=(8, 0))

        self.start_button = ttk.Button(actions, text=t("btn_start_cleanup"), style="Primary.TButton", command=self.start_cleanup)
        self.start_button.grid(row=0, column=0, padx=(0, 8))
        ttk.Button(actions, text=t("btn_browse_folder"), style="Secondary.TButton", command=self.select_folder).grid(
            row=0,
            column=1,
            padx=(0, 8),
        )
        self.exit_button = ttk.Button(actions, text=t("btn_exit"), style="Ghost.TButton", command=self.on_exit)
        self.exit_button.grid(row=0, column=2, padx=(0, 8))
        # Botón de donación en el hero — abre PayPal en el navegador
        ttk.Button(
            actions,
            text=t("btn_donate"),
            style="Donate.TButton",
            command=self.open_donate_url,
        ).grid(row=0, column=3)
        return hero

    def _build_settings_card(self, parent: tk.Widget) -> tk.Frame:
        card = self._build_card(parent)
        card.grid_columnconfigure(0, weight=1)

        tk.Label(
            card,
            text=t("section_controls"),
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Bahnschrift SemiBold", 16),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(16, 4))

        path_box = tk.Frame(card, bg=self.colors["surface_alt"], highlightthickness=1, highlightbackground=self.colors["border"])
        path_box.grid(row=1, column=0, sticky="ew", padx=14, pady=(10, 12))
        path_box.grid_columnconfigure(0, weight=1)

        tk.Label(
            path_box,
            text=t("label_target"),
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            font=("Segoe UI Semibold", 10),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        row = tk.Frame(path_box, bg=self.colors["surface_alt"])
        row.grid(row=1, column=0, sticky="ew", padx=14)
        row.grid_columnconfigure(0, weight=1)

        self.path_entry = ttk.Entry(row, textvariable=self.target_var, style="Surface.TEntry")
        self.path_entry.grid(row=0, column=0, sticky="ew")
        self.browse_button = ttk.Button(row, text=t("btn_browse"), style="Secondary.TButton", command=self.select_folder)
        self.browse_button.grid(row=0, column=1, padx=(8, 0))

        tk.Label(
            path_box,
            textvariable=self.path_summary_var,
            bg=self.colors["surface_alt"],
            fg=self.colors["accent"],
            font=("Segoe UI Semibold", 9),
            justify="left",
            wraplength=320,
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(10, 12))

        controls = tk.Frame(card, bg=self.colors["surface"])
        controls.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 12))
        controls.grid_columnconfigure(0, weight=1)
        controls.grid_columnconfigure(1, weight=1)

        auto_box = tk.Frame(controls, bg=self.colors["surface_alt"], highlightthickness=1, highlightbackground=self.colors["border"])
        auto_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        auto_box.grid_columnconfigure(0, weight=1)

        security_box = tk.Frame(controls, bg=self.colors["surface_alt"], highlightthickness=1, highlightbackground=self.colors["border"])
        security_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        security_box.grid_columnconfigure(0, weight=1)

        self._populate_automation_box(auto_box)
        self._populate_security_box(security_box)

        tk.Label(
            card,
            text=t("footer_note"),
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            justify="left",
            wraplength=320,
        ).grid(row=3, column=0, sticky="w", padx=14, pady=(0, 16))
        return card

    def _populate_automation_box(self, card: tk.Widget) -> None:
        tk.Label(
            card,
            text=t("section_automation"),
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            font=("Segoe UI Semibold", 10),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        self.auto_start_check = ttk.Checkbutton(
            card,
            text=t("check_auto_start"),
            variable=self.auto_start_var,
            style="Surface.TCheckbutton",
            command=self._schedule_save,
        )
        self.auto_start_check.grid(row=1, column=0, sticky="w", padx=14, pady=(10, 6))

        self.auto_close_check = ttk.Checkbutton(
            card,
            text=t("check_auto_close"),
            variable=self.auto_close_enabled_var,
            style="Surface.TCheckbutton",
            command=self._on_auto_close_toggle,
        )
        self.auto_close_check.grid(row=2, column=0, sticky="w", padx=14, pady=6)

        tk.Label(
            card,
            text=t("label_auto_close_seconds"),
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            font=("Segoe UI Semibold", 9),
        ).grid(row=3, column=0, sticky="w", padx=14, pady=(8, 4))
        self.auto_close_spin = ttk.Spinbox(
            card,
            from_=5,
            to=86_400,
            textvariable=self.auto_close_seconds_var,
            width=10,
            style="Surface.TSpinbox",
            command=self._on_auto_close_seconds_changed,
        )
        self.auto_close_spin.grid(row=4, column=0, sticky="w", padx=14)

        tk.Label(
            card,
            textvariable=self.auto_close_summary_var,
            bg=self.colors["surface_alt"],
            fg=self.colors["accent"],
            font=("Segoe UI Semibold", 9),
            justify="left",
            wraplength=150,
        ).grid(row=5, column=0, sticky="w", padx=14, pady=(8, 12))

    def _populate_security_box(self, card: tk.Widget) -> None:
        tk.Label(
            card,
            text=t("section_security"),
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            font=("Segoe UI Semibold", 10),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        self.password_required_check = ttk.Checkbutton(
            card,
            text=t("check_require_password"),
            variable=self.password_required_var,
            style="Surface.TCheckbutton",
            command=self._schedule_save,
        )
        self.password_required_check.grid(row=1, column=0, sticky="w", padx=14, pady=(10, 6))

        entry_row = tk.Frame(card, bg=self.colors["surface_alt"])
        entry_row.grid(row=2, column=0, sticky="ew", padx=14)
        entry_row.grid_columnconfigure(0, weight=1)

        self.password_entry = ttk.Entry(entry_row, textvariable=self.password_var, show="*", style="Surface.TEntry")
        self.password_entry.grid(row=0, column=0, sticky="ew")
        self.show_password_btn = ttk.Button(
            entry_row,
            text=t("btn_show_password"),
            style="Ghost.TButton",
            width=10,
            command=self.toggle_password_visibility,
        )
        self.show_password_btn.grid(row=0, column=1, padx=(8, 0))

        button_row = tk.Frame(card, bg=self.colors["surface_alt"])
        button_row.grid(row=3, column=0, sticky="w", padx=14, pady=(8, 6))

        self.save_password_btn = ttk.Button(
            button_row,
            text=t("btn_save_password"),
            style="Secondary.TButton",
            command=self.save_password_hash,
        )
        self.save_password_btn.grid(row=0, column=0, sticky="w")
        ttk.Button(button_row, text=t("btn_about"), style="Ghost.TButton", command=self.show_about_dialog).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(8, 0),
        )

        tk.Label(
            card,
            textvariable=self.security_summary_var,
            bg=self.colors["surface_alt"],
            fg=self.colors["accent"],
            font=("Segoe UI Semibold", 9),
            justify="left",
            wraplength=150,
        ).grid(row=4, column=0, sticky="w", padx=14, pady=(0, 12))

    def _build_activity_card(self, parent: tk.Widget) -> tk.Frame:
        card = self._build_card(parent)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(4, weight=1)

        top = tk.Frame(card, bg=self.colors["surface"])
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(18, 6))
        top.grid_columnconfigure(0, weight=1)

        tk.Label(
            top,
            text=t("section_activity"),
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
            wraplength=620,
        ).grid(row=1, column=0, sticky="ew", padx=10)
        self.progress = ttk.Progressbar(card, mode="indeterminate", style="App.Horizontal.TProgressbar")
        self.progress.grid(row=2, column=0, sticky="ew", padx=10, pady=(14, 14))

        metrics = tk.Frame(card, bg=self.colors["surface"])
        metrics.grid(row=3, column=0, sticky="ew", padx=10)
        for column in range(4):
            metrics.grid_columnconfigure(column, weight=1)

        self._build_stat_tile(metrics, t("stat_files"), self.files_metric_var, self.colors["accent"]).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 12),
        )
        self._build_stat_tile(metrics, t("stat_dirs"), self.dirs_metric_var, self.colors["success"]).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 12),
        )
        self._build_stat_tile(metrics, t("stat_errors"), self.errors_metric_var, self.colors["danger"]).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(0, 12),
        )
        self._build_stat_tile(metrics, t("stat_duration"), self.elapsed_metric_var, self.colors["warn"]).grid(
            row=0,
            column=3,
            sticky="ew",
        )

        log_frame = tk.Frame(card, bg=self.colors["input"], highlightthickness=1, highlightbackground=self.colors["border"])
        log_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=(18, 16))
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
        """Escribe el estado actual de la UI en config.json de forma atómica."""
        self._save_job = None
        try:
            # winfo_geometry puede fallar si la ventana está siendo destruida
            geometry = self.root.winfo_geometry()
        except tk.TclError:
            geometry = self.config.window_geometry  # Usa el último valor conocido
        self.config = self.config_manager.update(
            target_path=self.target_var.get().strip(),
            auto_start=self.auto_start_var.get(),
            auto_close_enabled=self.auto_close_enabled_var.get(),
            auto_close_seconds=self._safe_seconds(),
            window_geometry=geometry,
            password_required=self.password_required_var.get(),
            language=get_language(),  # Persiste el idioma activo
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
            self._refresh_status_text(extra=t("autoclose_paused_extra"))
            self._refresh_auto_close_summary(t("autoclose_paused_running"))
            self._countdown_job = self.root.after(1000, self._tick_countdown)
            return

        if self._countdown_remaining <= 0:
            self._set_status(t("autoclose_executed"))
            self.logger.info(t("autoclose_executed"))
            self.root.after(200, self.root.destroy)
            return

        self._refresh_status_text(extra=t("autoclose_countdown_short", sec=self._countdown_remaining))
        self._refresh_auto_close_summary(
            t("autoclose_countdown", sec=self._countdown_remaining)
        )
        self._countdown_remaining -= 1
        self._countdown_job = self.root.after(1000, self._tick_countdown)

    def _refresh_target_summary(self) -> None:
        target = self.target_var.get().strip()
        if not target:
            self.path_summary_var.set(t("no_folder_selected"))
            return

        path = Path(target)
        name = path.name or str(path)
        self.path_summary_var.set(t("target_ready", name=name, path=path))

    def _refresh_auto_close_summary(self, text: str | None = None) -> None:
        if text:
            self.auto_close_summary_var.set(text)
            return

        if not self.auto_close_enabled_var.get():
            self.auto_close_summary_var.set(t("autoclose_disabled"))
            return

        seconds = self._safe_seconds()
        self.auto_close_summary_var.set(t("autoclose_active", sec=seconds))

    def _refresh_security_summary(self) -> None:
        cfg = self.config_manager.get()
        if not self.password_required_var.get():
            self.security_summary_var.set(t("security_inactive"))
            return

        if cfg.password_hash and cfg.password_salt:
            self.security_summary_var.set(t("security_active_with_hash"))
            return

        self.security_summary_var.set(t("security_active_no_hash"))

    def _set_running_metrics(self) -> None:
        self.files_metric_var.set("...")
        self.dirs_metric_var.set("...")
        self.errors_metric_var.set("...")
        self.elapsed_metric_var.set(t("in_progress"))

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
        selected = filedialog.askdirectory(title=t("label_target"))
        if not selected:
            return
        self.target_var.set(str(Path(selected)))
        self._set_status(t("folder_selected", path=selected))

    def toggle_password_visibility(self) -> None:
        self._show_password = not self._show_password
        self.password_entry.configure(show="" if self._show_password else "*")
        self.show_password_btn.configure(text=t("btn_hide_password") if self._show_password else t("btn_show_password"))

    def save_password_hash(self) -> None:
        plain = self.password_var.get()
        if len(plain) < 4:
            self._set_status(t("password_too_short"))
            return

        hashed, salt = hash_password(plain)
        self.config = self.config_manager.update(password_hash=hashed, password_salt=salt)
        self.password_var.set("")
        self._refresh_security_summary()
        self._set_status(t("password_saved"))
        self.logger.info(t("password_updated"))

    def start_cleanup(self) -> None:
        if self._is_running:
            self._set_status(t("already_running"))
            return

        target = self.target_var.get().strip()
        is_valid, reason = self.cleaner.validate_target(target)
        if not is_valid:
            self._set_status(reason)
            return

        cfg = self.config_manager.get()
        if self.password_required_var.get():
            if not cfg.password_hash or not cfg.password_salt:
                self._set_status(t("password_required_no_hash"))
                return
            if not verify_password(self.password_var.get(), cfg.password_hash, cfg.password_salt):
                self._set_status(t("password_invalid"))
                return

        self._is_running = True
        self.start_button.state(["disabled"])
        self.progress.start(10)
        self._set_running_metrics()
        self._set_status(t("cleanup_started"))
        self.logger.info(t("cleanup_started_log"), target)
        self._refresh_auto_close_summary(t("autoclose_paused_cleanup"))

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
                continue  # Consistencia: siempre continue al final de cada rama

        self._queue_job = self.root.after(120, self._process_queue)

    def _finish_cleanup(self, result: CleanResult | None, error: str) -> None:
        self._is_running = False
        self.start_button.state(["!disabled"])
        self.progress.stop()

        if error:
            self._refresh_result_metrics()
            self._set_status(t("error_prefix", msg=error))
            self.logger.error(t("cleanup_failed_log"), error)
        elif result:
            self._refresh_result_metrics(result)
            summary = t(
                "cleanup_result",
                files=result.files_deleted,
                dirs=result.dirs_deleted,
                errors=result.errors,
            )
            self._set_status(summary)
            self.logger.info(summary)

        self.password_var.set("")
        self._sync_countdown_state(force_reset=True)

    def show_about_dialog(self) -> None:
        """Muestra el diálogo de información de la app con botón de donación PayPal."""
        # Guarda ante la posibilidad de que la ventana esté siendo destruida
        try:
            if not self.root.winfo_exists():
                return
        except tk.TclError:
            return

        about_win = tk.Toplevel(self.root, bg=self.colors["bg"])
        about_win.title(t("about_title"))
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

        # Nombre y versión de la aplicación
        tk.Label(
            frame,
            text=f"{APP_NAME} v{VERSION}",
            bg=self.colors["surface"],
            fg=self.colors["accent"],
            font=("Bahnschrift SemiBold", 16),
            justify="center",
        ).pack(padx=22, pady=(22, 6))

        # Descripción traducible
        tk.Label(
            frame,
            text=t("about_description"),
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 10),
            wraplength=420,
            justify="center",
        ).pack(padx=22, pady=(0, 8))

        # Autor, licencia y copyright
        tk.Label(
            frame,
            text=f"{t('about_author')} · {t('about_license')} · {t('about_copyright', year=year)}",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            justify="center",
        ).pack(padx=22, pady=(0, 16))

        # Separador visual antes de la sección de donación
        tk.Frame(frame, bg=self.colors["border"], height=1).pack(fill="x", padx=22, pady=(0, 16))

        # Invitación a donar
        tk.Label(
            frame,
            text=t("about_donate_label"),
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI Semibold", 10),
            justify="center",
        ).pack(padx=22, pady=(0, 10))

        # Botón de donación — abre la URL de PayPal en el navegador predeterminado
        ttk.Button(
            frame,
            text=t("btn_donate"),
            style="Donate.TButton",
            command=self.open_donate_url,
        ).pack(pady=(0, 12))

        # Botón para cerrar el diálogo
        ttk.Button(
            frame, text=t("btn_close"), style="Primary.TButton", command=about_win.destroy
        ).pack(pady=(0, 22))

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
        """Agrega una línea con timestamp a la bitácora y limita a 200 líneas."""
        if not hasattr(self, "activity_text"):
            return

        timestamp = dt.datetime.now().strftime("%H:%M:%S")
        try:
            self.activity_text.configure(state="normal")
            self.activity_text.insert("end", f"[{timestamp}] ", ("time",))
            self.activity_text.insert("end", f"{text}\n", ("message",))

            # Limita la bitácora a 200 líneas para evitar consumo excesivo de memoria
            line_count = int(self.activity_text.index("end-1c").split(".")[0])
            if line_count > 200:
                self.activity_text.delete("1.0", f"{line_count - 200}.0")

            self.activity_text.see("end")
        except (tk.TclError, ValueError):
            pass  # El widget puede estar en proceso de destrucción
        finally:
            try:
                self.activity_text.configure(state="disabled")
            except tk.TclError:
                pass

    def on_exit(self) -> None:
        """Maneja el cierre seguro: bloquea si hay limpieza activa, guarda config y destruye."""
        if self._is_running:
            self._set_status(t("exit_blocked"))
            return

        self._cancel_pending_jobs()
        self._persist_config()
        self.logger.info(t("app_closed"))
        self.root.destroy()

    def _cancel_pending_jobs(self) -> None:
        """Cancela todos los after() pendientes de forma segura antes de destruir la ventana."""
        for attr in ("_countdown_job", "_configure_job", "_save_job", "_queue_job"):
            job = getattr(self, attr, None)
            if job:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, attr, None)

    def open_donate_url(self) -> None:
        """Abre el enlace de donaciones (PayPal) en el navegador predeterminado del sistema."""
        try:
            webbrowser.open_new_tab(DONATE_URL)
        except (webbrowser.Error, OSError):
            pass  # Sin navegador disponible; se ignora silenciosamente

    def _change_language(self, lang: str) -> None:
        """Cambia el idioma activo, guarda la preferencia y reinicia la ventana."""
        if lang == get_language():
            return  # Ya está en el idioma seleccionado; no hace nada

        set_language(lang)
        self.config_manager.update(language=lang)  # Persiste antes de destruir
        self.restart_requested = True
        self._cancel_pending_jobs()
        self.root.destroy()


def run() -> None:
    """Punto de entrada principal.

    Ejecuta MainWindow en un bucle para soportar el reinicio automático
    cuando el usuario cambia de idioma desde el menú.
    """
    while True:
        app = MainWindow()
        app.run()
        if not app.restart_requested:
            break
