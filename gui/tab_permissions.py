"""
Governance-Suite — Tab GUI: Auditoría de permisos
"""
import tkinter as tk
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

        ctrl = tk.Frame(frame, bg=c["bg"], pady=10)
        ctrl.pack(fill=tk.X, padx=12)

        tk.Label(ctrl, text="Ruta:", bg=c["bg"], fg=c["fg"]).grid(row=0, column=0, padx=(0,6))
        self.path_var = tk.StringVar()
        tk.Entry(ctrl, textvariable=self.path_var, width=55,
                 bg=c["surface"], fg=c["fg"], relief="flat").grid(row=0, column=1, padx=(0,6))
        tk.Button(ctrl, text="Examinar", bg=c["surface"], fg=c["fg"],
                  relief="flat", command=self._browse).grid(row=0, column=2, padx=(0,12))

        self.recursive_var = tk.BooleanVar(value=True)
        self.files_var = tk.BooleanVar(value=False)
        tk.Checkbutton(ctrl, text="Recursivo", variable=self.recursive_var,
                       bg=c["bg"], fg=c["fg"], selectcolor=c["surface"],
                       activebackground=c["bg"]).grid(row=0, column=3)
        tk.Checkbutton(ctrl, text="Incluir archivos", variable=self.files_var,
                       bg=c["bg"], fg=c["fg"], selectcolor=c["surface"],
                       activebackground=c["bg"]).grid(row=0, column=4, padx=8)
        tk.Button(ctrl, text="  ▶  Auditar", bg=c["accent"], fg="#1e1e2e",
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  command=self._start).grid(row=0, column=5, padx=(12,0))

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=12, pady=(0,4))

        cols = ("Ruta", "Cuenta/Propietario", "Lectura", "Escritura", "Control Total")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            w = 300 if col == "Ruta" else 160
            self.tree.column(col, width=w)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12,0))
        vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,12))

        btns = tk.Frame(frame, bg=c["bg"])
        btns.pack(fill=tk.X, padx=12, pady=8)
        for fmt in ("CSV", "Excel", "JSON"):
            tk.Button(btns, text=f"Exportar {fmt}", bg=c["surface"], fg=c["fg"],
                      relief="flat", command=lambda f=fmt.lower(): self._export(f)
                      ).pack(side=tk.LEFT, padx=4)

        self.status_var = tk.StringVar(value="Esperando...")
        tk.Label(btns, textvariable=self.status_var, bg=c["bg"], fg="#6c7086",
                 font=("Segoe UI", 9)).pack(side=tk.RIGHT)

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
            self.tree.insert("", tk.END, values=(
                r.get("path", ""), account, read, write, fc
            ))
        self.status_var.set(f"{len(self.results)} entradas auditadas")

    def _export(self, fmt):
        if not self.results:
            messagebox.showinfo("Sin datos", "Primero realiza una auditoría.")
            return
        path = auto_export(self.results, "permissions", fmt)
        messagebox.showinfo("Exportado", f"Guardado en:\n{path}")
