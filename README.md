# Governance-Suite v2.0.0

Herramienta de gobernanza para escaneo, migración, análisis de permisos NTFS y generación de reportes sobre servidores de archivos Windows.

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
├── run_gui.py          # Punto de entrada GUI
├── run_cli.py          # Punto de entrada CLI
├── config.py           # Configuración global (compatible venv y .exe)
├── instalar.bat        # Instalación automática (ejecutar una vez)
├── run.bat             # Lanzador rápido (venv)
├── build.bat           # Compilar .exe para despliegue en servidor
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
│   ├── migration.py
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
| `pyinstaller` | Compilación a .exe (solo en equipo de desarrollo) |
