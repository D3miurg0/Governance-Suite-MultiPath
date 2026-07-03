"""
gui/tab_share_manager.py
─────────────────────────────────────────────────────────────────────────────
Pestaña GUI de gestión de shares SMB — soporte MULTI-SERVIDOR.

Flujo de uso:
  1. Escribir hostname / IP en el campo "Servidor" → [Conectar]
  2. La lista se puebla con los shares del servidor escaneado
  3. Hacer clic en un share para seleccionarlo
  4. Poner la nueva ruta y el directorio de backup
  5. [Migrar], [Verificar] o [Recrear]
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Shares puramente de sistema que nunca son operables
_SKIP_ALWAYS = {"IPC$"}


class ShareManagerTab:
    """Pestaña de gestión de shares SMB multi-servidor."""

    def __init__(self, parent, colors: dict, core=None):
        self.parent = parent
        self.c      = colors
        self.core   = core
        self._mgr   = None
        self._shares: list[dict] = []

    # ── Construcción de la UI ─────────────────────────────────────────────

    def build(self):
        bg = self.c["bg"]
        fg = self.c["fg"]
        ac = self.c["accent"]
        sf = self.c["surface"]

        # ── Fila superior: servidor + opciones ────────────────────────────
        top = tk.Frame(self.parent, bg=bg)
        top.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(top, text="Servidor:", bg=bg, fg=fg,
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))

        self.srv_var = tk.StringVar(value="localhost")
        srv_entry = tk.Entry(top, textvariable=self.srv_var, width=24,
                             bg=sf, fg=fg, insertbackground=fg,
                             relief="flat", font=("Segoe UI", 10))
        srv_entry.pack(side="left", padx=(0, 6))
        srv_entry.bind("<Return>", lambda _e: self._connect())

        tk.Button(
            top, text="  Conectar  ",
            bg=ac, fg="#1e1e2e", activebackground="#74c7ec",
            relief="flat", font=("Segoe UI", 9, "bold"),
            command=self._connect
        ).pack(side="left", padx=(0, 12))

        # Checkbox: ocultar shares admin (C$, ADMIN$...)
        self.hide_admin_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            top, text="Ocultar admin$",
            variable=self.hide_admin_var,
            bg=bg, fg=fg, selectcolor=sf,
            activebackground=bg, activeforeground=ac,
            font=("Segoe UI", 9),
            command=self._apply_filter
        ).pack(side="left", padx=(0, 12))

        self.srv_status = tk.Label(top, text="Sin conectar",
                                   bg=bg, fg="#6c7086",
                                   font=("Segoe UI", 9, "italic"))
        self.srv_status.pack(side="left")

        # ── Separador ─────────────────────────────────────────────────────
        ttk.Separator(self.parent, orient="horizontal").pack(fill="x", padx=10, pady=2)

        # ── Panel principal ────────────────────────────────────────────────
        main = tk.Frame(self.parent, bg=bg)
        main.pack(fill="both", expand=True, padx=10, pady=6)
        main.columnconfigure(0, weight=2)
        main.columnconfigure(1, weight=3)
        main.rowconfigure(0, weight=1)

        # ── Lista de shares ───────────────────────────────────────────────
        left = tk.LabelFrame(
            main, text=" Shares encontrados ",
            bg=bg, fg=ac, font=("Segoe UI", 9, "bold"),
            bd=1, relief="groove"
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        cols = ("name", "path", "comment")
        self.tree = ttk.Treeview(
            left, columns=cols, show="headings", selectmode="browse"
        )
        for col, hdr, w in [
            ("name",    "Share",       120),
            ("path",    "Ruta actual", 200),
            ("comment", "Comentario",  120),
        ]:
            self.tree.heading(col, text=hdr)
            self.tree.column(col, width=w, minwidth=60)
        self.tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        tk.Button(
            left, text="↻  Refrescar lista",
            bg=sf, fg=fg, activebackground=ac, activeforeground="#1e1e2e",
            relief="flat", font=("Segoe UI", 9),
            command=self._connect
        ).pack(fill="x", pady=(4, 2), padx=4)

        # ── Formulario derecho ─────────────────────────────────────────────
        right = tk.LabelFrame(
            main, text=" Operación ",
            bg=bg, fg=ac, font=("Segoe UI", 9, "bold"),
            bd=1, relief="groove"
        )
        right.grid(row=0, column=1, sticky="nsew")

        def lbl(parent, text):
            return tk.Label(parent, text=text, bg=bg, fg=fg,
                            font=("Segoe UI", 9, "bold"), anchor="w")

        def entry(parent, var, **kw):
            return tk.Entry(parent, textvariable=var,
                            bg=sf, fg=fg, insertbackground=fg,
                            relief="flat", font=("Segoe UI", 10), **kw)

        lbl(right, "Share seleccionado:").grid(row=0, column=0,
                                               sticky="w", padx=10, pady=(10, 2))
        self.sel_var = tk.StringVar(value="— ninguno —")
        tk.Label(right, textvariable=self.sel_var,
                 bg=sf, fg=ac, font=("Segoe UI", 10, "bold"),
                 anchor="w", padx=6, pady=3, relief="flat"
                 ).grid(row=1, column=0, sticky="ew", padx=10)

        lbl(right, "Ruta actual:").grid(row=2, column=0,
                                        sticky="w", padx=10, pady=(8, 2))
        self.cur_path_var = tk.StringVar(value="")
        tk.Label(right, textvariable=self.cur_path_var,
                 bg=sf, fg="#a6e3a1", font=("Segoe UI", 9),
                 anchor="w", padx=6, pady=2, relief="flat"
                 ).grid(row=3, column=0, sticky="ew", padx=10)

        lbl(right, "Nueva ruta:").grid(row=4, column=0,
                                       sticky="w", padx=10, pady=(8, 2))
        new_row = tk.Frame(right, bg=bg)
        new_row.grid(row=5, column=0, sticky="ew", padx=10)
        new_row.columnconfigure(0, weight=1)
        self.new_path_var = tk.StringVar()
        entry(new_row, self.new_path_var).grid(row=0, column=0, sticky="ew")
        tk.Button(new_row, text="📁", bg=sf, fg=fg, relief="flat",
                  command=self._browse_new).grid(row=0, column=1, padx=(4, 0))

        lbl(right, "Carpeta de backup:").grid(row=6, column=0,
                                              sticky="w", padx=10, pady=(8, 2))
        bk_row = tk.Frame(right, bg=bg)
        bk_row.grid(row=7, column=0, sticky="ew", padx=10)
        bk_row.columnconfigure(0, weight=1)
        self.backup_var = tk.StringVar(value="C:\\Temp\\ShareBackup")
        entry(bk_row, self.backup_var).grid(row=0, column=0, sticky="ew")
        tk.Button(bk_row, text="📁", bg=sf, fg=fg, relief="flat",
                  command=self._browse_backup).grid(row=0, column=1, padx=(4, 0))

        right.columnconfigure(0, weight=1)

        btn_frame = tk.Frame(right, bg=bg)
        btn_frame.grid(row=8, column=0, pady=14, padx=10, sticky="ew")
        btn_frame.columnconfigure((0, 1, 2), weight=1)

        for i, (txt, bg_c, fg_c, cmd) in enumerate([
            ("✅  Migrar",    "#a6e3a1", "#1e1e2e", self._migrate),
            ("🔍  Verificar", "#89b4fa", "#1e1e2e", self._verify),
            ("⚠  Recrear",   "#f38ba8", "#1e1e2e", self._recreate),
        ]):
            tk.Button(
                btn_frame, text=txt,
                bg=bg_c, fg=fg_c, activebackground="#cdd6f4",
                relief="flat", font=("Segoe UI", 9, "bold"),
                command=cmd
            ).grid(row=0, column=i, padx=4, sticky="ew")

        # ── Log ───────────────────────────────────────────────────────────
        log_frame = tk.LabelFrame(
            self.parent, text=" Log de operaciones ",
            bg=bg, fg=ac, font=("Segoe UI", 9, "bold"),
            bd=1, relief="groove"
        )
        log_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.log_box = tk.Text(
            log_frame, height=8,
            bg="#11111b", fg=fg,
            font=("Consolas", 9), relief="flat",
            state="disabled", wrap="word"
        )
        self.log_box.pack(fill="x", padx=4, pady=4)
        self.log_box.tag_configure("ok",   foreground="#a6e3a1")
        self.log_box.tag_configure("err",  foreground="#f38ba8")
        self.log_box.tag_configure("warn", foreground="#f9e2af")
        self.log_box.tag_configure("info", foreground="#89b4fa")
        self.log_box.tag_configure("dim",  foreground="#6c7086")

    # ── Conexión / escaneo ────────────────────────────────────────────────

    def _connect(self):
        server = self.srv_var.get().strip()
        self.srv_status.config(text="Conectando…", fg="#f9e2af")
        self._log(f"Conectando a '{server or 'localhost'}'…", "info")
        threading.Thread(target=self._scan_thread,
                         args=(server,), daemon=True).start()

    def _scan_thread(self, server: str):
        try:
            from modules.share_manager import ShareManagerModule
            mgr = ShareManagerModule(self.core, server=server)

            # Traer TODOS los shares (sin filtro) para diagnóstico
            all_shares = mgr.list_shares(skip_admin=False)

            # Log de diagnóstico: qué devolvió la API exactamente
            def _diag():
                self._log(
                    f"API devolvió {len(all_shares)} share(s) en total:", "dim"
                )
                for s in all_shares:
                    self._log(
                        f"   · {s['name']:<20}  {s['path']}", "dim"
                    )

            self.parent.after(0, _diag)

            # Filtrar solo IPC$ (no operable); el resto se muestra siempre
            visible = [s for s in all_shares if s["name"] not in _SKIP_ALWAYS]

            self._mgr = mgr
            # Guardar todos para operaciones internas
            self._all_shares = all_shares
            self.parent.after(0, lambda: self._populate_tree(visible, server))

        except Exception as exc:
            msg = str(exc)
            self.parent.after(0, lambda: (
                self._log(f"Error al conectar: {msg}", "err"),
                self.srv_status.config(text=f"Error: {msg}", fg="#f38ba8")
            ))

    def _populate_tree(self, shares: list[dict], server: str):
        self._shares = shares
        self.tree.delete(*self.tree.get_children())
        for s in shares:
            self.tree.insert("", "end",
                             iid=s["name"],
                             values=(s["name"], s["path"], s.get("comment", "")))
        label = server or "localhost"
        count = len(shares)
        self.srv_status.config(
            text=f"✓  {label}  —  {count} share(s)",
            fg="#a6e3a1"
        )
        if count == 0:
            self._log(
                "⚠ 0 shares visibles. Revisa el log anterior para ver "
                "qué devolvió la API. Posibles causas:\n"
                "   1) Sin permisos de admin en el servidor remoto\n"
                "   2) Firewall bloqueando puerto 445\n"
                "   3) El servidor sólo tiene shares admin (C$, ADMIN$)",
                "warn"
            )
        else:
            self._log(
                f"✓ Servidor '{label}': {count} share(s) mostrado(s).", "ok"
            )

    # ── Filtro dinámico (checkbox) ─────────────────────────────────────────

    def _apply_filter(self):
        """Re-aplica el filtro admin$ sobre los shares ya cargados."""
        if not self._shares and not getattr(self, "_all_shares", None):
            return
        source = getattr(self, "_all_shares", self._shares)
        if self.hide_admin_var.get():
            visible = [s for s in source
                       if s["name"] not in _SKIP_ALWAYS
                       and not s["name"].endswith("$")]
        else:
            visible = [s for s in source if s["name"] not in _SKIP_ALWAYS]
        self._shares = visible
        self.tree.delete(*self.tree.get_children())
        for s in visible:
            self.tree.insert("", "end", iid=s["name"],
                             values=(s["name"], s["path"], s.get("comment", "")))

    # ── Selección en el árbol ─────────────────────────────────────────────

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        name = sel[0]
        share = next((s for s in self._shares if s["name"] == name), None)
        if not share:
            return
        self.sel_var.set(name)
        self.cur_path_var.set(share.get("path", ""))
        if not self.new_path_var.get():
            self.new_path_var.set(share.get("path", ""))

    # ── Navegación de carpetas ─────────────────────────────────────────────

    def _browse_new(self):
        path = filedialog.askdirectory(title="Seleccionar nueva ruta del share")
        if path:
            self.new_path_var.set(path.replace("/", "\\"))

    def _browse_backup(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta de backup")
        if path:
            self.backup_var.set(path.replace("/", "\\"))

    # ── Log helpers ───────────────────────────────────────────────────────

    def _log(self, msg: str, tag: str = "info"):
        self.log_box.config(state="normal")
        self.log_box.insert("end", f"► {msg}\n", tag)
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    # ── Acciones ──────────────────────────────────────────────────────────

    def _validate(self) -> tuple[str, str, str] | None:
        if not self._mgr:
            messagebox.showwarning("Sin conexión", "Conecta primero a un servidor.")
            return None
        name = self.sel_var.get().strip()
        if not name or name.startswith("—"):
            messagebox.showwarning("Sin share seleccionado",
                                   "Selecciona un share de la lista.")
            return None
        new_path = self.new_path_var.get().strip()
        if not new_path:
            messagebox.showwarning("Sin ruta", "Indica la nueva ruta del share.")
            return None
        backup = self.backup_var.get().strip() or "C:\\Temp\\ShareBackup"
        return name, new_path, backup

    def _run_in_thread(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def _migrate(self):
        v = self._validate()
        if not v:
            return
        name, new_path, backup = v

        def _task():
            self.parent.after(0, lambda: self._log(
                f"Iniciando migración: '{name}' → {new_path}", "info"))
            ok = self._mgr.migrate_share(name, new_path, backup)
            tag = "ok" if ok else "err"
            msg = (f"✅  Share '{name}' migrado correctamente."
                   if ok else f"❌  La migración de '{name}' falló.")
            self.parent.after(0, lambda: self._log(msg, tag))
            if ok:
                self.parent.after(0, lambda: self._refresh_item(name, new_path))

        self._run_in_thread(_task)

    def _verify(self):
        v = self._validate()
        if not v:
            return
        name, new_path, _ = v

        def _task():
            ok = self._mgr.verify_share(name, new_path)
            tag = "ok" if ok else "warn"
            msg = (f"✅  Verificación OK: '{name}' apunta a {new_path}."
                   if ok else
                   f"⚠  '{name}' NO apunta a {new_path}. Revisa la ruta.")
            self.parent.after(0, lambda: self._log(msg, tag))

        self._run_in_thread(_task)

    def _recreate(self):
        v = self._validate()
        if not v:
            return
        name, new_path, backup = v
        if not messagebox.askyesno(
            "Confirmar recreación",
            f"⚠️  Se eliminará y recreará el share '{name}'.\n"
            "Los permisos SMB se resetean (Everyone/Read).\n\n"
            "¿Continuar?"
        ):
            return

        def _task():
            self.parent.after(0, lambda: self._log(
                f"Recreando share '{name}'…", "warn"))
            self._mgr.export_shares(backup)
            ok = self._mgr.recreate_share(name, new_path)
            tag = "ok" if ok else "err"
            msg = (f"✅  Share '{name}' recreado en {new_path}. Revisar permisos SMB."
                   if ok else f"❌  No se pudo recrear '{name}'.")
            self.parent.after(0, lambda: self._log(msg, tag))
            if ok:
                self.parent.after(0, lambda: self._refresh_item(name, new_path))

        self._run_in_thread(_task)

    def _refresh_item(self, name: str, new_path: str):
        try:
            self.tree.set(name, "path", new_path)
        except Exception:
            pass
        for s in self._shares:
            if s["name"] == name:
                s["path"] = new_path
        self.cur_path_var.set(new_path)
