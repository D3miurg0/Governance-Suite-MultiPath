"""
gui/tab_access_control.py
─────────────────────────────────────────────────────────────────────────────
Tab GUI — Gestión de Derechos de Acceso ISO 27001:2022 (5.15 / 5.18)
Sigue el patrón visual de tab_permissions.py / tab_migration.py.
─────────────────────────────────────────────────────────────────────────────
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread

from modules.access_control import AccessControlModule, PERMISSION_LEVELS


class AccessControlTab:
    """
    Pestaña única con cuatro sub-vistas seleccionables por botones de radio:
      • Listar ACEs          (5.15)
      • Acceso Efectivo      (5.15)
      • Asignar / Denegar    (5.15)
      • Revocar / Revisar    (5.18)
    """

    def __init__(self, parent: tk.Widget, colors: dict, core):
        self.parent = parent
        self.c      = colors
        self.core   = core
        self.ac     = AccessControlModule(core)
        self._current_panel: tk.Frame | None = None

    # ──────────────────────────────────────────────────────────────────────
    # Construcción del tab
    # ──────────────────────────────────────────────────────────────────────
    def build(self):
        c = self.c
        root = self.parent

        # ── cabecera ──────────────────────────────────────────────────────
        hdr = tk.Frame(root, bg=c["bg"])
        hdr.pack(fill=tk.X, padx=12, pady=(8, 0))
        tk.Label(
            hdr,
            text="Gestión de Derechos de Acceso  —  ISO/IEC 27001:2022  ·  5.15 / 5.18",
            bg=c["bg"], fg=c.get("accent", "#89dceb"),
            font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT)

        # ── selector de sub-vista ─────────────────────────────────────────
        nav = tk.Frame(root, bg=c["surface"])
        nav.pack(fill=tk.X, padx=12, pady=(6, 0))

        self._view_var = tk.StringVar(value="list")
        views = [
            ("📋 Listar ACEs",       "list"),
            ("🔍 Acceso Efectivo",   "effective"),
            ("✏️  Asignar / Denegar", "assign"),
            ("🗑️  Revocar / Revisar", "revoke"),
        ]
        for label, val in views:
            tk.Radiobutton(
                nav, text=label, variable=self._view_var, value=val,
                bg=c["surface"], fg=c["fg"],
                activebackground=c["surface"],
                selectcolor=c["bg"],
                font=("Segoe UI", 9),
                command=self._switch_view,
            ).pack(side=tk.LEFT, padx=8, pady=4)

        # ── contenedor de paneles dinámicos ───────────────────────────────
        self._panel_container = tk.Frame(root, bg=c["bg"])
        self._panel_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # ── barra de estado ───────────────────────────────────────────────
        status_bar = tk.Frame(root, bg=c["surface"])
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_var = tk.StringVar(value="Listo")
        tk.Label(
            status_bar, textvariable=self._status_var,
            bg=c["surface"], fg=c.get("muted", "#6c7086"),
            font=("Segoe UI", 8), anchor="w"
        ).pack(fill=tk.X, padx=8, pady=2)

        self._switch_view()   # mostrar panel inicial

    # ──────────────────────────────────────────────────────────────────────
    # Router de sub-vistas
    # ──────────────────────────────────────────────────────────────────────
    def _switch_view(self):
        if self._current_panel:
            self._current_panel.destroy()
        view = self._view_var.get()
        builders = {
            "list":      self._build_list_panel,
            "effective": self._build_effective_panel,
            "assign":    self._build_assign_panel,
            "revoke":    self._build_revoke_panel,
        }
        panel = tk.Frame(self._panel_container, bg=self.c["bg"])
        panel.pack(fill=tk.BOTH, expand=True)
        builders[view](panel)
        self._current_panel = panel

    # ──────────────────────────────────────────────────────────────────────
    # Utilidades GUI compartidas
    # ──────────────────────────────────────────────────────────────────────
    def _path_row(self, parent: tk.Frame, label="Ruta:") -> tk.StringVar:
        c = self.c
        row = tk.Frame(parent, bg=c["bg"])
        row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(row, text=label, bg=c["bg"], fg=c["fg"], width=18, anchor="e").pack(side=tk.LEFT)
        var = tk.StringVar()
        tk.Entry(row, textvariable=var, width=55,
                 bg=c["surface"], fg=c["fg"], relief="flat").pack(side=tk.LEFT, padx=4)
        tk.Button(
            row, text="Examinar", bg=c["surface"], fg=c["fg"], relief="flat",
            command=lambda: var.set(filedialog.askdirectory() or var.get())
        ).pack(side=tk.LEFT)
        return var

    def _text_row(self, parent: tk.Frame, label: str) -> tk.StringVar:
        c = self.c
        row = tk.Frame(parent, bg=c["bg"])
        row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(row, text=label, bg=c["bg"], fg=c["fg"], width=18, anchor="e").pack(side=tk.LEFT)
        var = tk.StringVar()
        tk.Entry(row, textvariable=var, width=45,
                 bg=c["surface"], fg=c["fg"], relief="flat").pack(side=tk.LEFT, padx=4)
        return var

    def _results_tree(self, parent: tk.Frame, columns: tuple) -> ttk.Treeview:
        frame = tk.Frame(parent, bg=self.c["bg"])
        frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=160 if col not in ("Ruta", "Cuenta", "SID") else 280)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=hsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        return tree

    def _set_status(self, msg: str):
        self._status_var.set(msg)

    def _action_btn(self, parent, text, command, accent=False):
        c = self.c
        bg = c.get("accent", "#89dceb") if accent else c["surface"]
        fg = "#1e1e2e" if accent else c["fg"]
        return tk.Button(
            parent, text=text, bg=bg, fg=fg,
            font=("Segoe UI", 9, "bold" if accent else "normal"),
            relief="flat", padx=10, command=command
        )

    # ──────────────────────────────────────────────────────────────────────
    # Panel 1 — Listar ACEs  (ISO 5.15)
    # ──────────────────────────────────────────────────────────────────────
    def _build_list_panel(self, panel: tk.Frame):
        c = self.c
        tk.Label(panel, text="ISO 5.15 — Listar ACEs de una ruta",
                 bg=c["bg"], fg=c.get("accent", "#89dceb"),
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        path_var  = self._path_row(panel)
        depth_var = self._text_row(panel, "Profundidad:")
        depth_var.set("2")

        cols = ("Ruta", "Cuenta", "Tipo", "Permisos", "Heredado", "Control ISO")
        tree = self._results_tree(panel, cols)

        btn_frame = tk.Frame(panel, bg=c["bg"])
        btn_frame.pack(fill=tk.X, pady=6)

        def _run():
            path = path_var.get().strip()
            if not path:
                messagebox.showwarning("Atención", "Selecciona una ruta."); return
            for row in tree.get_children():
                tree.delete(row)
            self._set_status("Listando ACEs...")

            def worker():
                try:
                    depth = int(depth_var.get() or "2")
                except ValueError:
                    depth = 2
                from core.utils import Utils
                import os
                long_path = Utils.get_long_unc_path(path)
                results = []
                for root, dirs, _ in os.walk(
                    long_path, onerror=self.core.on_walk_error
                ):
                    try:
                        rel = os.path.relpath(root, long_path)
                        cur = 0 if rel == "." else rel.count(os.sep) + 1
                    except ValueError:
                        cur = 0
                    if depth != -1 and cur > depth:
                        dirs[:] = []; continue
                    results.extend(self.ac.list_access(root))

                def update():
                    for a in results:
                        iso = "5.18 — Sobrante" if a["account"] == a["sid_raw"] else "5.15 — Activo"
                        tree.insert("", tk.END, values=(
                            a["path"], a["account"], a["type"],
                            a["permissions"],
                            "Sí" if a["inherited"] else "No",
                            iso,
                        ))
                    self._set_status(f"{len(results)} ACEs encontrados")
                panel.after(0, update)
            Thread(target=worker, daemon=True).start()

        self._action_btn(btn_frame, "  ▶  Listar ACEs", _run, accent=True).pack(side=tk.LEFT, padx=4)

        def _export():
            path = path_var.get().strip()
            if not path:
                messagebox.showwarning("Atención", "Selecciona una ruta."); return
            try:
                depth = int(depth_var.get() or "2")
            except ValueError:
                depth = 2
            self._set_status("Exportando...")
            Thread(
                target=lambda: (
                    self.ac.export_access_report(path, depth),
                    self._set_status("Reporte exportado")
                ),
                daemon=True
            ).start()

        self._action_btn(btn_frame, "  💾  Exportar CSV", _export).pack(side=tk.LEFT, padx=4)

    # ──────────────────────────────────────────────────────────────────────
    # Panel 2 — Acceso Efectivo  (ISO 5.15)
    # ──────────────────────────────────────────────────────────────────────
    def _build_effective_panel(self, panel: tk.Frame):
        c = self.c
        tk.Label(panel, text="ISO 5.15 — Acceso efectivo de una cuenta",
                 bg=c["bg"], fg=c.get("accent", "#89dceb"),
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        path_var    = self._path_row(panel)
        account_var = self._text_row(panel, "Cuenta:")

        result_frame = tk.Frame(panel, bg=c["surface"], padx=12, pady=10)
        result_frame.pack(fill=tk.X, pady=8)
        lbl_result = tk.Label(
            result_frame, text="—",
            bg=c["surface"], fg=c["fg"],
            font=("Consolas", 10), justify=tk.LEFT, anchor="w"
        )
        lbl_result.pack(fill=tk.X)

        def _run():
            path    = path_var.get().strip()
            account = account_var.get().strip()
            if not path or not account:
                messagebox.showwarning("Atención", "Ruta y cuenta son obligatorios."); return
            self._set_status("Calculando acceso efectivo...")

            def worker():
                r = self.ac.effective_access(path, account)
                text = (
                    f"Cuenta   : {r.get('account', '')}\n"
                    f"Ruta     : {r.get('path', '')}\n"
                    f"Allow    : 0x{r.get('allow_mask', 0):08X}\n"
                    f"Deny     : 0x{r.get('deny_mask',  0):08X}\n"
                    f"Efectivo : {r.get('summary', 'N/A')}"
                )
                panel.after(0, lambda: lbl_result.config(text=text))
                panel.after(0, lambda: self._set_status("Listo"))
            Thread(target=worker, daemon=True).start()

        btn_frame = tk.Frame(panel, bg=c["bg"])
        btn_frame.pack(fill=tk.X, pady=4)
        self._action_btn(btn_frame, "  ▶  Calcular", _run, accent=True).pack(side=tk.LEFT, padx=4)

    # ──────────────────────────────────────────────────────────────────────
    # Panel 3 — Asignar / Denegar  (ISO 5.15)
    # ──────────────────────────────────────────────────────────────────────
    def _build_assign_panel(self, panel: tk.Frame):
        c = self.c
        tk.Label(panel, text="ISO 5.15 — Asignar o Denegar acceso",
                 bg=c["bg"], fg=c.get("accent", "#89dceb"),
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        path_var    = self._path_row(panel)
        account_var = self._text_row(panel, "Cuenta:")

        # Selector de nivel
        lev_row = tk.Frame(panel, bg=c["bg"])
        lev_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(lev_row, text="Nivel de permiso:",
                 bg=c["bg"], fg=c["fg"], width=18, anchor="e").pack(side=tk.LEFT)
        level_var = tk.StringVar(value="Read")
        lev_cb = ttk.Combobox(
            lev_row, textvariable=level_var,
            values=list(PERMISSION_LEVELS.keys()),
            state="readonly", width=20
        )
        lev_cb.pack(side=tk.LEFT, padx=4)

        inherit_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            panel, text="Propagar a subcarpetas y archivos (OI+CI)",
            variable=inherit_var,
            bg=c["bg"], fg=c["fg"], selectcolor=c["surface"],
            activebackground=c["bg"]
        ).pack(anchor="w", padx=24, pady=(0, 8))

        btn_frame = tk.Frame(panel, bg=c["bg"])
        btn_frame.pack(fill=tk.X, pady=4)

        def _confirm_and_run(operation: str):
            path    = path_var.get().strip()
            account = account_var.get().strip()
            level   = level_var.get()
            if not path or not account:
                messagebox.showwarning("Atención", "Ruta y cuenta son obligatorios."); return
            verb = "otorgar" if operation == "grant" else "DENEGAR"
            if not messagebox.askyesno(
                "Confirmar operación",
                f"¿Confirmar {verb} '{level}' a '{account}'\nen la ruta:\n{path}?"
            ):
                return
            self._set_status(f"{verb.capitalize()}ando permiso...")

            def worker():
                if operation == "grant":
                    self.ac.grant_access(path, account, level, inherit_var.get())
                else:
                    self.ac.deny_access(path, account, level)
                panel.after(0, lambda: self._set_status("Operación completada"))
            Thread(target=worker, daemon=True).start()

        self._action_btn(
            btn_frame, "  ✅  Otorgar (Allow)",
            lambda: _confirm_and_run("grant"), accent=True
        ).pack(side=tk.LEFT, padx=4)
        self._action_btn(
            btn_frame, "  🚫  Denegar (Deny)",
            lambda: _confirm_and_run("deny")
        ).pack(side=tk.LEFT, padx=4)

    # ──────────────────────────────────────────────────────────────────────
    # Panel 4 — Revocar / Revisar  (ISO 5.18)
    # ──────────────────────────────────────────────────────────────────────
    def _build_revoke_panel(self, panel: tk.Frame):
        c = self.c
        tk.Label(panel, text="ISO 5.18 — Revocar acceso / Revisar sobrantes",
                 bg=c["bg"], fg=c.get("accent", "#89dceb"),
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        path_var    = self._path_row(panel)
        account_var = self._text_row(panel, "Cuenta a revocar:")
        depth_var   = self._text_row(panel, "Profundidad revisión:")
        depth_var.set("2")

        cols = ("Ruta", "SID", "Tipo", "Permisos", "Heredado", "Control ISO")
        tree = self._results_tree(panel, cols)

        btn_frame = tk.Frame(panel, bg=c["bg"])
        btn_frame.pack(fill=tk.X, pady=6)

        def _revoke():
            path    = path_var.get().strip()
            account = account_var.get().strip()
            if not path or not account:
                messagebox.showwarning("Atención", "Ruta y cuenta son obligatorios."); return
            if not messagebox.askyesno(
                "Confirmar revocación",
                f"Eliminar TODOS los ACEs explícitos de:\n'{account}'\nen: {path}\n\n¿Continuar?"
            ):
                return
            self._set_status("Revocando...")
            Thread(
                target=lambda: (
                    self.ac.revoke_access(path, account),
                    panel.after(0, lambda: self._set_status("Revocación completada"))
                ),
                daemon=True
            ).start()

        def _orphans():
            path = path_var.get().strip()
            if not path:
                messagebox.showwarning("Atención", "Selecciona una ruta."); return
            try:
                depth = int(depth_var.get() or "2")
            except ValueError:
                depth = 2
            for row in tree.get_children():
                tree.delete(row)
            self._set_status("Buscando accesos sobrantes...")

            def worker():
                orphans = self.ac.review_orphan_access(path, depth)
                def update():
                    for o in orphans:
                        tree.insert("", tk.END, values=(
                            o["path"], o["sid"], o["type"],
                            o["permissions"],
                            "Sí" if o["inherited"] else "No",
                            o["iso_control"],
                        ))
                    self._set_status(
                        f"{len(orphans)} acceso(s) sobrante(s) detectado(s)" if orphans
                        else "✅ Sin accesos sobrantes detectados"
                    )
                panel.after(0, update)
            Thread(target=worker, daemon=True).start()

        def _cleanup():
            path = path_var.get().strip()
            if not path:
                messagebox.showwarning("Atención", "Selecciona una ruta."); return
            if not messagebox.askyesno(
                "Confirmar limpieza",
                f"Eliminar ACEs explícitos redundantes con herencia en:\n{path}\n\n¿Continuar?"
            ):
                return
            self._set_status("Limpiando ACEs redundantes...")
            def worker():
                removed = self.ac.revoke_inherited_overrides(path)
                panel.after(0, lambda: self._set_status(
                    f"{removed} ACE(s) redundante(s) eliminado(s)"
                ))
            Thread(target=worker, daemon=True).start()

        self._action_btn(btn_frame, "  ✅  Revocar cuenta", _revoke, accent=True).pack(side=tk.LEFT, padx=4)
        self._action_btn(btn_frame, "  🔍  Revisar sobrantes", _orphans).pack(side=tk.LEFT, padx=4)
        self._action_btn(btn_frame, "  🧹  Limpiar redundantes", _cleanup).pack(side=tk.LEFT, padx=4)
