# Governance-Suite v2.2.0

> Suite unificada CLI + GUI para gobernanza de servidores de archivos Windows/Linux: escaneo de unidades, migración de datos (multi-path), análisis y gestión de permisos NTFS, y generación de reportes detallados.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows) ![GUI](https://img.shields.io/badge/GUI-CustomTkinter-informational?logo=python) ![License](https://img.shields.io/badge/License-Private-red)

---

## ¿Qué es Governance-Suite?

Governance-Suite es la evolución consolidada de herramientas previas (DemiurgoGUI, OpFiles-Core, FileOpsMaster, DemiurgoProject y PermisosApp) en una sola aplicación. Ofrece dos modos de operación: una **interfaz gráfica (GUI)** con pestañas para cada módulo y una **interfaz de línea de comandos (CLI)** para automatización y despliegue en servidores.

---

## Módulos principales

| Módulo | Descripción |
|---|---|
| **Escaneo** | Análisis de unidades y estructura de directorios |
| **Migración** | Transferencia y sincronización de archivos entre **múltiples rutas** en paralelo o secuencial |
| **Permisos** | Lectura y auditoría de permisos NTFS vía `pywin32` |
| **Análisis** | Procesamiento estadístico de datos con pandas |
| **Reportes** | Exportación a CSV, Excel y JSON |

---

## Novedades en v2.2.0 — Migración a CustomTkinter

### GUI modernizada con CustomTkinter

Toda la interfaz gráfica migró de `tkinter` estándar a **CustomTkinter**, logrando un diseño moderno con soporte nativo de modo oscuro/claro:

- **Modo oscuro activado por defecto** (`set_appearance_mode("dark")`).
- **Tema de color azul** (`set_default_color_theme("blue")`).
- Todos los widgets `tk.Frame`, `tk.Label`, `tk.Button`, `tk.Entry`, `tk.Checkbutton`, `tk.Radiobutton` reemplazados por sus equivalentes `ctk.*`.
- `ttk.Progressbar` reemplazado por `ctk.CTkProgressBar`.
- Widgets sin equivalente en CTk (`ttk.Treeview`, `ttk.Notebook`, `ttk.Scrollbar`, `ttk.Combobox`) conservados por compatibilidad.

### Archivos GUI actualizados

| Archivo | Cambios |
|---|---|
| `gui/app.py` | Ventana raíz `ctk.CTk()`, modo oscuro, tema azul |
| `gui/tab_scan.py` | Widgets CTk completos, `CTkProgressBar` |
| `gui/tab_analysis.py` | `CTkFrame` como pseudo-LabelFrame, color dinámico en score |
| `gui/tab_permissions.py` | Sustitución completa + `CTkProgressBar` |
| `gui/tab_reports.py` | Botones de cabecera CTk |
| `gui/tab_access_control.py` | `CTkRadioButton`, `CTkCheckBox`, API `.configure()` |

---

## Novedades en v2.1.0 — Migración Multi-Path

### GUI

La pestaña **Migración** ahora soporta **N pares Origen → Destino** configurables de forma dinámica:

- **+ Agregar ruta** — añade un nuevo par Origen/Destino sin límite.
- **✕** — elimina una fila (siempre queda al menos una).
- **Ejecutar rutas en paralelo** — todas las rutas corren simultáneamente; desactivado = modo secuencial.
- **Barra de progreso global** — acumula el avance de todas las rutas activas en tiempo real.
- **Log con colores por estado** — `[OK]` verde, `[UPDATED]` azul, `[SKIPPED]` gris, `[ERROR]` rojo.

### Core — `migrate_multi_paths()`

Nueva función en `core/migration.py`, compatible con la función individual `migrate_directory()` existente:

```python
from core.migration import migrate_multi_paths

resultados = migrate_multi_paths(
    paths=[
        (r"\\NAS\Depto1",  r"D:\Backup\Depto1"),
        (r"\\NAS\Depto2",  r"D:\Backup\Depto2"),
        (r"\\NAS\Proyectos", r"E:\Archive\Proyectos"),
    ],
    parallel_paths=True,      # True = todas a la vez | False = secuencial
    verify=True,              # Verifica integridad MD5 tras cada copia
    sync_only=True,           # Solo copia si origen es más nuevo o distinto tamaño
    overwrite=False,
    threads_per_path=4,       # Hilos internos por cada ruta
    year=2025,                # Opcional: solo archivos del año indicado
    # date_from=datetime(2025,1,1), date_to=datetime(2025,12,31)
)

# Retorna: { src_dir: [{"src", "dst", "status", "error", ...}] }
for ruta, archivos in resultados.items():
    errores = [a for a in archivos if a["status"] == "error"]
    print(f"{ruta}: {len(archivos)} archivos, {len(errores)} errores")
```

#### Parámetros de `migrate_multi_paths()`

| Parámetro | Tipo | Descripción |
|---|---|---|
| `paths` | `List[Tuple[str,str]]` | Lista de pares `(src_dir, dst_dir)` |
| `parallel_paths` | `bool` | `True` = rutas en paralelo (default), `False` = secuencial |
| `threads_per_path` | `int` | Hilos internos por cada `migrate_directory` (default: `DEFAULT_THREADS`) |
| `verify` | `bool` | Verificación de checksum MD5 tras cada archivo |
| `overwrite` | `bool` | Sobreescribir destino aunque exista |
| `sync_only` | `bool` | Solo copiar si origen es más nuevo o de distinto tamaño |
| `extensions` | `List[str]` | Filtrar por extensiones, ej. `[".docx", ".pdf"]` |
| `year` | `int` | Solo archivos modificados en el año indicado |
| `date_from` | `datetime` | Solo archivos modificados desde esta fecha |
| `date_to` | `datetime` | Solo archivos modificados hasta esta fecha |
| `progress_callback` | `Callable` | `fn(path_idx, src, done, total, result)` — recibe índice de ruta y avance |

#### Retorno

```python
{
  "\\\\NAS\\Depto1":    [ {"src": "...", "dst": "...", "status": "ok",      "checksum": "..."}, ... ],
  "\\\\NAS\\Depto2":    [ {"src": "...", "dst": "...", "status": "updated", "checksum": "..."}, ... ],
  "\\\\NAS\\Proyectos": [ {"src": "...", "dst": "...", "status": "skipped", "error": "..."}, ... ],
}
```

---

## Requisitos previos

- Windows 10/11 o Windows Server 2016/2019/2022
- **Python 3.10 o superior** (solo para ejecución con venv o compilación)  
  Descarga: https://www.python.org/downloads/
- Para despliegue en servidor como `.exe`: **no se requiere Python**

---

## Opción 1 — Ejecución local con venv

### Instalación (una sola vez)

```bat
instalar.bat
```

### Lanzar la app

```bat
run.bat
```

---

## Opción 2 — Compilar .exe para servidor

### Compilar

```bat
build.bat
```

El ejecutable queda en `dist\` junto con las carpetas `logs\` y `output\`.

### Desplegar en servidor

Copiar estos 3 elementos al servidor:

```
GovernanceSuite.exe
logs\
output\
```

Doble clic en `GovernanceSuite.exe` para iniciar. **No requiere Python instalado.**

---

## Ejecución con cuenta de dominio

```bat
runas /user:DOMINIO\usuario "C:\ruta\GovernanceSuite.exe"
```

**Ejemplo:**
```bat
runas /user:gap.net\spectragap "C:\GovernanceSuite\GovernanceSuite.exe"
```

Si ya estás logueado en el servidor con la cuenta correcta, basta con doble clic.

---

## Estructura del proyecto

```
Governance-Suite/
├── run_gui.py               # Punto de entrada GUI
├── run_cli.py               # Punto de entrada CLI
├── config.py                # Configuración global (compatible venv y .exe)
├── instalar.bat             # Instalación automática (ejecutar una vez)
├── run.bat                  # Lanzador rápido (venv)
├── build.bat                # Compilar .exe para despliegue en servidor
├── requirements.txt         # Dependencias Python
├── gui/                     # Interfaz gráfica (CustomTkinter + ttk híbrido)
│   ├── app.py
│   ├── tab_scan.py
│   ├── tab_migration.py          # ← Multi-path: N pares Origen→Destino
│   ├── tab_permissions.py
│   ├── tab_analysis.py
│   ├── tab_reports.py
│   └── tab_access_control.py
├── core/                    # Lógica de negocio
│   ├── scanner.py
│   ├── migration.py              # ← migrate_directory() + migrate_multi_paths()
│   ├── permission.py
│   ├── analysis.py
│   └── logger.py
├── output/                  # Reportes exportados (CSV, Excel, JSON)
└── logs/                    # Logs de sesión
```

---

## Dependencias

| Paquete | Uso |
|---|---|
| `customtkinter` | GUI moderna con soporte modo oscuro/claro |
| `pandas` | Procesamiento de datos |
| `openpyxl` / `xlsxwriter` | Exportación a Excel |
| `pywin32` | Lectura de permisos NTFS (Windows, descomentar en requirements) |
| `colorama` | Colores en CLI |
| `tqdm` | Barras de progreso CLI |
| `pyinstaller` | Compilación a .exe (descomentar en requirements) |

> **Nota:** `tkinter` y `ttk` son parte de la stdlib de Python y no requieren instalación. `ttk.Treeview`, `ttk.Notebook`, `ttk.Scrollbar` y `ttk.Combobox` se conservan al no tener equivalente nativo en CustomTkinter.

---

## Historial de versiones

- **v2.2.0** — Migración completa de GUI a CustomTkinter: modo oscuro nativo, widgets modernos (`CTkButton`, `CTkEntry`, `CTkCheckBox`, `CTkRadioButton`, `CTkProgressBar`); `ttk` conservado donde no hay equivalente CTk
- **v2.1.0** — Migración multi-path: N rutas en paralelo o secuencial, nueva función `migrate_multi_paths()`, GUI dinámica con log a color y progreso global unificado
- **v2.0.0** — Suite unificada, arquitectura modular GUI + CLI
- **v1.x** — Herramientas individuales (DemiurgoGUI, PermisosApp, FileOpsMaster, etc.)
