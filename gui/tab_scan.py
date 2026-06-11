"""
Governance-Suite — Tab GUI: Escaneo de servidores (customtkinter)
"""
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
from core.scanner import scan_directory
from core.exporter import auto_export

_BG      = "#1e1e2e"
_FG      = "#cdd6f4"
_ACCENT  = "#89b4fa"
_SURFACE = "#313244"


class ScanTab:
    def __init__(self, parent, colors):
        self.parent = parent
        self.colors = colors
        self.results = []

    def build(self):
        c = self.colors
        frame = self.parent

        # Controles superiores
        ctrl = ctk.CTkFrame(frame, fg_color=c["bg"])
        ctrl.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(ctrl, text="Ruta:", text_color=c["fg"],
                     font=ctk.CTkFont("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.path_var = ctk.StringVar()
        ctk.CTkEntry(ctrl, textvariable=self.path_var, width=380,
                     fg_color=c["surface"], text_color=c["fg"]
                     ).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(ctrl, text="Examinar", width=90,
                      fg_color=c["surface"], text_color=c["fg"],
                      hover_color=c["accent"],
                      command=self._browse).grid(row=0, column=2, padx=(0, 12))

        self.recursive_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(ctrl, text="Recursivo", variable=self.recursive_var,
                        text_color=c["fg"], fg_color=c["accent"],
                        hover_color=c["surface"]).grid(row=0, column=3, padx=6)

        ctk.CTkButton(ctrl, text="  ▶  Escanear",
                      fg_color=c["accent"], text_color="#1e1e2e",
                      font=ctk.CTkFont("Segoe UI", 10, "bold"),
                      hover_color="#74c7ec",
                      command=self._start_scan).grid(row=0, column=4, padx=(12, 0))

        # Barra de progreso
        self.progress = ctk.CTkProgressBar(frame, mode="indeterminate",
                                           fg_color=c["surface"], progress_color=c["accent"])
        self.progress.pack(fill="x", padx=12, pady=(0, 4))

        # Tabla de resultados (ttk.Treeview no tiene reemplazo directo en CTk)
        cols = ("Nombre", "Tipo", "Tamaño (KB)", "Modificado", "Ruta")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140 if col != "Ruta" else 300)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(12, 0))
        vsb.pack(side="right", fill="y", padx=(0, 12))

        # Botones inferiores
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
            self.parent.after(0, self._populate)
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.parent.after(0, self.progress.stop)
            self.parent.after(0, lambda: self.status_var.set(
                f"{len(self.results)} archivos encontrados"))

    def _populate(self):
        for item in self.results[:5000]:
            self.tree.insert("", "end", values=(
                item.get("name", ""),
                item.get("type", ""),
                round(item.get("size", 0) / 1024, 1),
                item.get("modified", ""),
                item.get("path", ""),
            ))

    def _export(self, fmt):
        if not self.results:
            messagebox.showinfo("Sin datos", "Primero realiza un escaneo.")
            return
        path = auto_export(self.results, "scan", fmt)
        messagebox.showinfo("Exportado", f"Guardado en:\n{path}")
