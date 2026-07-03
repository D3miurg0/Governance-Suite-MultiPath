"""
gui/tab_share_manager.py
─────────────────────────────────────────────────────────────────────────────
Pestaña GUI — Gestión y Migración de Shares SMB
Permite:
  • Listar shares del servidor local con su ruta actual
  • Exportar backup de configuración y permisos SMB
  • Migrar un share a nueva ruta (update sin eliminar)
  • Verificar que el share apunta a la ruta correcta
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import customtkinter as ctk

from modules.share_manager import ShareManagerModule


class ShareManagerTab:
    def __init__(self, parent, colors: dict, core=None):
        self.parent = parent
        self.c = colors
        self.core = core
        self.mgr = ShareManagerModule(core)
        self._shares_cache: list[dict] = []

    def build(self):
        root = ctk.CTkFrame(self.parent, fg_color=self.c["bg"])
        root.pack(fill="both", expand=True, padx=10, pady=8)

        # ── Sección superior: lista de shares ────────────────────────────
        top = ctk.CTkFrame(root, fg_color=self.c["surface"], corner_radius=8)
        top.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            top,
            text="📂  Shares del servidor",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            text_color=self.c["accent"],
        ).pack(anchor="w", padx=12, pady=(10, 4))

        # Treeview de shares
        tree_frame = tk.Frame(top, bg=self.c["surface"])
        tree_frame.pack(fill="x", padx=12, pady=(0, 8))

        cols = ("Nombre", "Ruta actual", "Comentario")
        self.tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings", height=7, selectmode="browse"
        )
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w", width=240 if col == "Ruta actual" else 160)
        self.tree.pack(side="left", fill="x", expand=True)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_share_select)

        btn_row = ctk.CTkFrame(top, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            btn_row, text="🔄  Actualizar lista",
            command=self._refresh_shares, width=160
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="💾  Exportar backup",
            command=self._export_shares, width=160,
            fg_color="#313244", hover_color="#45475a"
        ).pack(side="left")

        # ── Sección migración ─────────────────────────────────────────────
        mid = ctk.CTkFrame(root, fg_color=self.c["surface"], corner_radius=8)
        mid.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            mid,
            text="🔀  Migrar share a nueva ruta",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            text_color=self.c["accent"],
        ).pack(anchor="w", padx=12, pady=(10, 6))

        grid = ctk.CTkFrame(mid, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=(0, 10))

        # Share seleccionado
        ctk.CTkLabel(grid, text="Share:", width=100, anchor="e").grid(row=0, column=0, padx=(0, 8), pady=4, sticky="e")
        self.var_share_name = ctk.StringVar(value="")
        self.ent_share = ctk.CTkEntry(grid, textvariable=self.var_share_name, width=200, placeholder_text="GDL")
        self.ent_share.grid(row=0, column=1, padx=(0, 8), pady=4, sticky="w")
        ctk.CTkLabel(grid, text="(se rellena al seleccionar en la lista)", text_color="#6c7086", font=ctk.CTkFont(size=10)).grid(
            row=0, column=2, sticky="w"
        )

        # Nueva ruta
        ctk.CTkLabel(grid, text="Nueva ruta:", width=100, anchor="e").grid(row=1, column=0, padx=(0, 8), pady=4, sticky="e")
        self.var_new_path = ctk.StringVar()
        self.ent_new_path = ctk.CTkEntry(grid, textvariable=self.var_new_path, width=340, placeholder_text=r"E:\GDL")
        self.ent_new_path.grid(row=1, column=1, padx=(0, 8), pady=4, sticky="w")
        ctk.CTkButton(
            grid, text="📁", width=36,
            command=self._browse_new_path
        ).grid(row=1, column=2, pady=4, sticky="w")

        # Directorio de backup
        ctk.CTkLabel(grid, text="Backup en:", width=100, anchor="e").grid(row=2, column=0, padx=(0, 8), pady=4, sticky="e")
        self.var_backup_dir = ctk.StringVar(value=r"C:\Temp")
        ctk.CTkEntry(grid, textvariable=self.var_backup_dir, width=340).grid(row=2, column=1, padx=(0, 8), pady=4, sticky="w")
        ctk.CTkButton(
            grid, text="📁", width=36,
            command=self._browse_backup_dir
        ).grid(row=2, column=2, pady=4, sticky="w")

        # Botones acción
        action_row = ctk.CTkFrame(mid, fg_color="transparent")
        action_row.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkButton(
            action_row,
            text="🚀  Migrar share (update sin eliminar)",
            command=self._migrate_share,
            width=280,
            fg_color="#1e6b3e",
            hover_color="#166130",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_row,
            text="✔  Solo verificar ruta",
            command=self._verify_share,
            width=180,
            fg_color="#313244",
            hover_color="#45475a",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_row,
            text="🔃  Recrear share (eliminar + crear)",
            command=self._recreate_share,
            width=230,
            fg_color="#6b3a1e",
            hover_color="#7a4422",
        ).pack(side="left")

        # ── Log ───────────────────────────────────────────────────────────
        log_frame = ctk.CTkFrame(root, fg_color=self.c["surface"], corner_radius=8)
        log_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            log_frame,
            text="📋  Log",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=self.c["accent"],
        ).pack(anchor="w", padx=12, pady=(8, 2))

        self.log_box = tk.Text(
            log_frame,
            height=10,
            bg="#181825",
            fg="#cdd6f4",
            font=("Consolas", 9),
            relief="flat",
            wrap="word",
            state="disabled",
        )
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # Tags de color en log
        self.log_box.tag_config("ok",    foreground="#a6e3a1")
        self.log_box.tag_config("error", foreground="#f38ba8")
        self.log_box.tag_config("warn",  foreground="#fab387")
        self.log_box.tag_config("info",  foreground="#89dceb")

        # Carga inicial
        self._refresh_shares()

    # ──────────────────────────────────────────────────────────────────────
    # Helpers UI
    # ──────────────────────────────────────────────────────────────────────

    def _log(self, msg: str, tag: str = "info"):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}] {msg}\n", tag)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _browse_new_path(self):
        path = filedialog.askdirectory(title="Seleccionar nueva ruta del share")
        if path:
            self.var_new_path.set(path.replace("/", "\\"))

    def _browse_backup_dir(self):
        path = filedialog.askdirectory(title="Seleccionar directorio de backup")
        if path:
            self.var_backup_dir.set(path.replace("/", "\\"))

    def _on_share_select(self, event):
        sel = self.tree.selection()
        if sel:
            values = self.tree.item(sel[0])["values"]
            if values:
                self.var_share_name.set(str(values[0]))

    # ──────────────────────────────────────────────────────────────────────
    # Acciones
    # ──────────────────────────────────────────────────────────────────────

    def _refresh_shares(self):
        def _work():
            self._log("Listando shares...", "info")
            shares = self.mgr.list_shares()
            self._shares_cache = shares
            self.tree.delete(*self.tree.get_children())
            for s in shares:
                self.tree.insert("", "end", values=(s["name"], s["path"], s["comment"]))
            self._log(f"Encontrados {len(shares)} shares.", "ok")

        threading.Thread(target=_work, daemon=True).start()

    def _export_shares(self):
        output_dir = self.var_backup_dir.get() or r"C:\Temp"

        def _work():
            self._log(f"Exportando backup → {output_dir}", "info")
            result = self.mgr.export_shares(output_dir)
            if result:
                self._log(f"Backup guardado en: {result}", "ok")
            else:
                self._log("Error al exportar backup.", "error")

        threading.Thread(target=_work, daemon=True).start()

    def _migrate_share(self):
        name = self.var_share_name.get().strip()
        new_path = self.var_new_path.get().strip()
        backup_dir = self.var_backup_dir.get().strip() or r"C:\Temp"

        if not name or not new_path:
            messagebox.showwarning("Datos incompletos", "Especifica el nombre del share y la nueva ruta.")
            return

        confirm = messagebox.askyesno(
            "Confirmar migración",
            f"Se va a actualizar el share '{name}' para apuntar a:\n\n{new_path}\n\n"
            f"Se exportará un backup antes de proceder.\n\n¿Continuar?"
        )
        if not confirm:
            return

        def _work():
            self._log(f"Iniciando migración de share '{name}' → {new_path}", "info")
            ok = self.mgr.migrate_share(name, new_path, backup_dir)
            if ok:
                self._log(f"✅ Share '{name}' migrado correctamente a {new_path}", "ok")
            else:
                self._log(f"❌ Falló la migración del share '{name}'", "error")
            self._refresh_shares()

        threading.Thread(target=_work, daemon=True).start()

    def _verify_share(self):
        name = self.var_share_name.get().strip()
        expected = self.var_new_path.get().strip()

        if not name or not expected:
            messagebox.showwarning("Datos incompletos", "Especifica el nombre del share y la ruta esperada.")
            return

        def _work():
            self._log(f"Verificando share '{name}' → {expected}", "info")
            ok = self.mgr.verify_share(name, expected)
            if ok:
                self._log(f"✅ Verificación OK: '{name}' apunta a {expected}", "ok")
            else:
                info = self.mgr.get_share_info(name)
                actual = info["path"] if info else "N/A"
                self._log(f"❌ El share '{name}' apunta a '{actual}' (esperado: '{expected}')", "error")

        threading.Thread(target=_work, daemon=True).start()

    def _recreate_share(self):
        name = self.var_share_name.get().strip()
        new_path = self.var_new_path.get().strip()

        if not name or not new_path:
            messagebox.showwarning("Datos incompletos", "Especifica el nombre del share y la nueva ruta.")
            return

        confirm = messagebox.askyesno(
            "⚠️  Confirmar recreación",
            f"ADVERTENCIA: Esto eliminará el share '{name}' y lo recreará en:\n\n{new_path}\n\n"
            f"Los permisos SMB específicos NO se conservan automáticamente.\n"
            f"Exporta un backup primero para poder reaplicarlos.\n\n¿Continuar?",
            icon="warning"
        )
        if not confirm:
            return

        def _work():
            self._log(f"Recreando share '{name}' en {new_path}...", "warn")
            ok = self.mgr.recreate_share(name, new_path)
            if ok:
                self._log(f"✅ Share '{name}' recreado en {new_path}. Revisar permisos SMB.", "ok")
            else:
                self._log(f"❌ Error al recrear el share '{name}'.", "error")
            self._refresh_shares()

        threading.Thread(target=_work, daemon=True).start()
