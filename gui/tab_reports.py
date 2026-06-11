"""
Governance-Suite — Tab GUI: Reportes y archivos exportados (customtkinter)
"""
import customtkinter as ctk
from tkinter import ttk, messagebox
import tkinter as tk
import os
import subprocess
import sys
from config import OUTPUT_DIR, LOGS_DIR


class ReportsTab:
    def __init__(self, parent, colors):
        self.parent = parent
        self.colors = colors

    def build(self):
        c = self.colors
        frame = self.parent

        header = ctk.CTkFrame(frame, fg_color=c["bg"])
        header.pack(fill="x", padx=12, pady=10)
        ctk.CTkButton(header, text="🔄  Actualizar", width=120,
                      fg_color=c["surface"], text_color=c["fg"],
                      hover_color=c["accent"],
                      command=self._refresh).pack(side="left", padx=4)
        ctk.CTkButton(header, text="📂  Abrir carpeta output", width=180,
                      fg_color=c["surface"], text_color=c["fg"],
                      hover_color=c["accent"],
                      command=self._open_output).pack(side="left", padx=4)

        # Notebook interno (ttk)
        nb = ttk.Notebook(frame)
        nb.pack(fill="both", expand=True, padx=8, pady=4)

        self.output_frame = ttk.Frame(nb)
        self.logs_frame = ttk.Frame(nb)
        nb.add(self.output_frame, text="  Exportados  ")
        nb.add(self.logs_frame, text="  Logs  ")

        self.output_tree = ttk.Treeview(
            self.output_frame,
            columns=("Archivo", "Tamaño", "Fecha"),
            show="headings", height=12
        )
        for col, w in [("Archivo", 300), ("Tamaño", 120), ("Fecha", 180)]:
            self.output_tree.heading(col, text=col)
            self.output_tree.column(col, width=w)
        vsb = ttk.Scrollbar(self.output_frame, orient="vertical",
                            command=self.output_tree.yview)
        self.output_tree.configure(yscrollcommand=vsb.set)
        self.output_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.output_tree.bind("<Double-1>", self._open_file)

        self.logs_tree = ttk.Treeview(
            self.logs_frame,
            columns=("Archivo", "Tamaño", "Fecha"),
            show="headings", height=12
        )
        for col, w in [("Archivo", 300), ("Tamaño", 120), ("Fecha", 180)]:
            self.logs_tree.heading(col, text=col)
            self.logs_tree.column(col, width=w)
        vsb2 = ttk.Scrollbar(self.logs_frame, orient="vertical",
                             command=self.logs_tree.yview)
        self.logs_tree.configure(yscrollcommand=vsb2.set)
        self.logs_tree.pack(side="left", fill="both", expand=True)
        vsb2.pack(side="right", fill="y")

        self._refresh()

    def _refresh(self):
        self._load_tree(self.output_tree, OUTPUT_DIR)
        self._load_tree(self.logs_tree, LOGS_DIR)

    def _load_tree(self, tree, folder):
        for row in tree.get_children():
            tree.delete(row)
        if not folder.exists():
            return
        files = sorted(folder.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        from datetime import datetime
        for f in files:
            if f.is_file():
                size = f.stat().st_size
                size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
                mod = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                tree.insert("", "end", values=(f.name, size_str, mod), tags=(str(f),))

    def _open_file(self, event):
        item = self.output_tree.focus()
        if item:
            tags = self.output_tree.item(item, "tags")
            if tags:
                self._launch(tags[0])

    def _open_output(self):
        self._launch(str(OUTPUT_DIR))

    def _launch(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", str(e))
