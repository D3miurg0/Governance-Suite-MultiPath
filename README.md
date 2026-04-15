# Governance-Suite v2.0.0

Herramienta de gobernanza para escaneo, migración, análisis de permisos NTFS y generación de reportes sobre servidores de archivos Windows.

---

## Requisitos previos

- Windows 10/11
- **Python 3.10 o superior** instalado y en el PATH  
  Descarga: https://www.python.org/downloads/

---

## Instalación (una sola vez por máquina)

1. Copia o descarga la carpeta del proyecto en la máquina destino.
2. Doble clic en **`instalar.bat`**.
   - Crea el entorno virtual `venv`
   - Instala todas las dependencias (`requirements.txt`, `pywin32`, `ttkthemes`)
   - Crea las carpetas `logs/` y `output/`

---

## Ejecución normal

Doble clic en **`run.bat`**, o desde CMD:

```bat
call venv\Scripts\activate
python run_gui.py
```

---

## Ejecución con otra cuenta (recomendado para leer permisos NTFS)

Para acceder a rutas de red protegidas, ejecuta con una cuenta de dominio con privilegios:

```bat
runas /user:DOMINIO\usuario "cmd /k cd /d C:\ruta\Governance-Suite && venv\Scripts\activate && python run_gui.py"
```

**Ejemplo real:**
```bat
runas /user:gap.net\spectragap "cmd /k cd /d C:\Users\e.siapti2\Downloads\Aranda\Governance-Suite-main\Governance-Suite-main && venv\Scripts\activate && python run_gui.py"
```

Se pedirá la contraseña de la cuenta indicada.

---

## Estructura del proyecto

```
Governance-Suite/
├── run_gui.py          # Punto de entrada GUI
├── run_cli.py          # Punto de entrada CLI
├── config.py           # Configuración global
├── instalar.bat        # Instalación automática (ejecutar una vez)
├── run.bat             # Lanzador rápido
├── requirements.txt    # Dependencias Python
├── gui/                # Interfaz gráfica (tabs)
│   ├── app.py
│   ├── tab_scan.py
│   ├── tab_migration.py
│   ├── tab_permissions.py
│   ├── tab_analysis.py
│   └── tab_reports.py
├── core/               # Lógica de negocio
│   ├── scanner.py
│   ├── migrator.py
│   ├── permissions.py
│   ├── analyzer.py
│   └── logger.py
├── output/             # Reportes exportados (CSV, Excel, JSON)
└── logs/               # Logs de sesión
```

---

## Dependencias

| Paquete | Uso |
|---|---|
| `pandas` | Procesamiento de datos |
| `openpyxl` / `xlsxwriter` | Exportación a Excel |
| `pywin32` | Lectura de permisos NTFS (Windows) |
| `ttkthemes` | Temas visuales para la GUI |
| `colorama` | Colores en CLI |
| `tqdm` | Barras de progreso CLI |

---

## Notas

- Los archivos exportados se guardan en `output/`
- Los logs de sesión se guardan en `logs/`
- El tema visual por defecto es `clam` (compatible con todos los sistemas Windows sin dependencias adicionales)
