"""
Governance Suite - Ventana principal GUI con tabs (customtkinter)
"""
import customtkinter as ctk
from tkinter import ttk
from config import APP_NAME, VERSION, GUI_WINDOW_SIZE, GUI_MIN_SIZE, ICON_PATH

# Tema global CTk
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Paleta Catppuccin Mocha
_BG      = "#1e1e2e"
_FG      = "#cdd6f4"
_ACCENT  = "#89b4fa"
_SURFACE = "#313244"


class GovernanceApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title(f"{APP_NAME}  v{VERSION}")
        w, h = (int(x) for x in GUI_WINDOW_SIZE.split("x"))
        self.root.geometry(f"{w}x{h}")
        self.root.minsize(*GUI_MIN_SIZE)
        self._load_icon()
        self._colors = {"bg": _BG, "fg": _FG, "accent": _ACCENT, "surface": _SURFACE}
        self._build_ui()

    def _load_icon(self):
        try:
            self.root.iconbitmap(str(ICON_PATH))
        except Exception:
            pass

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self.root, fg_color=_SURFACE, corner_radius=0, height=46)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text=f"  \U0001f6e1\ufe0f  {APP_NAME}",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            text_color=_ACCENT
        ).pack(side="left", padx=12)
        ctk.CTkLabel(
            header,
            text=f"v{VERSION}",
            font=ctk.CTkFont("Segoe UI", 9),
            text_color="#6c7086"
        ).pack(side="left", padx=(0, 16))
        ctk.CTkLabel(
            header,
            text="File Governance Platform",
            font=ctk.CTkFont(family="Segoe UI", size=9, slant="italic"),
            text_color="#6c7086"
        ).pack(side="right", padx=16)

        # Notebook (ttk.Notebook se mantiene; CTk no tiene equivalente nativo)
        from tkinter import ttk
        import tkinter as tk
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TNotebook",     background=_BG,      borderwidth=0)
        style.configure("TNotebook.Tab", background=_SURFACE, foreground=_FG,
                        padding=[14, 6], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", _ACCENT)],
                  foreground=[("selected", "#1e1e2e")])
        style.configure("TFrame",   background=_BG)
        style.configure("Treeview", background=_SURFACE, foreground=_FG,
                        fieldbackground=_SURFACE, rowheight=24)
        style.configure("Treeview.Heading", background=_BG, foreground=_ACCENT,
                        font=("Segoe UI", 10, "bold"))
        style.configure("TScrollbar", background=_SURFACE, troughcolor=_BG)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        from gui.tab_scan        import ScanTab
        from gui.tab_migration   import MigrationTab
        from gui.tab_permissions import PermissionsTab
        from gui.tab_analysis    import AnalysisTab
        from gui.tab_reports     import ReportsTab

        tabs = [
            ("  \U0001f50d  Escaneo",   ScanTab),
            ("  \U0001f4c2  Migracion", MigrationTab),
            ("  \U0001f512  Permisos",  PermissionsTab),
            ("  \U0001f4ca  Analisis",  AnalysisTab),
            ("  \U0001f4c4  Reportes",  ReportsTab),
        ]
        for label, TabClass in tabs:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=label)
            TabClass(frame, self._colors).build()

        # Status bar
        self.status_var = tk.StringVar(value="Listo")
        status_bar = tk.Label(
            self.root, textvariable=self.status_var,
            bd=1, relief="sunken", anchor="w",
            bg=_SURFACE, fg="#6c7086",
            font=("Segoe UI", 9), padx=8
        )
        status_bar.pack(side="bottom", fill="x")

    def run(self):
        self.root.mainloop()
