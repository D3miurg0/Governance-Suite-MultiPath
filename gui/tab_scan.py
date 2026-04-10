"""
Governance-Suite — Tab GUI: Escaneo de servidores
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
from core.scanner import scan_directory
from core.exporter import auto_export


class ScanTab:
    def __init__(self, parent, colors):
        self.parent = parent
        self.colors = colors
        self.results = []

    def build(self):
        c = self.colors
        frame = self.parent

        # Controles superiores
        ctrl = tk.Frame(frame, bg=c["bg"], pady=10)
        ctrl.pack(fill=tk.X, padx=12)

        tk.Label(ctrl, text="Ruta:", bg=c["bg"], fg=c["fg"],
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=(0,6))
        self.path_var = tk.StringVar()
        tk.Entry(ctrl, textvariable=self.path_var, width=55,
                 bg=c["surface"], fg=c["fg"], insertbackground=c["fg"],
                 relief="flat", font=("Segoe UI", 10)).grid(row=0, column=1, padx=(0,6))
        tk.Button(ctrl, text="Examinar", bg=c["surface"], fg=c["fg"],
                  relief="flat", command=self._browse).grid(row=0, column=2, padx=(0,12))

        self.recursive_var = tk.BooleanVar(value=True)
        tk.Checkbutton(ctrl, text="Recursivo", variable=self.recursive_var,
                       bg=c["bg"], fg=c["fg"], selectcolor=c["surface"],
                       activebackground=c["bg"]).grid(row=0, column=3, padx=6)

        tk.Button(ctrl, text="  ▶  Escanear", bg=c["accent"], fg="#1e1e2e",
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  command=self._start_scan).grid(row=0, column=4, padx=(12,0))

        # Barra de progreso
        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=12, pady=(0,4))

        # Tabla de resultados
        cols = ("Nombre", "Tipo", "Tamaño (KB)", "Modificado", "Ruta")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140 if col not in ("Ruta",) else 300)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12,0))
        vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,12))

        # Botones inferiores
        btns = tk.Frame(frame, bg=c["bg"])
        btns.pack(fill=tk.X, padx=12, pady=8)
        for fmt in ("CSV", "Excel", "JSON"):
            tk.Button(btns, text=f"Exportar {fmt}", bg=c["surface"], fg=c["fg"],
                      relief="flat", command=lambda f=fmt.lower(): self._export(f)
                      ).pack(side=tk.LEFT, padx=4)

        self.status_var = tk.StringVar(value="Esperando...")
        tk.Label(btns, textvariable=self.status_var,
                 bg=c["bg"], fg="#6c7086", font=("Segoe UI", 9)
                 ).pack(side=tk.RIGHT)

    def _browse(self):
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)

    def _start_scan(self):
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("Atención", "Ingresa una ruta válida.")
            return
        self.progress.start()
        self.status_var.set("Escaneando...")
        for row in self.tree.get_children():
            self.tree.delete(row)
        Thread(target=self._scan_worker, args=(path,), daemon=True).start()

    def _scan_worker(self, path):
        recursive = self.recursive_var.get()
        try:
            self.results = list(scan_directory(path, recursive=recursive))
            self.parent.after(0, self._populate_tree)
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.parent.after(0, self.progress.stop)

    def _populate_tree(self):
        for item in self.results[:2000]:  # Límite visual
            tipo = "Carpeta" if item["is_dir"] else "Archivo"
            size = round(item["size"] / 1024, 1) if not item["is_dir"] else ""
            self.tree.insert("", tk.END, values=(
                item["name"], tipo, size, item["modified"][:10], item["path"]
            ))
        self.status_var.set(f"{len(self.results)} elementos encontrados")

    def _export(self, fmt):
        if not self.results:
            messagebox.showinfo("Sin datos", "Primero realiza un escaneo.")
            return
        path = auto_export(self.results, "scan", fmt)
        messagebox.showinfo("Exportado", f"Guardado en:\n{path}")
