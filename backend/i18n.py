"""Módulo de internacionalización (i18n) de LimpiarAxess.

Soporta español ('es') e inglés ('en').
Uso:
    from backend.i18n import t, set_language, get_language

    set_language("en")
    print(t("btn_exit"))          # → "Exit"
    print(t("autoclose_active", sec=30))  # → "Auto-close active. Configured time: 30s."
"""
from __future__ import annotations

# ── Idioma activo ────────────────────────────────────────────────────────────
# Modificado por set_language(); predeterminado: español.
_LANG: str = "es"

# ── Diccionario de traducciones ──────────────────────────────────────────────
# Formato: "clave": {"es": "...", "en": "..."}
# Los marcadores {nombre} se sustituyen por t(key, nombre=valor).
# Los marcadores %s/%d se usan tal cual para el módulo logging de Python.
_TRANSLATIONS: dict[str, dict[str, str]] = {

    # ── Estados de la aplicación ─────────────────────────────────────────────
    "app_ready": {
        "es": "Aplicación lista.",
        "en": "Application ready.",
    },
    "config_loaded": {
        "es": "Configuración cargada.",
        "en": "Configuration loaded.",
    },
    # Cadenas de formato para logging (usan %s nativo de Python logging)
    "app_started": {
        "es": "Aplicación iniciada. Versión %s",
        "en": "Application started. Version %s",
    },
    "app_closed": {
        "es": "Aplicación cerrada.",
        "en": "Application closed.",
    },

    # ── Menú ─────────────────────────────────────────────────────────────────
    "menu_file": {"es": "Archivo", "en": "File"},
    "menu_start_cleanup": {"es": "Iniciar limpieza", "en": "Start cleanup"},
    "menu_select_folder": {"es": "Seleccionar carpeta", "en": "Select folder"},
    "menu_exit": {"es": "Salir", "en": "Exit"},
    "menu_help": {"es": "Ayuda", "en": "Help"},
    "menu_about": {"es": "About", "en": "About"},
    "menu_language": {"es": "Idioma", "en": "Language"},

    # ── Sección hero ─────────────────────────────────────────────────────────
    "hero_subtitle": {
        "es": "Limpieza segura, ahora en una distribución más cómoda",
        "en": "Safe cleanup, now in a more comfortable layout",
    },
    "hero_description": {
        "es": "Destino, automatización, seguridad, métricas y bitácora accesibles desde la vista inicial.",
        "en": "Target, automation, security, metrics and log accessible from the main view.",
    },

    # ── Botones principales ───────────────────────────────────────────────────
    "btn_start_cleanup": {"es": "Iniciar limpieza", "en": "Start cleanup"},
    "btn_browse_folder": {"es": "Examinar carpeta", "en": "Browse folder"},
    "btn_exit": {"es": "Salir", "en": "Exit"},
    "btn_browse": {"es": "Examinar", "en": "Browse"},
    "btn_show_password": {"es": "Mostrar", "en": "Show"},
    "btn_hide_password": {"es": "Ocultar", "en": "Hide"},
    "btn_save_password": {"es": "Guardar password", "en": "Save password"},
    "btn_about": {"es": "About", "en": "About"},
    "btn_close": {"es": "Cerrar", "en": "Close"},
    "btn_donate": {"es": "☕ Cómprame una cerveza", "en": "☕ Buy me a beer"},

    # ── Panel Controles ───────────────────────────────────────────────────────
    "section_controls": {"es": "Controles", "en": "Controls"},
    "label_target": {"es": "Destino de limpieza", "en": "Cleanup target"},
    "no_folder_selected": {
        "es": "No hay carpeta seleccionada todavía.",
        "en": "No folder selected yet.",
    },
    "target_ready": {
        "es": "Destino listo: {name} | Ruta completa: {path}",
        "en": "Target ready: {name} | Full path: {path}",
    },
    "footer_note": {
        "es": "Validación de rutas críticas, guardado automático, log rotativo y password con hash.",
        "en": "Critical path validation, auto-save, rotating log and hashed password.",
    },

    # ── Panel Automatización ──────────────────────────────────────────────────
    "section_automation": {"es": "Automatización", "en": "Automation"},
    "check_auto_start": {"es": "Auto iniciar al abrir", "en": "Auto start on open"},
    "check_auto_close": {"es": "Habilitar autocierre", "en": "Enable auto-close"},
    "label_auto_close_seconds": {"es": "Segundos para autocierre", "en": "Seconds for auto-close"},
    "autoclose_disabled": {
        "es": "Autocierre desactivado. La ventana seguirá abierta hasta salir manualmente.",
        "en": "Auto-close disabled. Window stays open until manually closed.",
    },
    "autoclose_active": {
        "es": "Autocierre activo. Tiempo configurado: {sec}s.",
        "en": "Auto-close active. Configured time: {sec}s.",
    },
    "autoclose_paused_extra": {
        "es": "Autocierre pausado durante limpieza.",
        "en": "Auto-close paused during cleanup.",
    },
    "autoclose_paused_running": {
        "es": "Autocierre pausado mientras hay trabajo en curso.",
        "en": "Auto-close paused while cleanup is in progress.",
    },
    "autoclose_paused_cleanup": {
        "es": "Autocierre pausado mientras se completa la limpieza.",
        "en": "Auto-close paused while cleanup completes.",
    },
    "autoclose_countdown": {
        "es": "La aplicación se cerrará sola en {sec}s si permanece inactiva.",
        "en": "The application will close in {sec}s if left idle.",
    },
    "autoclose_countdown_short": {
        "es": "Autocierre en {sec}s",
        "en": "Auto-close in {sec}s",
    },
    "autoclose_executed": {
        "es": "Autocierre ejecutado.",
        "en": "Auto-close executed.",
    },

    # ── Panel Seguridad ───────────────────────────────────────────────────────
    "section_security": {"es": "Seguridad y acceso", "en": "Security & access"},
    "check_require_password": {
        "es": "Requerir password para limpiar",
        "en": "Require password to clean",
    },
    "security_inactive": {
        "es": "Protección opcional desactivada. Puedes iniciar la limpieza directamente.",
        "en": "Optional protection disabled. You can start cleanup directly.",
    },
    "security_active_with_hash": {
        "es": "Protección activa. Escribe la clave actual y luego ejecuta la limpieza.",
        "en": "Protection active. Enter the current password then start cleanup.",
    },
    "security_active_no_hash": {
        "es": "Protección activa, pero todavía no hay password guardado.",
        "en": "Protection active, but no password has been saved yet.",
    },

    # ── Centro de actividad ───────────────────────────────────────────────────
    "section_activity": {"es": "Centro de actividad", "en": "Activity center"},

    # ── Tiles de métricas ─────────────────────────────────────────────────────
    "stat_files": {"es": "Archivos", "en": "Files"},
    "stat_dirs": {"es": "Carpetas", "en": "Folders"},
    "stat_errors": {"es": "Errores", "en": "Errors"},
    "stat_duration": {"es": "Duración", "en": "Duration"},
    "in_progress": {"es": "En curso", "en": "In progress"},

    # ── Mensajes de estado ────────────────────────────────────────────────────
    "already_running": {
        "es": "La limpieza ya está en ejecución.",
        "en": "Cleanup is already running.",
    },
    "cleanup_started": {
        "es": "Limpieza iniciada en segundo plano...",
        "en": "Cleanup started in background...",
    },
    "cleanup_result": {
        "es": "Finalizado: {files} archivos, {dirs} carpetas, {errors} errores.",
        "en": "Done: {files} files, {dirs} folders, {errors} errors.",
    },
    "error_prefix": {
        "es": "Error: {msg}",
        "en": "Error: {msg}",
    },
    "folder_selected": {
        "es": "Carpeta seleccionada: {path}",
        "en": "Folder selected: {path}",
    },
    "exit_blocked": {
        "es": "Espera a que termine la limpieza antes de salir.",
        "en": "Wait for cleanup to finish before exiting.",
    },
    "password_too_short": {
        "es": "El password debe tener al menos 4 caracteres.",
        "en": "Password must be at least 4 characters.",
    },
    "password_saved": {
        "es": "Password guardado de forma segura.",
        "en": "Password saved securely.",
    },
    "password_required_no_hash": {
        "es": "Activa protección por password, pero no hay password guardado.",
        "en": "Password protection enabled, but no password has been saved.",
    },
    "password_invalid": {
        "es": "Password inválido.",
        "en": "Invalid password.",
    },

    # ── Cadenas de log (formato %s para Python logging) ───────────────────────
    "password_updated": {
        "es": "Password de protección actualizado.",
        "en": "Protection password updated.",
    },
    "cleanup_started_log": {
        "es": "Limpieza iniciada. Ruta objetivo: %s",
        "en": "Cleanup started. Target path: %s",
    },
    "cleanup_failed_log": {
        "es": "Fallo de limpieza: %s",
        "en": "Cleanup failed: %s",
    },

    # ── Diálogo About ─────────────────────────────────────────────────────────
    "about_title": {"es": "About", "en": "About"},
    "about_description": {
        "es": (
            "Herramienta de escritorio para vaciar el contenido de una carpeta con validaciones "
            "de seguridad, log local y automatización opcional."
        ),
        "en": (
            "Desktop tool to clear folder contents with security validations, "
            "local log and optional automation."
        ),
    },
    "about_author": {"es": "Autor: Synyster Rick", "en": "Author: Synyster Rick"},
    "about_license": {"es": "Licencia: Apache License 2.0", "en": "License: Apache License 2.0"},
    "about_copyright": {"es": "Copyright {year}", "en": "Copyright {year}"},
    "about_donate_label": {
        "es": "¿Te gusta la herramienta? ☕",
        "en": "Like the tool? ☕",
    },
}


