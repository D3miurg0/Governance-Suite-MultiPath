"""
gui/tab_share_manager.py
─────────────────────────────────────────────────────────────────────────────
Pestaña GUI para gestión / migración de shares SMB.

Cuando el campo Servidor está vacío o contiene el hostname local,
el módulo usa None internamente (API local sin red).
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import socket
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Optional

from modules.share_manager import ShareManagerModule


class ShareManagerTab:
    """Pestaña de gestión y migración de shares SMB."""

    def __init__(self, parent: ttk.Notebook, core=None):
        self.core   = core
        self.frame  = ttk.Frame(parent)
        self._mgr: Optional[ShareManagerModule] = None
        self._shares: list[dict] = []
        self._build_ui()

    # ── UI ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        f = self.frame
        f.columnconfigure(0, weight=3)
        f.columnconfigure(1, weight=2)
        f.rowconfigure(1, weight=1)

        # ── Barra superior: servidor + conectar ─────────────────────────
        top = ttk.Frame(f)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))

        ttk.Label(top, text="Servidor:").pack(side="left")
        self._sv_server = tk.StringVar(value=socket.gethostname())
        self._entry_server = ttk.Entry(top, textvariable=self._sv_server, width=28)
        self._entry_server.pack(side="left", padx=(4, 8))

        ttk.Button(top, text="Conectar", command=self._on_connect).pack(side="left")

        self._sv_status = tk.StringVar(value="")
        ttk.Label(top, textvariable=self._sv_status, foreground="green").pack(side="left", padx=8)

        self._var_hide_admin = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            top, text="Ocultar admin$",
            variable=self._var_hide_admin,
            command=self._refresh_tree
        ).pack(side="left", padx=8)

        # ── Lista de shares ──────────────────────────────────────────
        lf = ttk.LabelFrame(f, text="Shares encontrados")
        lf.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=4)
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)

        cols = ("Share", "Ruta actual", "Comentario")
        self._tree = ttk.Treeview(lf, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self._tree.heading(c, text=c)
        self._tree.column("Share",       width=140, minwidth=80)
        self._tree.column("Ruta actual", width=320, minwidth=120)
        self._tree.column("Comentario",  width=160, minwidth=80)
        self._tree.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(lf, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=1, sticky="ns")

        ttk.Button(
            lf, text="↻ Refrescar lista", command=self._on_connect
        ).grid(row=1, column=0, pady=4)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # ── Panel de operación ─────────────────────────────────────────
        op = ttk.LabelFrame(f, text="Operación")
        op.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=4)
        op.columnconfigure(0, weight=1)

        ttk.Label(op, text="Share seleccionado:").grid(row=0, column=0, sticky="w", padx=8, pady=(8,0))
        self._sv_selected = tk.StringVar(value="— ninguno —")
        ttk.Label(op, textvariable=self._sv_selected, font=("Segoe UI", 10, "bold")).grid(
            row=1, column=0, sticky="ew", padx=8)

        ttk.Label(op, text="Ruta actual:").grid(row=2, column=0, sticky="w", padx=8, pady=(8,0))
        self._sv_cur_path = tk.StringVar()
        ttk.Entry(op, textvariable=self._sv_cur_path, state="readonly").grid(
            row=3, column=0, sticky="ew", padx=8)

        ttk.Label(op, text="Nueva ruta:").grid(row=4, column=0, sticky="w", padx=8, pady=(8,0))
        ruta_f = ttk.Frame(op)
        ruta_f.grid(row=5, column=0, sticky="ew", padx=8)
        ruta_f.columnconfigure(0, weight=1)
        self._sv_new_path = tk.StringVar()
        ttk.Entry(ruta_f, textvariable=self._sv_new_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(ruta_f, text="📂", width=3,
                   command=lambda: self._sv_new_path.set(
                       filedialog.askdirectory() or self._sv_new_path.get()
                   )).grid(row=0, column=1)

        ttk.Label(op, text="Carpeta de backup:").grid(row=6, column=0, sticky="w", padx=8, pady=(8,0))
        bk_f = ttk.Frame(op)
        bk_f.grid(row=7, column=0, sticky="ew", padx=8)
        bk_f.columnconfigure(0, weight=1)
        self._sv_backup = tk.StringVar(value=r"C:\Temp\ShareBackup")
        ttk.Entry(bk_f, textvariable=self._sv_backup).grid(row=0, column=0, sticky="ew")
        ttk.Button(bk_f, text="📂", width=3,
                   command=lambda: self._sv_backup.set(
                       filedialog.askdirectory() or self._sv_backup.get()
                   )).grid(row=0, column=1)

        btn_f = ttk.Frame(op)
        btn_f.grid(row=8, column=0, pady=12, padx=8)
        ttk.Button(btn_f, text="☑ Migrar",    command=self._on_migrate).pack(side="left", padx=4)
        ttk.Button(btn_f, text="● Verificar", command=self._on_verify).pack(side="left", padx=4)
        ttk.Button(btn_f, text="⚠ Recrear",   command=self._on_recreate).pack(side="left", padx=4)

        # ── Log ─────────────────────────────────────────────────────────────
        lf2 = ttk.LabelFrame(f, text="Log de operaciones")
        lf2.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0,8))
        lf2.columnconfigure(0, weight=1)

        self._log_text = tk.Text(lf2, height=7, state="disabled",
                                 bg="#1e1e1e", fg="#cccccc",
                                 font=("Consolas", 9))
        self._log_text.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        self._log_text.tag_config("ok",   foreground="#4ec94e")
        self._log_text.tag_config("err",  foreground="#f44747")
        self._log_text.tag_config("warn", foreground="#ce9178")
        self._log_text.tag_config("info", foreground="#9cdcfe")

    # ── Eventos ──────────────────────────────────────────────────────────

    def _log(self, msg: str, tag: str = "info"):
        self._log_text.configure(state="normal")
        self._log_text.insert("end", f"\u25ba {msg}\n", tag)
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _get_server_arg(self) -> Optional[str]:
        """
        Si el campo servidor está vacío o es el hostname local devuelve None
        (el módulo llama a la API local directamente).
        Cualquier otro valor se pasa tal cual.
        """
        val = self._sv_server.get().strip()
        local_names = {socket.gethostname().lower(), "localhost", "127.0.0.1", ""}
        return None if val.lower() in local_names else val

    def _on_connect(self):
        srv_arg = self._get_server_arg()
        self._mgr = ShareManagerModule(self.core, server=srv_arg or "")
        label = srv_arg or "localhost (local)"
        self._log(f"Conectando a '{label}'…", "info")
        threading.Thread(target=self._do_load, daemon=True).start()

    def _do_load(self):
        if not self._mgr:
            return
        skip = self._var_hide_admin.get()
        shares = self._mgr.list_shares(skip_admin=skip)
        self._shares = shares
        self.frame.after(0, self._refresh_tree)
        srv = self._mgr.server_label
        if shares:
            self._log(f"✓ {srv}: {len(shares)} share(s) encontrado(s).", "ok")
        else:
            self._log(f"⚠ {srv}: 0 shares — verifica permisos o conectividad.", "warn")

    def _refresh_tree(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        skip = self._var_hide_admin.get()
        for s in self._shares:
            if skip and s["name"].endswith("$"):
                continue
            self._tree.insert("", "end", values=(s["name"], s["path"], s["comment"]))

    def _on_select(self, _event=None):
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0], "values")
        self._sv_selected.set(vals[0])
        self._sv_cur_path.set(vals[1])

    def _selected_share(self) -> Optional[str]:
        name = self._sv_selected.get()
        return None if name == "— ninguno —" else name

    # ── Acciones ─────────────────────────────────────────────────────────

    def _on_migrate(self):
        name = self._selected_share()
        if not name:
            self._log("Selecciona un share primero.", "warn")
            return
        new_path = self._sv_new_path.get().strip()
        if not new_path:
            self._log("Indica la nueva ruta.", "warn")
            return
        backup = self._sv_backup.get().strip() or "."
        self._log(f"Migrando '{name}' → {new_path}…", "info")

        def _run():
            ok = self._mgr.migrate_share(name, new_path, backup)
            msg = (f"✅ Share '{name}' migrado correctamente."
                   if ok else f"❌ Fallo al migrar '{name}'.")
            self.frame.after(0, lambda: self._log(msg, "ok" if ok else "err"))
            if ok:
                self.frame.after(0, self._on_connect)
        threading.Thread(target=_run, daemon=True).start()

    def _on_verify(self):
        name = self._selected_share()
        if not name:
            self._log("Selecciona un share primero.", "warn")
            return
        new_path = self._sv_new_path.get().strip()
        if not new_path:
            self._log("Indica la ruta esperada en el campo 'Nueva ruta'.", "warn")
            return
        ok = self._mgr.verify_share(name, new_path)
        msg = (f"✅ '{name}' apunta correctamente a {new_path}."
               if ok else f"❌ '{name}' NO apunta a {new_path}.")
        self._log(msg, "ok" if ok else "err")

    def _on_recreate(self):
        name = self._selected_share()
        if not name:
            self._log("Selecciona un share primero.", "warn")
            return
        new_path = self._sv_new_path.get().strip()
        if not new_path:
            self._log("Indica la nueva ruta.", "warn")
            return
        from tkinter import messagebox
        if not messagebox.askyesno(
            "Recrear share",
            f"Esto eliminará y recreará '{name}'.\n"
            "Los permisos SMB se resetearán.\n\n¿Continuar?"
        ):
            return
        ok = self._mgr.recreate_share(name, new_path)
        msg = (f"✅ '{name}' recreado en {new_path}."
               if ok else f"❌ Fallo al recrear '{name}'.")
        self._log(msg, "ok" if ok else "err")
        if ok:
            self._on_connect()
