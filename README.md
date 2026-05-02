# LimpiarAxess v0.3.0

Aplicación de escritorio en Python para vaciar de forma segura el contenido de una carpeta, manteniendo la carpeta raíz, con una interfaz renovada tipo dashboard, validaciones defensivas y empaquetado para Windows.

## Qué hace

- Elimina de forma recursiva archivos y subcarpetas dentro del destino seleccionado.
- Mantiene intacta la carpeta principal para evitar borrados más agresivos de lo esperado.
- Reintenta el borrado de archivos de solo lectura.
- Bloquea rutas críticas como la raíz del disco, el HOME del usuario o la carpeta de la propia app.
- Permite proteger la ejecución con password almacenado como hash PBKDF2 + salt.
- Guarda configuración de ventana y preferencias de uso automáticamente.
- Registra actividad en `log.txt`.

## Requisitos

- Windows 10/11
- Python 3.11 o superior para ejecutar desde código fuente
- Dependencias de runtime: ninguna externa, solo librería estándar
- Dependencia de build: `PyInstaller` definida en `requirements-build.txt`

## Ejecutar en desarrollo

```powershell
python main.py
```

En el primer arranque se genera `config.json` automáticamente a partir de los valores por defecto del código. El archivo `config.example.json` se conserva como plantilla documentada para el repositorio.

## Compilar

```powershell
.\build.ps1
```

El build genera `LimpiarAxess.exe` en la misma carpeta raíz donde está `main.py`, usando `limpiar.ico` y metadatos de versión para el ejecutable de Windows.

## Versionado y releases

El proyecto usa Semantic Versioning (`vX.Y.Z`):

- `patch`: correcciones compatibles
- `minor`: nuevas funcionalidades compatibles
- `major`: cambios incompatibles

La versión debe coincidir entre:

- `backend/version.py`
- `config.example.json`
- `pyproject.toml`
- `README.md`
- Tag de GitHub `vX.Y.Z`
- Título/About de la app
- Metadatos del `.exe`

Flujo recomendado para publicar cada commit con su propia versión:

```powershell
.\scripts\release.ps1 -Bump minor -Message "feat: moderniza la GUI y alinea releases"
```

Ese script:

1. Incrementa la versión en todos los archivos sincronizados.
2. Ejecuta pruebas.
3. Recompila el `.exe` en la raíz.
4. Crea el commit.
5. Crea el tag `vX.Y.Z`.
6. Hace push de `main` y del tag.

## CI/CD

- `CI`: valida pruebas en cada push o pull request contra `main`.
- `Release`: al recibir un tag `vX.Y.Z`, recompila en Windows y publica el ejecutable como asset del release de GitHub.

## Estructura

- `frontend/`: interfaz gráfica
- `backend/`: lógica de limpieza, seguridad, rutas y configuración
- `scripts/`: automatización de versionado, release y build metadata
- `tests/`: pruebas unitarias y de sincronización de versión

## Licencia

Distribuido bajo Apache License 2.0. Ver [`LICENSE`](LICENSE).
