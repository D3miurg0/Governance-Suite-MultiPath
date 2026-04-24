"""
Governance-Suite — Tab GUI: Migración de archivos
Soporta filtro por año o rango de fechas de modificación.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
from datetime import datetime
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

        # --- Origen ---
        row0 = tk.Frame(frame, bg=c["bg"])
        row0.pack(fill=tk.X, **pad)
        tk.Label(row0, text="Origen:", width=10, anchor="w",
                 bg=c["bg"], fg=c["fg"]).pack(side=tk.LEFT)
        self.src_var = tk.StringVar()
        tk.Entry(row0, textvariable=self.src_var, width=50,
                 bg=c["surface"], fg=c["fg"], relief="flat").pack(side=tk.LEFT, padx=4)
        tk.Button(row0, text="Examinar", bg=c["surface"], fg=c["fg"],
                  relief="flat", command=lambda: self._browse(self.src_var)).pack(side=tk.LEFT)

        # --- Destino ---
        row1 = tk.Frame(frame, bg=c["bg"])
        row1.pack(fill=tk.X, **pad)
        tk.Label(row1, text="Destino:", width=10, anchor="w",
                 bg=c["bg"], fg=c["fg"]).pack(side=tk.LEFT)
        self.dst_var = tk.StringVar()
        tk.Entry(row1, textvariable=self.dst_var, width=50,
                 bg=c["surface"], fg=c["fg"], relief="flat").pack(side=tk.LEFT, padx=4)
        tk.Button(row1, text="Examinar", bg=c["surface"], fg=c["fg"],
                  relief="flat", command=lambda: self._browse(self.dst_var)).pack(side=tk.LEFT)

        # --- Filtro por fecha ---
        date_frame = tk.LabelFrame(frame, text=" Filtro por fecha de modificación ",
                                   bg=c["bg"], fg=c["fg"], relief="flat",
                                   font=("Segoe UI", 9))
        date_frame.pack(fill=tk.X, padx=12, pady=(6, 2))

        # Año exacto
        year_row = tk.Frame(date_frame, bg=c["bg"])
        year_row.pack(fill=tk.X, padx=8, pady=3)
        self.year_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(year_row, text="Solo año:", variable=self.year_enabled,
                       bg=c["bg"], fg=c["fg"], selectcolor=c["surface"],
                       activebackground=c["bg"],
                       command=self._toggle_date_fields).pack(side=tk.LEFT)
        self.year_var = tk.StringVar(value=str(datetime.now().year))
        self.year_entry = tk.Entry(year_row, textvariable=self.year_var, width=8,
                                   bg=c["surface"], fg=c["fg"], relief="flat",
                                   state="disabled")
        self.year_entry.pack(side=tk.LEFT, padx=6)

        # Rango desde / hasta
        range_row = tk.Frame(date_frame, bg=c["bg"])
        range_row.pack(fill=tk.X, padx=8, pady=(0, 4))
        self.range_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(range_row, text="Rango:", variable=self.range_enabled,
                       bg=c["bg"], fg=c["fg"], selectcolor=c["surface"],
                       activebackground=c["bg"],
                       command=self._toggle_date_fields).pack(side=tk.LEFT)
        tk.Label(range_row, text="Desde (YYYY-MM-DD):", bg=c["bg"],
                 fg=c["fg"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(12, 2))
        self.date_from_var = tk.StringVar()
        self.date_from_entry = tk.Entry(range_row, textvariable=self.date_from_var,
                                        width=12, bg=c["surface"], fg=c["fg"],
                                        relief="flat", state="disabled")
        self.date_from_entry.pack(side=tk.LEFT, padx=4)
        tk.Label(range_row, text="Hasta:", bg=c["bg"],
                 fg=c["fg"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(8, 2))
        self.date_to_var = tk.StringVar()
        self.date_to_entry = tk.Entry(range_row, textvariable=self.date_to_var,
                                      width=12, bg=c["surface"], fg=c["fg"],
                                      relief="flat", state="disabled")
        self.date_to_entry.pack(side=tk.LEFT, padx=4)

        # --- Opciones generales ---
        opts = tk.Frame(frame, bg=c["bg"])
        opts.pack(fill=tk.X, **pad)
        self.verify_var   = tk.BooleanVar(value=True)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.sync_var     = tk.BooleanVar(value=False)
        tk.Checkbutton(opts, text="Verificar integridad",       variable=self.verify_var,
                       bg=c["bg"], fg=c["fg"], selectcolor=c["surface"],
                       activebackground=c["bg"]).pack(side=tk.LEFT, padx=8)
        tk.Checkbutton(opts, text="Sobrescribir existentes",    variable=self.overwrite_var,
                       bg=c["bg"], fg=c["fg"], selectcolor=c["surface"],
                       activebackground=c["bg"]).pack(side=tk.LEFT, padx=8)
        tk.Checkbutton(opts, text="Solo actualizar más nuevos", variable=self.sync_var,
                       bg=c["bg"], fg=c["fg"], selectcolor=c["surface"],
                       activebackground=c["bg"]).pack(side=tk.LEFT, padx=8)

        # --- Botón iniciar ---
        tk.Button(frame, text="  ▶  Iniciar migración",
                  bg=c["accent"], fg="#1e1e2e",
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  command=self._start).pack(pady=8)

        # --- Barra de progreso + etiqueta ---
        pb_frame = tk.Frame(frame, bg=c["bg"])
        pb_frame.pack(fill=tk.X, padx=12, pady=(0, 2))
        self.progress = ttk.Progressbar(pb_frame, mode="indeterminate", maximum=100)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progress_label = tk.Label(pb_frame, text="", bg=c["bg"], fg=c["fg"],
                                       font=("Segoe UI", 9), width=18, anchor="e")
        self.progress_label.pack(side=tk.LEFT, padx=(6, 0))

        # --- Log ---
        self.log = tk.Text(frame, height=16, bg=c["surface"], fg=c["fg"],
                           font=("Consolas", 9), relief="flat", state="disabled")
        self.log.pack(fill=tk.BOTH, expand=True, padx=12)

        # --- Exportar ---
        btns = tk.Frame(frame, bg=c["bg"])
        btns.pack(fill=tk.X, padx=12, pady=6)
        for fmt in ("CSV", "Excel", "JSON"):
            tk.Button(btns, text=f"Exportar {fmt}", bg=c["surface"], fg=c["fg"],
                      relief="flat",
                      command=lambda f=fmt.lower(): self._export(f)).pack(side=tk.LEFT, padx=4)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _toggle_date_fields(self):
        """Habilita/deshabilita campos según el checkbox activo."""
        year_state  = "normal" if self.year_enabled.get()  else "disabled"
        range_state = "normal" if self.range_enabled.get() else "disabled"
        self.year_entry.configure(state=year_state)
        self.date_from_entry.configure(state=range_state)
        self.date_to_entry.configure(state=range_state)

    def _browse(self, var):
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def _set_scanning_mode(self):
        self.progress.configure(mode="indeterminate")
        self.progress.start(10)
        self.progress_label.configure(text="Escaneando...")

    def _set_progress_mode(self, total):
        self.progress.stop()
        if total == 0:
            self.progress.configure(mode="determinate", maximum=1, value=0)
            self.progress_label.configure(text="Sin archivos")
        else:
            self.progress.configure(mode="determinate", maximum=100, value=0)
            self.progress_label.configure(text=f"0 / {total}  (0%)")

    def _update_progress(self, done, total):
        pct = int(done / total * 100) if total else 0
        self.progress["value"] = pct
        self.progress_label.configure(text=f"{done} / {total}  ({pct}%)")

    # ------------------------------------------------------------------
    # Validación de fecha
    # ------------------------------------------------------------------

    def _parse_date_inputs(self):
        """Parsea y valida los campos de fecha. Devuelve (year, date_from, date_to) o lanza ValueError."""
        year = date_from = date_to = None
        fmt = "%Y-%m-%d"
        if self.year_enabled.get():
            raw = self.year_var.get().strip()
            if not raw.isdigit() or not (1990 <= int(raw) <= datetime.now().year + 1):
                raise ValueError(f"Año inválido: '{raw}'. Usa un año entre 1990 y {datetime.now().year + 1}.")
            year = int(raw)
        if self.range_enabled.get():
            raw_from = self.date_from_var.get().strip()
            raw_to   = self.date_to_var.get().strip()
            if raw_from:
                try:
                    date_from = datetime.strptime(raw_from, fmt)
                except ValueError:
                    raise ValueError(f"Fecha 'Desde' inválida: '{raw_from}'. Formato: YYYY-MM-DD")
            if raw_to:
                try:
                    date_to = datetime.strptime(raw_to, fmt).replace(hour=23, minute=59, second=59)
                except ValueError:
                    raise ValueError(f"Fecha 'Hasta' inválida: '{raw_to}'. Formato: YYYY-MM-DD")
            if date_from and date_to and date_from > date_to:
                raise ValueError("La fecha 'Desde' no puede ser mayor que 'Hasta'.")
        return year, date_from, date_to

    # ------------------------------------------------------------------
    # Flujo principal
    # ------------------------------------------------------------------

    def _start(self):
        src = self.src_var.get().strip()
        dst = self.dst_var.get().strip()
        if not src or not dst:
            messagebox.showwarning("Faltan datos", "Selecciona origen y destino.")
            return
        try:
            year, date_from, date_to = self._parse_date_inputs()
        except ValueError as e:
            messagebox.showwarning("Filtro de fecha inválido", str(e))
            return

        self.results = []
        self._log(f"Iniciando migración: {src} → {dst}")
        if year:
            self._log(f"  Filtro: año {year}")
        if date_from or date_to:
            self._log(f"  Filtro: {date_from or '—'} → {date_to or '—'}")
        self._set_scanning_mode()
        Thread(target=self._worker,
               args=(src, dst, year, date_from, date_to), daemon=True).start()

    def _worker(self, src, dst, year, date_from, date_to):
        self.parent.after(0, lambda: self._log(
            "🔍 Escaneando archivos en origen..."
        ))
        first_callback = [True]

        def cb(done, total, r):
            if first_callback[0]:
                first_callback[0] = False
                self.parent.after(0, lambda t=total: self._set_progress_mode(t))
                self.parent.after(0, lambda t=total: self._log(
                    f"📂 {t} archivo(s) encontrado(s). Copiando..."
                ))
            status = r.get("status", "?")
            self.parent.after(0, lambda d=done, t=total: self._update_progress(d, t))
            self.parent.after(0, lambda s=status, rr=r: self._log(
                f"[{s.upper()}] {rr.get('src', '')}"
            ))

        try:
            self.results = migrate_directory(
                src, dst,
                verify=self.verify_var.get(),
                overwrite=self.overwrite_var.get(),
                sync_only=self.sync_var.get(),
                progress_callback=cb,
                year=year,
                date_from=date_from,
                date_to=date_to,
            )
            total   = len(self.results)
            ok      = sum(1 for r in self.results if r["status"] == "ok")
            updated = sum(1 for r in self.results if r["status"] == "updated")
            skipped = sum(1 for r in self.results if r["status"] == "skipped")
            errors  = sum(1 for r in self.results if r["status"] == "error")

            if total == 0:
                self.parent.after(0, lambda: self._set_progress_mode(0))
                self.parent.after(0, lambda: self._log(
                    "\n⚠️  No se encontraron archivos con los filtros indicados."
                ))
            else:
                summary = (
                    f"\n{'─' * 48}\n"
                    f"  Migración finalizada — {total} archivo(s)\n"
                    f"  ✅  Nuevos:       {ok}\n"
                    f"  🔄  Actualizados: {updated}\n"
                    f"  ⏭️  Saltados:     {skipped}\n"
                    f"  ❌  Errores:      {errors}\n"
                    f"{'─' * 48}"
                )
                self.parent.after(0, lambda: self._log(summary))
                self.parent.after(0, lambda: self._update_progress(total, total))

        except FileNotFoundError as e:
            self.parent.after(0, self.progress.stop)
            self.parent.after(0, lambda: messagebox.showerror("Directorio no encontrado", str(e)))
        except Exception as e:
            self.parent.after(0, self.progress.stop)
            self.parent.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _export(self, fmt):
        if not self.results:
            messagebox.showinfo("Sin datos", "Primero realiza una migración.")
            return
        path = auto_export(self.results, "migration", fmt)
        messagebox.showinfo("Exportado", f"Guardado en:\n{path}")
