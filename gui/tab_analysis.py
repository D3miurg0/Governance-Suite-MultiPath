"""
Governance-Suite — Tab GUI: Análisis y métricas (customtkinter)
"""
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
from core.scanner import scan_directory
from core.analysis import summarize_scan, detect_large_files, detect_old_files
from core.metrics import governance_score
from core.exporter import auto_export


class AnalysisTab:
    def __init__(self, parent, colors):
        self.parent = parent
        self.colors = colors
        self.items = []

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
        ctk.CTkButton(ctrl, text="  ▶  Analizar",
                      fg_color=c["accent"], text_color="#1e1e2e",
                      font=ctk.CTkFont("Segoe UI", 10, "bold"),
                      hover_color="#74c7ec",
                      command=self._start).grid(row=0, column=3)

        self.progress = ctk.CTkProgressBar(frame, mode="indeterminate",
                                           fg_color=c["surface"], progress_color=c["accent"])
        self.progress.pack(fill="x", padx=12, pady=(0, 4))

        # Panel de resumen
        summary_frame = ctk.CTkFrame(frame, fg_color=c["surface"], corner_radius=8)
        summary_frame.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(summary_frame, text=" Resumen ",
                     text_color=c["accent"],
                     font=ctk.CTkFont("Segoe UI", 10, "bold")
                     ).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(6, 2))

        self.summary_vars = {}
        fields = [
            ("total_files",      "Archivos totales"),
            ("total_dirs",       "Directorios"),
            ("total_size_mb",    "Tamaño total (MB)"),
            ("avg_file_size_kb", "Promedio por archivo (KB)"),
        ]
        for i, (key, label) in enumerate(fields):
            row_i = i // 2 + 1
            col_i = (i % 2) * 2
            ctk.CTkLabel(summary_frame, text=f"{label}:",
                         text_color=c["fg"],
                         font=ctk.CTkFont("Segoe UI", 9)
                         ).grid(row=row_i, column=col_i, sticky="w", padx=12, pady=2)
            var = ctk.StringVar(value="—")
            self.summary_vars[key] = var
            ctk.CTkLabel(summary_frame, textvariable=var,
                         text_color=c["accent"],
                         font=ctk.CTkFont("Segoe UI", 10, "bold")
                         ).grid(row=row_i, column=col_i + 1, sticky="w", padx=4)

        # Score
        score_frame = ctk.CTkFrame(frame, fg_color=c["bg"])
        score_frame.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(score_frame, text="Governance Score:",
                     text_color=c["fg"],
                     font=ctk.CTkFont("Segoe UI", 11, "bold")
                     ).pack(side="left")
        self.score_var = ctk.StringVar(value="—")
        self.score_lbl = ctk.CTkLabel(score_frame, textvariable=self.score_var,
                                      text_color=c["accent"],
                                      font=ctk.CTkFont("Segoe UI", 20, "bold"))
        self.score_lbl.pack(side="left", padx=12)

        # Archivos grandes
        ctk.CTkLabel(frame, text="Archivos más grandes:",
                     text_color=c["fg"],
                     font=ctk.CTkFont("Segoe UI", 10, "bold")
                     ).pack(anchor="w", padx=14, pady=(8, 0))
        cols = ("Nombre", "Tamaño (MB)", "Ruta")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=10)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=300 if col == "Ruta" else 180)
        self.tree.pack(fill="both", expand=True, padx=12)

        btns = ctk.CTkFrame(frame, fg_color=c["bg"])
        btns.pack(fill="x", padx=12, pady=8)
        for fmt in ("CSV", "Excel", "JSON"):
            ctk.CTkButton(btns, text=f"Exportar {fmt}", width=110,
                          fg_color=c["surface"], text_color=c["fg"],
                          hover_color=c["accent"],
                          command=lambda f=fmt.lower(): self._export(f)
                          ).pack(side="left", padx=4)

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
        Thread(target=self._worker, args=(path,), daemon=True).start()

    def _worker(self, path):
        try:
            self.items = list(scan_directory(path))
            summary = summarize_scan(self.items)
            score = governance_score(self.items)
            large = detect_large_files(self.items, threshold_mb=50)
            self.parent.after(0, lambda: self._update_ui(summary, score, large))
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.parent.after(0, self.progress.stop)

    def _update_ui(self, summary, score, large):
        for key, var in self.summary_vars.items():
            var.set(str(summary.get(key, "—")))
        sc = score["score"]
        color = "#a6e3a1" if sc >= 70 else ("#f9e2af" if sc >= 40 else "#f38ba8")
        self.score_var.set(f"{sc}/100")
        self.score_lbl.configure(text_color=color)
        for row in self.tree.get_children():
            self.tree.delete(row)
        for f in large[:30]:
            self.tree.insert("", "end", values=(
                f["name"],
                round(f["size"] / 1024 / 1024, 1),
                f["path"]
            ))

    def _export(self, fmt):
        if not self.items:
            messagebox.showinfo("Sin datos", "Primero realiza un análisis.")
            return
        path = auto_export(self.items, "analysis", fmt)
        messagebox.showinfo("Exportado", f"Guardado en:\n{path}")
