"""
Governance-Suite — Tab GUI: Migración de archivos
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
from core.migration import migrate_directory
from core.exporter import auto_export


class MigrationTab:
    def __init__(self, parent, colors):
        self.parent = parent
        self.colors = colors
        self.results = []

    def build(self):
        c = self.colors
        frame = self.parent
        pad = {"padx": 12, "pady": 4}

        # Origen
        row0 = tk.Frame(frame, bg=c["bg"])
        row0.pack(fill=tk.X, **pad)
        tk.Label(row0, text="Origen:", width=10, anchor="w",
                 bg=c["bg"], fg=c["fg"]).pack(side=tk.LEFT)
        self.src_var = tk.StringVar()
        tk.Entry(row0, textvariable=self.src_var, width=50,
                 bg=c["surface"], fg=c["fg"], relief="flat").pack(side=tk.LEFT, padx=4)
        tk.Button(row0, text="Examinar", bg=c["surface"], fg=c["fg"],
                  relief="flat", command=lambda: self._browse(self.src_var)).pack(side=tk.LEFT)

        # Destino
        row1 = tk.Frame(frame, bg=c["bg"])
        row1.pack(fill=tk.X, **pad)
        tk.Label(row1, text="Destino:", width=10, anchor="w",
                 bg=c["bg"], fg=c["fg"]).pack(side=tk.LEFT)
        self.dst_var = tk.StringVar()
        tk.Entry(row1, textvariable=self.dst_var, width=50,
                 bg=c["surface"], fg=c["fg"], relief="flat").pack(side=tk.LEFT, padx=4)
        tk.Button(row1, text="Examinar", bg=c["surface"], fg=c["fg"],
                  relief="flat", command=lambda: self._browse(self.dst_var)).pack(side=tk.LEFT)

        # Opciones
        opts = tk.Frame(frame, bg=c["bg"])
        opts.pack(fill=tk.X, **pad)
        self.verify_var = tk.BooleanVar(value=True)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.sync_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opts, text="Verificar integridad", variable=self.verify_var,
                       bg=c["bg"], fg=c["fg"], selectcolor=c["surface"],
                       activebackground=c["bg"]).pack(side=tk.LEFT, padx=8)
        tk.Checkbutton(opts, text="Sobrescribir existentes", variable=self.overwrite_var,
                       bg=c["bg"], fg=c["fg"], selectcolor=c["surface"],
                       activebackground=c["bg"]).pack(side=tk.LEFT, padx=8)
        tk.Checkbutton(opts, text="Solo actualizar más nuevos", variable=self.sync_var,
                       bg=c["bg"], fg=c["fg"], selectcolor=c["surface"],
                       activebackground=c["bg"]).pack(side=tk.LEFT, padx=8)

        # Botón iniciar
        tk.Button(frame, text="  ▶  Iniciar migración",
                  bg=c["accent"], fg="#1e1e2e",
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  command=self._start).pack(pady=8)

        # Barra de progreso determinada + etiqueta de conteo
        pb_frame = tk.Frame(frame, bg=c["bg"])
        pb_frame.pack(fill=tk.X, padx=12, pady=(0, 2))
        self.progress = ttk.Progressbar(pb_frame, mode="determinate", maximum=100)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progress_label = tk.Label(pb_frame, text="", bg=c["bg"], fg=c["fg"],
                                       font=("Segoe UI", 9), width=18, anchor="e")
        self.progress_label.pack(side=tk.LEFT, padx=(6, 0))

        # Log de resultados
        self.log = tk.Text(frame, height=18, bg=c["surface"], fg=c["fg"],
                           font=("Consolas", 9), relief="flat", state="disabled")
        self.log.pack(fill=tk.BOTH, expand=True, padx=12)

        # Exportar
        btns = tk.Frame(frame, bg=c["bg"])
        btns.pack(fill=tk.X, padx=12, pady=6)
        for fmt in ("CSV", "Excel", "JSON"):
            tk.Button(btns, text=f"Exportar {fmt}", bg=c["surface"], fg=c["fg"],
                      relief="flat", command=lambda f=fmt.lower(): self._export(f)
                      ).pack(side=tk.LEFT, padx=4)

    def _browse(self, var):
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def _update_progress(self, done, total):
        pct = int(done / total * 100) if total else 0
        self.progress["value"] = pct
        self.progress_label.configure(text=f"{done} / {total}  ({pct}%)")

    def _start(self):
        src = self.src_var.get().strip()
        dst = self.dst_var.get().strip()
        if not src or not dst:
            messagebox.showwarning("Faltan datos", "Selecciona origen y destino.")
            return
        # Resetear barra
        self.progress["value"] = 0
        self.progress_label.configure(text="")
        self._log(f"Iniciando migración: {src} → {dst}")
        Thread(target=self._worker, args=(src, dst), daemon=True).start()

    def _worker(self, src, dst):
        counters = {"ok": 0, "updated": 0, "skipped": 0, "error": 0}

        def cb(done, total, r):
            status = r.get("status", "?")
            # Acumular contadores
            if status == "ok":
                counters["ok"] += 1
            elif status == "updated":
                counters["updated"] += 1
            elif status == "skipped":
                counters["skipped"] += 1
            elif status == "error":
                counters["error"] += 1

            self.parent.after(0, lambda d=done, t=total: self._update_progress(d, t))
            self.parent.after(0, lambda: self._log(
                f"[{status.upper()}] {r.get('src', '')}"
            ))

        try:
            self.results = migrate_directory(
                src, dst,
                verify=self.verify_var.get(),
                overwrite=self.overwrite_var.get(),
                sync_only=self.sync_var.get(),
                progress_callback=cb,
            )
            # Recalcular contadores desde resultados finales (fuente de verdad)
            total = len(self.results)
            ok      = sum(1 for r in self.results if r["status"] == "ok")
            updated = sum(1 for r in self.results if r["status"] == "updated")
            skipped = sum(1 for r in self.results if r["status"] == "skipped")
            errors  = sum(1 for r in self.results if r["status"] == "error")

            summary = (
                f"\n{'─' * 48}\n"
                f"  Migración finalizada — {total} archivo(s) procesado(s)\n"
                f"  ✅  Copiados:     {ok}\n"
                f"  🔄  Actualizados: {updated}\n"
                f"  ⏭️  Saltados:     {skipped}\n"
                f"  ❌  Errores:      {errors}\n"
                f"{'─' * 48}"
            )
            self.parent.after(0, lambda: self._log(summary))
            # Barra al 100% al terminar
            self.parent.after(0, lambda: self._update_progress(total, total))
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _export(self, fmt):
        if not self.results:
            messagebox.showinfo("Sin datos", "Primero realiza una migración.")
            return
        path = auto_export(self.results, "migration", fmt)
        messagebox.showinfo("Exportado", f"Guardado en:\n{path}")
