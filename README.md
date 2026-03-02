# LimpiarAxess v0.1.0

Aplicación de escritorio en Python para limpiar de forma recursiva el contenido de una carpeta seleccionada, con GUI y configuración persistente.

## Funcionalidades

- **Borrado recursivo robusto** del contenido de carpeta objetivo (mantiene la carpeta raíz).
- Manejo de archivos/carpetas de solo lectura con reintento automático.
- Validaciones de seguridad para evitar rutas críticas.
- Barra de estado informativa (sin messagebox para el flujo operativo).
- Log con timestamp en `log.txt`.
- Auto inicio del proceso al abrir la app.
- Autocierre configurable con countdown visible en la barra de estado.
- Password opcional para ejecutar limpieza (almacenado como hash PBKDF2 + salt).
- Guardado automático de cambios en `config.json`.
- Recuerdo de posición/tamaño de la ventana.
- Menú `About`.
- Atajos de teclado estilo Windows.

## Atajos

- `Ctrl+O`: seleccionar carpeta.
- `F5` o `Alt+S`: iniciar limpieza.
- `Ctrl+G`: guardar password.
- `F1`: abrir About.
- `Ctrl+Q` o `Alt+X`: salir.

## Ejecutar

```powershell
python main.py
```

## Compilar

```powershell
.\build.ps1
```

Genera el ejecutable `LimpiarAxess.exe` en la raíz del proyecto usando `--windowed` y el icono local `limpiar.ico`.

## Versionamiento (Semantic Versioning)

La versión actual se mantiene sincronizada en:
- `backend/version.py`
- `config.json`
- Tags de Git
- Releases de GitHub

### Incrementar versión

```powershell
# Corrección de bugs (0.1.0 → 0.1.1)
python .\scripts\bump_version.py patch

# Nueva funcionalidad compatible (0.1.0 → 0.2.0)
python .\scripts\bump_version.py minor

# Cambios incompatibles (0.1.0 → 1.0.0)
python .\scripts\bump_version.py major
```

## CI/CD

Cada push a `main` ejecuta automáticamente:
1. Build del ejecutable en Windows
2. Creación de release con tag `vX.Y.Z`
3. Publicación del `.exe` como asset del release
