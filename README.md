# Governance-Suite

> Suite unificada CLI + GUI para gestión de archivos, permisos NTFS, migración y análisis en servidores Windows/Linux.

## Descripción

Evolución consolidada de 5 proyectos anteriores:
- **FileOpsMaster** — operaciones de archivos V1–V10
- **DemiurgoProject** — arquitectura modular + build .exe
- **PermisosApp** — auditoría de permisos con GUI
- **DemiurgoGUI** — GUI madura + 12 sesiones de auditoría reales
- **OpFiles-Core** — primer intento CLI+GUI con i18n

## Características

- ✅ **Dos interfaces**: CLI interactiva con menús + GUI con pestañas (Tkinter)
- ✅ **Core compartido**: toda la lógica en `core/` — sin duplicación entre interfaces
- ✅ **Menús anidados** en CLI (submenús por módulo)
- ✅ **Tabs unificados** en GUI (una ventana, todas las funciones)
- ✅ **i18n** ES/EN heredado de OpFiles-Core
- ✅ **Logging** por sesión en `logs/`
- ✅ **Exportación** CSV, Excel y JSON
- ✅ **Build** a `.exe` con PyInstaller

## Instalación

```bash
git clone https://github.com/D3miurg0/Governance-Suite.git
cd Governance-Suite
pip install -r requirements.txt
```

## Uso

```bash
# Lanzar GUI (por defecto)
python main.py

# Lanzar CLI
python main.py --cli

# O directamente
python run_gui.py
python run_cli.py
```

## Estructura

```
Governance-Suite/
├── main.py              # Launcher: detecta --cli o lanza GUI
├── run_cli.py           # Entrada directa CLI
├── run_gui.py           # Entrada directa GUI
├── config.py            # Configuración centralizada
├── requirements.txt
├── build.bat            # Build Windows .exe
├── build.sh             # Build Linux/Mac
├── Governance-Suite.spec
│
├── core/                # Motor compartido (sin UI)
│   ├── scanner.py       # Escaneo de servidores remotos
│   ├── migration.py     # Migración de archivos
│   ├── permission.py    # Auditoría de permisos NTFS
│   ├── analysis.py      # Métricas y estadísticas
│   ├── global_analysis.py  # Análisis multi-servidor
│   ├── comparison.py    # Comparación entre auditorías
│   ├── exporter.py      # CSV / Excel / JSON
│   ├── metrics.py       # Métricas de gobernanza
│   └── logger.py        # Logging de sesiones
│
├── cli/                 # Versión CLI
│   ├── menu_main.py     # Menú principal interactivo
│   ├── menu_scan.py
│   ├── menu_migration.py
│   ├── menu_permissions.py
│   ├── menu_analysis.py
│   └── menu_reports.py
│
├── gui/                 # Versión GUI (Tkinter)
│   ├── app.py           # Ventana principal con tabs
│   ├── tab_scan.py
│   ├── tab_migration.py
│   ├── tab_permissions.py
│   ├── tab_analysis.py
│   └── tab_reports.py
│
├── locales/             # i18n
│   ├── es.json
│   └── en.json
│
├── output/              # Resultados (gitignored)
└── logs/                # Logs de sesión (gitignored)
```

## Requisitos

- Python 3.9+
- Windows (recomendado para permisos NTFS) o Linux
- Ver `requirements.txt`

## Licencia

Privado — D3miurg0
