import os
import json
import locale


class LanguageManager:
    """Singleton para gestión de idioma (ES/EN) con dot-notation."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.locale_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locales"
        )
        self.current_lang = self._detect_os_language()
        self.translations: dict = {}
        self.load_language(self.current_lang)

    def _detect_os_language(self) -> str:
        try:
            os_lang = locale.getdefaultlocale()[0]
            if os_lang and os_lang.lower().startswith('es'):
                return 'es'
        except Exception:
            pass
        return 'en'

    def load_language(self, lang_code: str):
        file_path = os.path.join(self.locale_dir, f"{lang_code}.json")
        if not os.path.exists(file_path):
            lang_code = 'en'
            file_path = os.path.join(self.locale_dir, "en.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.current_lang = lang_code
        except Exception as e:
            print(f"Error cargando idioma {lang_code}: {e}")
            self.translations = {}

    def get(self, key: str, default: str = None) -> str:
        keys = key.split('.')
        val = self.translations
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default or key
        return str(val) if val is not None else (default or key)


# Instancia global
LANG = LanguageManager()
