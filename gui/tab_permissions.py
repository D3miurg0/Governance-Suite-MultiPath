"""
Governance-Suite — Tab GUI: Auditoría de permisos (customtkinter)
"""
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
from core.permission import audit_path
from core.exporter import auto_export


class PermissionsTab:
    def __init__(self, parent, colors):
        self.parent = parent
        self.colors = colors
        self.results = []

    def build(self):
        c = self.colors
        frame = self.parent

        ctrl = ctk.CTkFrame(frame, fg_color=c["bg"])
        ctrl.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(ctrl, text="Ruta:", text_color=c["fg"]).grid(row=0, column=0, padx=(0, 6))
        self.path_var = ctk.StringVar()
        ctk.CTkEntry(ctrl, textvariable=self.path_var, width=380,
                     fg_color=c["surface"], text_color=c["fg"]
                     ).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(ctrl, text="Examinar", width=90,
                      fg_color=c["surface"], text_color=c["fg"],
                      hover_color=c["accent"],
                      command=self._browse).grid(row=0, column=2, padx=(0, 12))

        self.recursive_var = ctk.BooleanVar(value=True)
        self.files_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(ctrl, text="Recursivo", variable=self.recursive_var,
                        text_color=c["fg"], fg_color=c["accent"],
                        hover_color=c["surface"]).grid(row=0, column=3)
        ctk.CTkCheckBox(ctrl, text="Incluir archivos", variable=self.files_var,
                        text_color=c["fg"], fg_color=c["accent"],
                        hover_color=c["surface"]).grid(row=0, column=4, padx=8)
        ctk.CTkButton(ctrl, text="  ▶  Auditar",
                      fg_color=c["accent"], text_color="#1e1e2e",
                      font=ctk.CTkFont("Segoe UI", 10, "bold"),
                      hover_color="#74c7ec",
                      command=self._start).grid(row=0, column=5, padx=(12, 0))

        self.progress = ctk.CTkProgressBar(frame, mode="indeterminate",
                                           fg_color=c["surface"], progress_color=c["accent"])
        self.progress.pack(fill="x", padx=12, pady=(0, 4))

        cols = ("Ruta", "Cuenta/Propietario", "Lectura", "Escritura", "Control Total")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            w = 300 if col == "Ruta" else 160
            self.tree.column(col, width=w)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(12, 0))
        vsb.pack(side="right", fill="y", padx=(0, 12))

        btns = ctk.CTkFrame(frame, fg_color=c["bg"])
        btns.pack(fill="x", padx=12, pady=8)
        for fmt in ("CSV", "Excel", "JSON"):
            ctk.CTkButton(btns, text=f"Exportar {fmt}", width=110,
                          fg_color=c["surface"], text_color=c["fg"],
                          hover_color=c["accent"],
                          command=lambda f=fmt.lower(): self._export(f)
                          ).pack(side="left", padx=4)

        self.status_var = ctk.StringVar(value="Esperando...")
        ctk.CTkLabel(btns, textvariable=self.status_var,
                     text_color="#6c7086",
                     font=ctk.CTkFont("Segoe UI", 9)).pack(side="right")

    def _browse(self):
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)

    def _start(self):
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("Atención", "Selecciona una ruta.")
            return
        self.progress.start()
        self.status_var.set("Auditando...")
        for row in self.tree.get_children():
            self.tree.delete(row)
        Thread(target=self._worker, args=(path,), daemon=True).start()

    def _worker(self, path):
        try:
            self.results = audit_path(
                path,
                recursive=self.recursive_var.get(),
                include_files=self.files_var.get(),
            )
            self.parent.after(0, self._populate)
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.parent.after(0, self.progress.stop)

    def _populate(self):
        for r in self.results[:2000]:
            account = r.get("account", str(r.get("owner", "N/A")))
            read = "✅" if r.get("readable") or r.get("read") else "❌"
            write = "✅" if r.get("writable") or r.get("write") else "❌"
            fc = "✅" if r.get("full_control") else "❌"
            self.tree.insert("", "end", values=(
                r.get("path", ""), account, read, write, fc
            ))
        self.status_var.set(f"{len(self.results)} entradas auditadas")

    def _export(self, fmt):
        if not self.results:
            messagebox.showinfo("Sin datos", "Primero realiza una auditoría.")
            return
        path = auto_export(self.results, "permissions", fmt)
        messagebox.showinfo("Exportado", f"Guardado en:\n{path}")
