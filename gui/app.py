"""
Governance Suite - Ventana principal GUI con tabs
"""
import tkinter as tk
from tkinter import ttk
from config import APP_NAME, APP_NAME_FULL, VERSION, GUI_THEME, GUI_WINDOW_SIZE, GUI_MIN_SIZE, ICON_PATH


class GovernanceApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME}  v{VERSION}")
        self.root.geometry(GUI_WINDOW_SIZE)
        self.root.minsize(*GUI_MIN_SIZE)
        self._load_icon()
        self._setup_style()
        self._build_ui()

    def _load_icon(self):
        """Carga el icono personalizado generado por tools/generate_icon.py."""
        try:
            self.root.iconbitmap(str(ICON_PATH))
        except Exception:
            pass  # Linux/Mac: iconbitmap no aplica, continuar sin error

    def _setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use(GUI_THEME)
        BG      = "#1e1e2e"
        FG      = "#cdd6f4"
        ACCENT  = "#89b4fa"
        SURFACE = "#313244"
        self.root.configure(bg=BG)
        style.configure(".",             background=BG,      foreground=FG,      font=("Segoe UI", 10))
        style.configure("TNotebook",     background=BG,      borderwidth=0)
        style.configure("TNotebook.Tab", background=SURFACE, foreground=FG,
                        padding=[14, 6], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#1e1e2e")])
        style.configure("TFrame",   background=BG)
        style.configure("TLabel",   background=BG,      foreground=FG)
        style.configure("TButton",  background=SURFACE,  foreground=FG,  padding=[10, 5], relief="flat")
        style.map("TButton",
                  background=[("active", ACCENT)],
                  foreground=[("active", "#1e1e2e")])
        style.configure("TEntry",     fieldbackground=SURFACE, foreground=FG, insertcolor=FG, borderwidth=1)
        style.configure("TScrollbar", background=SURFACE, troughcolor=BG)
        style.configure("Treeview",   background=SURFACE, foreground=FG,
                        fieldbackground=SURFACE, rowheight=24)
        style.configure("Treeview.Heading", background=BG, foreground=ACCENT,
                        font=("Segoe UI", 10, "bold"))
        style.configure("Accent.TButton", background=ACCENT, foreground="#1e1e2e",
                        font=("Segoe UI", 10, "bold"))
        self._colors = {"bg": BG, "fg": FG, "accent": ACCENT, "surface": SURFACE}

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=self._colors["surface"], pady=8)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text=f"  \U0001f6e1\ufe0f  {APP_NAME}",
            font=("Segoe UI", 14, "bold"),
            bg=self._colors["surface"],
            fg=self._colors["accent"]
        ).pack(side=tk.LEFT, padx=12)
        tk.Label(
            header,
            text=f"v{VERSION}",
            font=("Segoe UI", 9),
            bg=self._colors["surface"],
            fg="#6c7086"
        ).pack(side=tk.LEFT, padx=(0, 16))
        tk.Label(
            header,
            text="File Governance Platform",
            font=("Segoe UI", 9, "italic"),
            bg=self._colors["surface"],
            fg="#6c7086"
        ).pack(side=tk.RIGHT, padx=16)

        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        # Tabs
        from gui.tab_scan        import ScanTab
        from gui.tab_migration   import MigrationTab
        from gui.tab_permissions import PermissionsTab
        from gui.tab_analysis    import AnalysisTab
        from gui.tab_reports     import ReportsTab

        tabs = [
            ("  \U0001f50d  Escaneo",    ScanTab),
            ("  \U0001f4c2  Migracion",  MigrationTab),
            ("  \U0001f512  Permisos",   PermissionsTab),
            ("  \U0001f4ca  Analisis",   AnalysisTab),
            ("  \U0001f4c4  Reportes",   ReportsTab),
        ]
        for label, TabClass in tabs:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=label)
            TabClass(frame, self._colors).build()

        # Status bar
        self.status_var = tk.StringVar(value="Listo")
        status_bar = tk.Label(
            self.root, textvariable=self.status_var,
            bd=1, relief=tk.SUNKEN, anchor=tk.W,
            bg=self._colors["surface"], fg="#6c7086",
            font=("Segoe UI", 9), padx=8
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def run(self):
        self.root.mainloop()
