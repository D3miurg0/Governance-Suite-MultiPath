# Governance-Suite

> Plataforma unificada de gobernanza de archivos: escaneo, migración, auditoría de permisos NTFS y dashboards analíticos.

---

## Requisitos

- Python 3.11+
- Windows (recomendado para módulo de permisos NTFS)

```bash
pip install -r requirements.txt
# Solo en Windows, para auditoría de permisos:
pip install pywin32
```

---

## Uso rápido

```bash
python main.py
```

Se abrirá el menú interactivo principal con las siguientes opciones:

| Opción | Función |
|--------|--------|
| 1 | Escaneo de archivos (multi-hilo, por año) |
| 2 | Migración paralela/streaming con filtros de fecha |
| 3 | Auditoría de permisos NTFS (ACL) |
| 4 | Dashboard Excel consolidado |
| 5 | Reportes y exportación |

---

## Estructura del proyecto

```
Governance-Suite/
├── main.py                  # Launcher
├── config.py                # Constantes globales
├── requirements.txt
├── core/
│   ├── audit.py             # Sesión, locks, logging
│   ├── utils.py             # Utilidades compartidas
│   └── language.py          # Strings de idioma
├── modules/
│   ├── scan.py              # Escaneo multi-hilo
│   ├── migration.py         # Migración paralela/streaming
│   ├── permission.py        # Auditoría ACL NTFS
│   └── analysis.py          # Dashboard Excel
└── cli/
    ├── menu_main.py         # Menú raíz
    ├── menu_scan.py
    ├── menu_migration.py
    ├── menu_permissions.py
    ├── menu_analysis.py
    └── menu_reports.py
```

---

## Notas

- El módulo de permisos ACL requiere `pywin32` y ejecución con privilegios en Windows.
- Los reportes se guardan en `output/<timestamp>/` dentro del directorio del proyecto.
- Compatible con rutas largas UNC (`\\?\UNC\` y `\\?\`).