# ── API pública ──────────────────────────────────────────────────────────────

def set_language(lang: str) -> None:
    """Establece el idioma activo.

    Args:
        lang: Código de idioma. Valores válidos: ``'es'`` (español) o ``'en'`` (inglés).
              Cualquier otro valor se ignora silenciosamente.
    """
    global _LANG  # noqa: PLW0603
    if lang in ("es", "en"):
        _LANG = lang


def get_language() -> str:
    """Devuelve el código del idioma actualmente activo (``'es'`` o ``'en'``)."""
    return _LANG


def t(key: str, **kwargs: object) -> str:
    """Devuelve la cadena traducida para *key* en el idioma activo.

    Si la clave no existe devuelve la propia clave como texto de reserva.
    Soporta sustituciones tipo ``str.format()``::

        t("target_ready", name="tmp", path="/tmp/tmp")

    Las cadenas de log con ``%s`` se devuelven sin sustitución para que
    el módulo ``logging`` de Python las interpole en tiempo de emisión.

    Args:
        key:    Identificador de la cadena en ``_TRANSLATIONS``.
        **kwargs: Valores para sustitución de marcadores ``{nombre}``.

    Returns:
        Cadena traducida (y formateada si se pasaron kwargs).
    """
    entry = _TRANSLATIONS.get(key)
    if entry is None:
        return key  # Clave desconocida: devuelve la clave como texto de reserva

    # Preferencia: idioma activo; si no existe, español; si no, la clave
    text = entry.get(_LANG) or entry.get("es") or key

    # Aplica sustituciones sólo si se proporcionaron kwargs
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass  # Devuelve el texto sin sustituir si hay un error de formato

    return text
