"""
gui/tab_share_manager.py
─────────────────────────────────────────────────────────────────────────────
Pestaña GUI para gestión / migración de shares SMB.
Firma compatible con el resto de tabs de app.py:
  __init__(self, parent, colors, core=None)
  build()

Cambios:
  issue #1 — Detección de sesiones SMB activas antes de Migrar / Recrear.
  issue #2 — Validación visual en tiempo real del campo Nueva ruta (✅/❌/⚠).
             Botón Migrar deshabilitado cuando la ruta no es válida.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
import socket
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from modules.share_manager import ShareManagerModule


class ShareManagerTab:
    """Pestaña de gestión y migración de shares SMB."""

    def __init__(self, parent: ttk.Frame, colors: dict, core=None):
        self.parent = parent
        self.colors = colors
        self.core   = core
        self._mgr: Optional[ShareManagerModule] = None
        self._shares: list[dict] = []
        # Referencia al botón Migrar para habilitar/deshabilitar (issue #2)
        self._btn_migrar: Optional[ttk.Button] = None

    def build(self):
        """Construye la UI dentro de self.parent (llamado desde app.py)."""
        self._build_ui(self.parent)

    # ── UI ───────────────────────────────────────────────────────────────

    def _build_ui(self, f: ttk.Frame):
        f.columnconfigure(0, weight=3)
        f.columnconfigure(1, weight=2)
        f.rowconfigure(1, weight=1)

        # ── Barra superior ─────────────────────────────────────────
        top = ttk.Frame(f)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))

        ttk.Label(top, text="Servidor:").pack(side="left")
        self._sv_server = tk.StringVar(value=socket.gethostname())
        ttk.Entry(top, textvariable=self._sv_server, width=28).pack(side="left", padx=(4, 8))
        ttk.Button(top, text="Conectar", command=self._on_connect).pack(side="left")

        self._sv_status = tk.StringVar()
        ttk.Label(top, textvariable=self._sv_status, foreground="green").pack(side="left", padx=8)

        self._var_hide_admin = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            top, text="Ocultar admin$",
            variable=self._var_hide_admin,
            command=self._refresh_tree
        ).pack(side="left", padx=8)

        # ── Lista de shares ─────────────────────────────────────────
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
        ttk.Button(lf, text="↻ Refrescar lista", command=self._on_connect).grid(row=1, column=0, pady=4)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # ── Panel de operación ────────────────────────────────────────
        op = ttk.LabelFrame(f, text="Operación")
        op.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=4)
        op.columnconfigure(0, weight=1)

        ttk.Label(op, text="Share seleccionado:").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 0))
        self._sv_selected = tk.StringVar(value="— ninguno —")
        ttk.Label(op, textvariable=self._sv_selected,
                  font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="ew", padx=8)

        ttk.Label(op, text="Ruta actual:").grid(row=2, column=0, sticky="w", padx=8, pady=(8, 0))
        self._sv_cur_path = tk.StringVar()
        ttk.Entry(op, textvariable=self._sv_cur_path, state="readonly").grid(
            row=3, column=0, sticky="ew", padx=8)

        ttk.Label(op, text="Nueva ruta:").grid(row=4, column=0, sticky="w", padx=8, pady=(8, 0))
        ruta_f = ttk.Frame(op)
        ruta_f.grid(row=5, column=0, sticky="ew", padx=8)
        ruta_f.columnconfigure(0, weight=1)
        self._sv_new_path = tk.StringVar()
        # Rastrear cambios en el campo para validación en tiempo real (issue #2)
        self._sv_new_path.trace_add("write", self._on_new_path_change)
        ttk.Entry(ruta_f, textvariable=self._sv_new_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(ruta_f, text="📂", width=3,
                   command=lambda: self._sv_new_path.set(
                       filedialog.askdirectory() or self._sv_new_path.get()
                   )).grid(row=0, column=1)

        # ── Indicador de validación de ruta (issue #2) ────────────────
        self._sv_path_status = tk.StringVar(value="")
        self._lbl_path_status = ttk.Label(
            op, textvariable=self._sv_path_status,
            font=("Segoe UI", 9)
        )
        self._lbl_path_status.grid(row=6, column=0, sticky="w", padx=10, pady=(2, 0))

        ttk.Label(op, text="Carpeta de backup:").grid(row=7, column=0, sticky="w", padx=8, pady=(8, 0))
        bk_f = ttk.Frame(op)
        bk_f.grid(row=8, column=0, sticky="ew", padx=8)
        bk_f.columnconfigure(0, weight=1)
        self._sv_backup = tk.StringVar(value=r"C:\Temp\ShareBackup")
        ttk.Entry(bk_f, textvariable=self._sv_backup).grid(row=0, column=0, sticky="ew")
        ttk.Button(bk_f, text="📂", width=3,
                   command=lambda: self._sv_backup.set(
                       filedialog.askdirectory() or self._sv_backup.get()
                   )).grid(row=0, column=1)

        btn_f = ttk.Frame(op)
        btn_f.grid(row=9, column=0, pady=12, padx=8)

        # Botón Migrar — se guarda la referencia para poder deshabilitarlo (issue #2)
        self._btn_migrar = ttk.Button(btn_f, text="☑ Migrar", command=self._on_migrate, state="disabled")
        self._btn_migrar.pack(side="left", padx=4)

        ttk.Button(btn_f, text="● Verificar", command=self._on_verify).pack(side="left", padx=4)
        ttk.Button(btn_f, text="⚠ Recrear",   command=self._on_recreate).pack(side="left", padx=4)

        # ── Log ─────────────────────────────────────────────────────────────
        lf2 = ttk.LabelFrame(f, text="Log de operaciones")
        lf2.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        lf2.columnconfigure(0, weight=1)

        self._log_text = tk.Text(
            lf2, height=7, state="disabled",
            bg="#1e1e1e", fg="#cccccc",
            font=("Consolas", 9)
        )
        self._log_text.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        self._log_text.tag_config("ok",   foreground="#4ec94e")
        self._log_text.tag_config("err",  foreground="#f44747")
        self._log_text.tag_config("warn", foreground="#ce9178")
        self._log_text.tag_config("info", foreground="#9cdcfe")

        # Auto-conectar al abrir la pestaña
        self.parent.after(200, self._on_connect)

    # ── Validación de ruta en tiempo real (issue #2) ──────────────────────

    def _on_new_path_change(self, *_args):
        """
        Callback ejecutado cada vez que el campo 'Nueva ruta' cambia.
        Actualiza el indicador visual y habilita/deshabilita el botón Migrar.
        """
        path = self._sv_new_path.get().strip()

        if not path:
            # Campo vacío — sin indicador, botón deshabilitado
            self._sv_path_status.set("")
            self._lbl_path_status.configure(foreground="gray")
            if self._btn_migrar:
                self._btn_migrar.configure(state="disabled")
            return

        # Detectar si es ruta UNC (\\servidor\recurso) — no verificable localmente
        is_unc = path.startswith("\\\\")

        if is_unc:
            self._sv_path_status.set("⚠  Ruta UNC — verificar manualmente")
            self._lbl_path_status.configure(foreground="#ce9178")
            # Habilitamos Migrar ya que no podemos verificar remotamente
            if self._btn_migrar:
                self._btn_migrar.configure(state="normal")
        elif os.path.isdir(path):
            self._sv_path_status.set("✅  Ruta válida")
            self._lbl_path_status.configure(foreground="#4ec94e")
            if self._btn_migrar:
                self._btn_migrar.configure(state="normal")
        else:
            self._sv_path_status.set("❌  Ruta no encontrada")
            self._lbl_path_status.configure(foreground="#f44747")
            if self._btn_migrar:
                self._btn_migrar.configure(state="disabled")

    # ── Verificación de sesiones activas (issue #1) ───────────────────────

    def _check_sessions_before_op(self, share_name: str, op_label: str) -> bool:
        """
        Consulta sesiones SMB activas. Si hay usuarios conectados muestra
        un diálogo de advertencia con la lista.

        Retorna True si se debe continuar con la operación, False si el
        usuario eligió cancelar.
        """
        if not self._mgr:
            return True
        try:
            sessions = self._mgr.get_active_sessions(share_name)
        except Exception as exc:
            self._log(f"⚠ No se pudo verificar sesiones activas: {exc}", "warn")
            return True  # No bloqueamos si la consulta falla

        if not sessions:
            return True  # Sin sesiones activas — continuar directamente

        # Construir mensaje con detalle de usuarios conectados
        lines = []
        for s in sessions[:10]:  # Máximo 10 en el diálogo para no saturarlo
            idle_min = s["idle_time_sec"] // 60
            lines.append(
                f"  • {s['user']}@{s['client']}  "
                f"({s['open_files']} archivo(s) abierto(s), inactivo {idle_min} min)"
            )
        if len(sessions) > 10:
            lines.append(f"  ... y {len(sessions) - 10} sesión(es) más.")

        users_detail = "\n".join(lines)
        msg = (
            f"⚠  Hay {len(sessions)} sesión(es) SMB activa(s) en el servidor:\n\n"
            f"{users_detail}\n\n"
            f"Continuar con '{op_label}' puede interrumpir el acceso de estos usuarios.\n"
            f"¿Deseas continuar de todas formas?"
        )
        self._log(
            f"⚠ {len(sessions)} sesión(es) activa(s) detectada(s) antes de '{op_label}'.",
            "warn"
        )
        return messagebox.askyesno(
            f"Sesiones activas — {op_label}",
            msg,
            icon="warning"
        )

    # ── Lógica ────────────────────────────────────────────────────────────

    def _log(self, msg: str, tag: str = "info"):
        self._log_text.configure(state="normal")
        self._log_text.insert("end", f"► {msg}\n", tag)
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _get_server_arg(self) -> Optional[str]:
        """None = local (API directa sin red). String = servidor remoto."""
        val = self._sv_server.get().strip()
        local_names = {socket.gethostname().lower(), "localhost", "127.0.0.1", ""}
        return None if val.lower() in local_names else val

    def _on_connect(self):
        srv_arg = self._get_server_arg()
        self._mgr = ShareManagerModule(self.core, server=srv_arg or "")
        label = srv_arg or socket.gethostname() + " (local)"
        self._log(f"Conectando a '{label}'…", "info")
        self._sv_status.set(f"⏳ {label}…")
        threading.Thread(target=self._do_load, daemon=True).start()

    def _do_load(self):
        """Corre en hilo daemon — cualquier excepción se muestra en el log GUI."""
        if not self._mgr:
            return
        try:
            self._shares = self._mgr.list_shares(skip_admin=False)
        except Exception as exc:
            self.parent.after(0, lambda: self._log(
                f"❌ Error inesperado cargando shares: {exc}", "err"))
            self._shares = []

        self.parent.after(0, self._refresh_tree)
        srv     = self._mgr.server_label
        visible = len([s for s in self._shares if s["name"] != "IPC$"])
        if visible:
            self._sv_status.set(f"✓ {srv} — {visible} share(s)")
            self.parent.after(0, lambda: self._log(
                f"✓ {srv}: {visible} share(s) encontrado(s).", "ok"))
        else:
            self._sv_status.set(f"⚠ {srv} — 0 shares")
            self.parent.after(0, lambda: self._log(
                f"⚠ {srv}: 0 shares. Verifica permisos.", "warn"))

    def _refresh_tree(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        skip = self._var_hide_admin.get()
        for s in self._shares:
            if s["name"] == "IPC$":
                continue
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

        # ── Verificar sesiones activas antes de migrar (issue #1) ──
        if not self._check_sessions_before_op(name, "Migrar"):
            self._log("Migración cancelada por el usuario.", "warn")
            return

        backup = self._sv_backup.get().strip() or "."
        self._log(f"Migrando '{name}' → {new_path}…", "info")

        def _run():
            try:
                ok = self._mgr.migrate_share(name, new_path, backup)
            except Exception as exc:
                self.parent.after(0, lambda: self._log(
                    f"❌ Error inesperado migrando '{name}': {exc}", "err"))
                return
            msg = (f"✅ Share '{name}' migrado correctamente."
                   if ok else f"❌ Fallo al migrar '{name}'.")
            self.parent.after(0, lambda: self._log(msg, "ok" if ok else "err"))
            if ok:
                self.parent.after(0, self._on_connect)
        threading.Thread(target=_run, daemon=True).start()

    def _on_verify(self):
        name = self._selected_share()
        if not name:
            self._log("Selecciona un share primero.", "warn")
            return
        new_path = self._sv_new_path.get().strip()
        if not new_path:
            self._log("Indica la ruta esperada en 'Nueva ruta'.", "warn")
            return
        try:
            ok = self._mgr.verify_share(name, new_path)
        except Exception as exc:
            self._log(f"❌ Error verificando '{name}': {exc}", "err")
            return
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
        if not messagebox.askyesno(
            "Recrear share",
            f"Esto eliminará y recreará '{name}'.\n"
            "Los permisos SMB se resetearán.\n\n¿Continuar?"
        ):
            return

        # ── Verificar sesiones activas antes de recrear (issue #1) ──
        if not self._check_sessions_before_op(name, "Recrear"):
            self._log("Recreación cancelada por el usuario.", "warn")
            return

        backup = self._sv_backup.get().strip() or "."
        try:
            ok = self._mgr.recreate_share(name, new_path, backup_dir=backup)
        except Exception as exc:
            self._log(f"❌ Error recreando '{name}': {exc}", "err")
            return
        msg = (f"✅ '{name}' recreado en {new_path}."
               if ok else f"❌ Fallo al recrear '{name}'.")
        self._log(msg, "ok" if ok else "err")
        if ok:
            self._on_connect()
