# LimpiarAxess

Aplicación de escritorio en Python para limpiar de forma recursiva el contenido de una carpeta seleccionada, con GUI y configuración persistente.

## Funcionalidades

- Borrado recursivo del contenido de carpeta objetivo (mantiene la carpeta raíz).
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

## Compilar sin ventana de CMD

```powershell
.\build.ps1
```

Genera el ejecutable en `dist\LimpiarAxess.exe` usando `--windowed`.

## Incrementar versión (0.0.1)

```powershell
python .\scripts\bump_version.py
```
