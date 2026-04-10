# Governance-Suite

Suite unificada **CLI + GUI** para administración de archivos, permisos NTFS, migración y análisis en infraestructura Windows/Linux.

> Evolución consolidada de: `DemiurgoGUI` · `OpFiles-Core` · `FileOpsMaster` · `DemiurgoProject` · `PermisosApp`

---

## Características

| Módulo | Descripción |
|---|---|
| 🔍 **Scanner** | Escaneo multi-hilo de metadatos de archivos en rutas locales y UNC |
| 📦 **Migration** | Migración paralela/streaming con reintentos y manejo de permisos NTFS |
| 🔐 **Permissions** | Auditoría completa de permisos NTFS con exportación CSV |
| 📊 **Analysis** | Análisis de reportes CSV por año, tamaño y tipo |
| 🌍 **Global Analysis** | Análisis multi-servidor consolidado |
| ↔️ **Comparison** | Comparación entre auditorías (diff de permisos) |
| 📤 **Exporter** | Exportación a CSV, Excel y JSON |
| 📝 **Logs** | Sistema de log por sesión de auditoría |

---

## Modos de ejecución

```bash
# Lanzador automático (detecta --cli o lanza GUI)
python main.py

# Modo CLI interactivo
python main.py --cli
python run_cli.py

# Modo GUI (Tkinter)
python run_gui.py
```

---

## Instalación

```bash
git clone https://github.com/D3miurg0/Governance-Suite.git
cd Governance-Suite
pip install -r requirements.txt
```

### Dependencias opcionales (Windows)
```bash
pip install pywin32   # Para gestión de permisos NTFS
```

---

## Estructura del proyecto

```
Governance-Suite/
├── main.py               # Launcher principal (CLI o GUI)
├── run_cli.py            # Entrada directa CLI
├── run_gui.py            # Entrada directa GUI
├── config.py             # Configuración centralizada
├── requirements.txt
│
├── core/                 # Motor compartido (sin dependencias de UI)
│   ├── audit.py          # Sesión de auditoría y logging
│   ├── utils.py          # Utilidades generales
│   └── language.py       # Sistema i18n
│
├── modules/              # Módulos funcionales
│   ├── scan.py           # Escaneo de archivos multi-hilo
│   ├── migration.py      # Migración de archivos
│   ├── permission.py     # Auditoría de permisos NTFS
│   ├── analysis.py       # Análisis de métricas
│   ├── global_analysis.py# Análisis multi-servidor
│   ├── comparison.py     # Comparación entre auditorías
│   ├── exporter.py       # Exportadores CSV/Excel/JSON
│   └── excel_rewriter.py # Reescritura/normalización Excel
│
├── cli/                  # Interfaz CLI con menús interactivos
│   ├── menu_main.py      # Menú principal
│   ├── menu_scan.py      # Submenú escaneo
│   ├── menu_migration.py # Submenú migración
│   ├── menu_permissions.py# Submenú permisos
│   ├── menu_analysis.py  # Submenú análisis
│   └── menu_reports.py   # Submenú reportes
│
├── gui/                  # Interfaz gráfica Tkinter
│   ├── app.py            # Ventana principal con tabs
│   ├── tab_scan.py       # Tab escaneo
│   ├── tab_migration.py  # Tab migración
│   ├── tab_permissions.py# Tab permisos
│   ├── tab_analysis.py   # Tab análisis
│   └── tab_reports.py    # Tab reportes
│
├── locales/              # Internacionalización
│   ├── es.json           # Español
│   └── en.json           # Inglés
│
├── output/               # Resultados generados (gitignored)
└── logs/                 # Logs de sesión (gitignored)
```

---

## Requisitos

- Python 3.9+
- Windows (recomendado para permisos NTFS) o Linux
- Ver `requirements.txt`

---

## Licencia

Proyecto privado — D3miurg0 / Luis Eduardo Sánchez González
