"""
core/compat.py — Compatibilidad de dependencias opcionales.

Importar desde aquí en lugar de repetir el bloque try/except
en cada módulo.
"""

# ── tqdm ─────────────────────────────────────────────────────────────────────
try:
    from tqdm import tqdm  # noqa: F401
    USE_TQDM = True
except ImportError:
    USE_TQDM = False

    class tqdm:  # type: ignore[no-redef]
        """Fallback silencioso cuando tqdm no está instalado."""

        def __init__(self, iterable=None, desc=None, unit="it", **kwargs):
            self.iterable = iterable

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def update(self, n=1):
            pass

        def set_description(self, s):
            pass

        def close(self):
            pass

        @staticmethod
        def write(s: str):
            print(s)

        def __iter__(self):
            return iter(self.iterable) if self.iterable is not None else iter([])
