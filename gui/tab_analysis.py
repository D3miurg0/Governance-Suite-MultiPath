"""
Governance-Suite — Tab GUI: Análisis y métricas
"""
import tkinter as tk
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

        ctrl = tk.Frame(frame, bg=c["bg"], pady=10)
        ctrl.pack(fill=tk.X, padx=12)

        tk.Label(ctrl, text="Ruta:", bg=c["bg"], fg=c["fg"]).grid(row=0, column=0, padx=(0,6))
        self.path_var = tk.StringVar()
        tk.Entry(ctrl, textvariable=self.path_var, width=55,
                 bg=c["surface"], fg=c["fg"], relief="flat").grid(row=0, column=1, padx=(0,6))
        tk.Button(ctrl, text="Examinar", bg=c["surface"], fg=c["fg"],
                  relief="flat", command=self._browse).grid(row=0, column=2, padx=(0,12))
        tk.Button(ctrl, text="  ▶  Analizar", bg=c["accent"], fg="#1e1e2e",
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  command=self._start).grid(row=0, column=3)

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=12, pady=(0,4))

        # Panel de resumen
        summary_frame = tk.LabelFrame(frame, text=" Resumen ",
                                      bg=c["bg"], fg=c["accent"],
                                      font=("Segoe UI", 10, "bold"))
        summary_frame.pack(fill=tk.X, padx=12, pady=4)
        self.summary_vars = {}
        fields = [
            ("total_files", "Archivos totales"),
            ("total_dirs", "Directorios"),
            ("total_size_mb", "Tamaño total (MB)"),
            ("avg_file_size_kb", "Promedio por archivo (KB)"),
        ]
        for i, (key, label) in enumerate(fields):
            tk.Label(summary_frame, text=f"{label}:", bg=c["bg"], fg=c["fg"],
                     font=("Segoe UI", 9)).grid(row=i//2, column=(i%2)*2, sticky="w", padx=12, pady=2)
            var = tk.StringVar(value="—")
            self.summary_vars[key] = var
            tk.Label(summary_frame, textvariable=var, bg=c["bg"], fg=c["accent"],
                     font=("Segoe UI", 10, "bold")).grid(row=i//2, column=(i%2)*2+1, sticky="w", padx=4)

        # Score
        score_frame = tk.Frame(frame, bg=c["bg"])
        score_frame.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(score_frame, text="Governance Score:", bg=c["bg"], fg=c["fg"],
                 font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        self.score_var = tk.StringVar(value="—")
        tk.Label(score_frame, textvariable=self.score_var, bg=c["bg"], fg=c["accent"],
                 font=("Segoe UI", 20, "bold")).pack(side=tk.LEFT, padx=12)

        # Archivos grandes
        tk.Label(frame, text="Archivos más grandes:", bg=c["bg"], fg=c["fg"],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(8,0))
        cols = ("Nombre", "Tamaño (MB)", "Ruta")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=10)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=300 if col == "Ruta" else 180)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=12)

        btns = tk.Frame(frame, bg=c["bg"])
        btns.pack(fill=tk.X, padx=12, pady=8)
        for fmt in ("CSV", "Excel", "JSON"):
            tk.Button(btns, text=f"Exportar {fmt}", bg=c["surface"], fg=c["fg"],
                      relief="flat", command=lambda f=fmt.lower(): self._export(f)
                      ).pack(side=tk.LEFT, padx=4)

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
        for row in self.tree.get_children():
            self.tree.delete(row)
        for f in large[:30]:
            self.tree.insert("", tk.END, values=(
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
