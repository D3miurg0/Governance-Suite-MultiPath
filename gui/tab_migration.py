"""
Governance-Suite — Tab GUI: Migración de archivos (Multi-Path - CustomTkinter)
Permite configurar N pares Origen→Destino y ejecutarlos en paralelo o secuencial.
Soporta filtro por año o rango de fechas de modificación.

Cambios issue #3:
  - Nuevo checkbox “Usar Robocopy” con campo /MT:{n}.
  - En modo Robocopy el progreso se muestra en el log línea a línea y la
    barra avanza en modo indeterminado (robocopy no reporta total de archivos
    al inicio); al terminar se pasa a modo determinado con el resumen.
  - En modo Robocopy se habilita campo “Log Robocopy” para definir carpeta
    donde guardar el .log de robocopy.
"""
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from threading import Thread, Lock
from datetime import datetime
from core.migration import migrate_multi_paths, rollback_migration
from core.exporter import auto_export


# ---------------------------------------------------------------------------
# Fila de un par Origen → Destino
# ---------------------------------------------------------------------------

class _PathRow:
    """Widget compuesto que representa un par Origen / Destino en CustomTkinter."""

    def __init__(self, container, idx: int, colors: dict, on_remove):
        self.colors = c = colors
        self.idx = idx

        self.frame = ctk.CTkFrame(container, fg_color=c["bg"], corner_radius=0)
        self.frame.pack(fill="x", padx=4, pady=2)

        self.lbl_idx = ctk.CTkLabel(
            self.frame, text=f"#{idx + 1}", width=30, anchor="e",
            text_color=c["fg"], font=ctk.CTkFont("Segoe UI", 11)
        )
        self.lbl_idx.pack(side="left")

        self.src_var = ctk.StringVar()
        self.src_entry = ctk.CTkEntry(
            self.frame, textvariable=self.src_var, width=280,
            fg_color=c["surface"], text_color=c["fg"], border_width=0
        )
        self.src_entry.pack(side="left", padx=(6, 2))

        self.btn_browse_src = ctk.CTkButton(
            self.frame, text="…", fg_color=c["surface"], text_color=c["fg"],
            hover_color=c["accent"], width=28, height=28,
            command=lambda: self._browse(self.src_var)
        )
        self.btn_browse_src.pack(side="left")

        self.lbl_arrow = ctk.CTkLabel(
            self.frame, text="→", text_color=c["fg"], width=20
        )
        self.lbl_arrow.pack(side="left", padx=4)

        self.dst_var = ctk.StringVar()
        self.dst_entry = ctk.CTkEntry(
            self.frame, textvariable=self.dst_var, width=280,
            fg_color=c["surface"], text_color=c["fg"], border_width=0
        )
        self.dst_entry.pack(side="left", padx=(2, 2))

        self.btn_browse_dst = ctk.CTkButton(
            self.frame, text="…", fg_color=c["surface"], text_color=c["fg"],
            hover_color=c["accent"], width=28, height=28,
            command=lambda: self._browse(self.dst_var)
        )
        self.btn_browse_dst.pack(side="left")

        self.btn_remove = ctk.CTkButton(
            self.frame, text="✕", fg_color=c["bg"], text_color="#f38ba8",
            hover_color=c["surface"], width=28, height=28,
            command=lambda: on_remove(self)
        )
        self.btn_remove.pack(side="left", padx=(6, 0))

    def _browse(self, var: ctk.StringVar):
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    def get_pair(self):
        src = self.src_var.get().strip()
        dst = self.dst_var.get().strip()
        return (src, dst) if src and dst else None

    def destroy(self):
        self.frame.destroy()

    def update_index(self, idx: int):
        self.idx = idx
        self.lbl_idx.configure(text=f"#{idx + 1}")


# ---------------------------------------------------------------------------
# Tab principal
# ---------------------------------------------------------------------------

class MigrationTab:
    def __init__(self, parent, colors):
        self.parent = parent
        self.colors = colors
        self.results: dict = {}
        self._rows: list[_PathRow] = []
        self._lock = Lock()
        self._global_done = 0
        self._global_total = 0
        self._per_path_totals: dict[int, int] = {}

    def build(self):
        c = self.colors
        frame = self.parent
        pad = {"padx": 12, "pady": 4}

        # ── Rutas ───────────────────────────────────────────────────────────────
        paths_frame = ctk.CTkFrame(frame, fg_color=c["bg"])
        paths_frame.pack(fill="x", padx=12, pady=(8, 2))

        ctk.CTkLabel(
            paths_frame, text=" Rutas de migración (Multi-Path) ",
            text_color=c["accent"], font=ctk.CTkFont("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=6, pady=(4, 2))

        self.scroll_frame = ctk.CTkScrollableFrame(
            paths_frame, height=120, fg_color=c["bg"],
            scrollbar_button_color=c["surface"],
            scrollbar_button_hover_color=c["accent"]
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=4, pady=4)

        add_row_frame = ctk.CTkFrame(paths_frame, fg_color=c["bg"])
        add_row_frame.pack(fill="x", padx=4, pady=(2, 4))
        ctk.CTkButton(
            add_row_frame, text="+ Agregar ruta", fg_color=c["surface"],
            text_color=c["fg"], hover_color=c["accent"],
            font=ctk.CTkFont("Segoe UI", 11), width=120,
            command=self._add_row
        ).pack(side="left", padx=4)
        self._add_row()

        # ── Modo de ejecución ──────────────────────────────────────────────
        mode_frame = ctk.CTkFrame(frame, fg_color=c["bg"])
        mode_frame.pack(fill="x", **pad)

        self.parallel_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            mode_frame, text="Ejecutar rutas en paralelo",
            variable=self.parallel_var,
            text_color=c["fg"], fg_color=c["accent"], hover_color=c["surface"]
        ).pack(side="left", padx=8)

        # ── Filtro por fecha ────────────────────────────────────────────────
        date_frame = ctk.CTkFrame(frame, fg_color=c["surface"], corner_radius=8)
        date_frame.pack(fill="x", padx=12, pady=(6, 2))

        ctk.CTkLabel(
            date_frame, text=" Filtro por fecha de modificación ",
            text_color=c["accent"], font=ctk.CTkFont("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=10, pady=(6, 2))

        year_row = ctk.CTkFrame(date_frame, fg_color=c["surface"])
        year_row.pack(fill="x", padx=8, pady=3)
        self.year_enabled = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            year_row, text="Solo año:", variable=self.year_enabled,
            text_color=c["fg"], fg_color=c["accent"], hover_color=c["surface"],
            command=self._toggle_date_fields
        ).pack(side="left", padx=8)
        self.year_var = ctk.StringVar(value=str(datetime.now().year))
        self.year_entry = ctk.CTkEntry(
            year_row, textvariable=self.year_var, width=80,
            fg_color=c["bg"], text_color=c["fg"], border_width=0, state="disabled"
        )
        self.year_entry.pack(side="left", padx=6)

        range_row = ctk.CTkFrame(date_frame, fg_color=c["surface"])
        range_row.pack(fill="x", padx=8, pady=(0, 6))
        self.range_enabled = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            range_row, text="Rango:", variable=self.range_enabled,
            text_color=c["fg"], fg_color=c["accent"], hover_color=c["surface"],
            command=self._toggle_date_fields
        ).pack(side="left", padx=8)
        ctk.CTkLabel(
            range_row, text="Desde (YYYY-MM-DD):",
            text_color=c["fg"], font=ctk.CTkFont("Segoe UI", 11)
        ).pack(side="left", padx=(12, 2))
        self.date_from_var = ctk.StringVar()
        self.date_from_entry = ctk.CTkEntry(
            range_row, textvariable=self.date_from_var, width=110,
            fg_color=c["bg"], text_color=c["fg"], border_width=0, state="disabled"
        )
        self.date_from_entry.pack(side="left", padx=4)
        ctk.CTkLabel(
            range_row, text="Hasta:",
            text_color=c["fg"], font=ctk.CTkFont("Segoe UI", 11)
        ).pack(side="left", padx=(8, 2))
        self.date_to_var = ctk.StringVar()
        self.date_to_entry = ctk.CTkEntry(
            range_row, textvariable=self.date_to_var, width=110,
            fg_color=c["bg"], text_color=c["fg"], border_width=0, state="disabled"
        )
        self.date_to_entry.pack(side="left", padx=4)

        # ── Opciones generales ────────────────────────────────────────────
        opts = ctk.CTkFrame(frame, fg_color=c["bg"])
        opts.pack(fill="x", **pad)
        self.verify_var    = ctk.BooleanVar(value=True)
        self.overwrite_var = ctk.BooleanVar(value=False)
        self.sync_var      = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            opts, text="Verificar integridad", variable=self.verify_var,
            text_color=c["fg"], fg_color=c["accent"], hover_color=c["surface"]
        ).pack(side="left", padx=8)
        ctk.CTkCheckBox(
            opts, text="Sobrescribir existentes", variable=self.overwrite_var,
            text_color=c["fg"], fg_color=c["accent"], hover_color=c["surface"]
        ).pack(side="left", padx=8)
        ctk.CTkCheckBox(
            opts, text="Solo actualizar más nuevos", variable=self.sync_var,
            text_color=c["fg"], fg_color=c["accent"], hover_color=c["surface"]
        ).pack(side="left", padx=8)

        # ── Opciones Robocopy (issue #3) ──────────────────────────────────
        rc_frame = ctk.CTkFrame(frame, fg_color=c["surface"], corner_radius=8)
        rc_frame.pack(fill="x", padx=12, pady=(4, 2))

        rc_top = ctk.CTkFrame(rc_frame, fg_color=c["surface"])
        rc_top.pack(fill="x", padx=8, pady=(6, 2))

        self.robocopy_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            rc_top,
            text="🚀  Usar Robocopy  (recomendado para volúmenes > 1 TB)",
            variable=self.robocopy_var,
            text_color=c["accent"], fg_color=c["accent"], hover_color=c["surface"],
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            command=self._toggle_robocopy_fields,
        ).pack(side="left", padx=4)

        rc_opts = ctk.CTkFrame(rc_frame, fg_color=c["surface"])
        rc_opts.pack(fill="x", padx=8, pady=(2, 6))

        ctk.CTkLabel(
            rc_opts, text="/MT (hilos):",
            text_color=c["fg"], font=ctk.CTkFont("Segoe UI", 11)
        ).pack(side="left", padx=(4, 2))
        self.rc_threads_var = ctk.StringVar(value="8")
        self.rc_threads_entry = ctk.CTkEntry(
            rc_opts, textvariable=self.rc_threads_var, width=50,
            fg_color=c["bg"], text_color=c["fg"], border_width=0, state="disabled"
        )
        self.rc_threads_entry.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(
            rc_opts, text="Log Robocopy:",
            text_color=c["fg"], font=ctk.CTkFont("Segoe UI", 11)
        ).pack(side="left", padx=(4, 2))
        self.rc_log_var = ctk.StringVar(value=r"C:\Temp\RobocopyLogs")
        self.rc_log_entry = ctk.CTkEntry(
            rc_opts, textvariable=self.rc_log_var, width=200,
            fg_color=c["bg"], text_color=c["fg"], border_width=0, state="disabled"
        )
        self.rc_log_entry.pack(side="left", padx=(0, 4))
        self.rc_log_browse = ctk.CTkButton(
            rc_opts, text="…", fg_color=c["surface"], text_color=c["fg"],
            hover_color=c["accent"], width=28, height=28, state="disabled",
            command=lambda: self.rc_log_var.set(
                filedialog.askdirectory() or self.rc_log_var.get()
            )
        )
        self.rc_log_browse.pack(side="left")

        # Flags extra (MIR, MOVE, etc.)
        ctk.CTkLabel(
            rc_opts, text="Flags extra:",
            text_color=c["fg"], font=ctk.CTkFont("Segoe UI", 11)
        ).pack(side="left", padx=(12, 2))
        self.rc_flags_var = ctk.StringVar(value="")
        self.rc_flags_entry = ctk.CTkEntry(
            rc_opts, textvariable=self.rc_flags_var, width=160,
            fg_color=c["bg"], text_color=c["fg"], border_width=0, state="disabled",
            placeholder_text="Ej: /MIR /XD Temp"
        )
        self.rc_flags_entry.pack(side="left", padx=4)

        # ── Botón iniciar ──────────────────────────────────────────────────
        self._start_btn = ctk.CTkButton(
            frame, text="  ▶  Iniciar migración",
            fg_color=c["accent"], text_color="#1e1e2e",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            hover_color="#74c7ec",
            command=self._start
        )
        self._start_btn.pack(pady=8)

        # ── Progreso global ────────────────────────────────────────────────
        pb_frame = ctk.CTkFrame(frame, fg_color=c["bg"])
        pb_frame.pack(fill="x", padx=12, pady=(0, 2))
        self.progress = ctk.CTkProgressBar(
            pb_frame, mode="determinate",
            fg_color=c["surface"], progress_color=c["accent"]
        )
        self.progress.pack(side="left", fill="x", expand=True)
        self.progress.set(0)
        self.progress_label = ctk.CTkLabel(
            pb_frame, text="", text_color=c["fg"],
            font=ctk.CTkFont("Segoe UI", 11), width=150, anchor="e"
        )
        self.progress_label.pack(side="left", padx=(6, 0))

        # ── Log ─────────────────────────────────────────────────────────────
        self.log = tk.Text(
            frame, height=14, bg=c["surface"], fg=c["fg"],
            font=("Consolas", 9), relief="flat", state="disabled"
        )
        self.log.pack(fill=tk.BOTH, expand=True, padx=12)
        self.log.tag_configure("ok",       foreground="#a6e3a1")
        self.log.tag_configure("error",    foreground="#f38ba8")
        self.log.tag_configure("skipped",  foreground="#a6adc8")
        self.log.tag_configure("updated",  foreground="#89b4fa")
        self.log.tag_configure("header",   foreground="#cba6f7",
                               font=("Consolas", 9, "bold"))
        self.log.tag_configure("robocopy", foreground="#f9e2af")

        # ── Exportar / Rollback ───────────────────────────────────────────
        btns = ctk.CTkFrame(frame, fg_color=c["bg"])
        btns.pack(fill="x", padx=12, pady=6)
        for fmt in ("CSV", "Excel", "JSON"):
            ctk.CTkButton(
                btns, text=f"Exportar {fmt}", fg_color=c["surface"],
                text_color=c["fg"], hover_color=c["accent"], width=110,
                command=lambda f=fmt.lower(): self._export(f)
            ).pack(side="left", padx=4)
        ctk.CTkButton(
            btns, text="⏪ Rollback desde Log", fg_color=c["bg"],
            text_color="#f38ba8", hover_color=c["surface"], width=150,
            border_width=1, border_color="#f38ba8",
            command=self._gui_rollback
        ).pack(side="right", padx=12)

    # ------------------------------------------------------------------
    # Gestión de filas
    # ------------------------------------------------------------------

    def _add_row(self):
        idx = len(self._rows)
        row = _PathRow(self.scroll_frame, idx, self.colors, self._remove_row)
        self._rows.append(row)

    def _remove_row(self, row: "_PathRow"):
        if len(self._rows) == 1:
            messagebox.showwarning("Atención", "Debe quedar al menos una ruta.")
            return
        self._rows.remove(row)
        row.destroy()
        for i, r in enumerate(self._rows):
            r.update_index(i)

    # ------------------------------------------------------------------
    # Toggle campos Robocopy (issue #3)
    # ------------------------------------------------------------------

    def _toggle_robocopy_fields(self):
        """Habilita/deshabilita los campos de Robocopy según el checkbox."""
        state = "normal" if self.robocopy_var.get() else "disabled"
        self.rc_threads_entry.configure(state=state)
        self.rc_log_entry.configure(state=state)
        self.rc_log_browse.configure(state=state)
        self.rc_flags_entry.configure(state=state)

    # ------------------------------------------------------------------
    # Helpers de fecha
    # ------------------------------------------------------------------

    def _toggle_date_fields(self):
        year_state  = "normal" if self.year_enabled.get()  else "disabled"
        range_state = "normal" if self.range_enabled.get() else "disabled"
        self.year_entry.configure(state=year_state)
        self.date_from_entry.configure(state=range_state)
        self.date_to_entry.configure(state=range_state)

    def _parse_date_inputs(self):
        year = date_from = date_to = None
        fmt = "%Y-%m-%d"
        if self.year_enabled.get():
            raw = self.year_var.get().strip()
            if not raw.isdigit() or not (1990 <= int(raw) <= datetime.now().year + 1):
                raise ValueError(f"Año inválido: '{raw}'.")
            year = int(raw)
        if self.range_enabled.get():
            raw_from = self.date_from_var.get().strip()
            raw_to   = self.date_to_var.get().strip()
            if raw_from:
                try:
                    date_from = datetime.strptime(raw_from, fmt)
                except ValueError:
                    raise ValueError(f"Fecha 'Desde' inválida: '{raw_from}'.")
            if raw_to:
                try:
                    date_to = datetime.strptime(raw_to, fmt).replace(
                        hour=23, minute=59, second=59)
                except ValueError:
                    raise ValueError(f"Fecha 'Hasta' inválida: '{raw_to}'.")
            if date_from and date_to and date_from > date_to:
                raise ValueError("'Desde' no puede ser mayor que 'Hasta'.")
        return year, date_from, date_to

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _log(self, msg, tag=None):
        self.log.configure(state="normal")
        if tag:
            self.log.insert(tk.END, msg + "\n", tag)
        else:
            self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    # ------------------------------------------------------------------
    # Progreso
    # ------------------------------------------------------------------

    def _set_scanning_mode(self):
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        self.progress_label.configure(text="Escaneando...")

    def _set_progress_mode(self, total):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        if total == 0:
            self.progress.set(0)
            self.progress_label.configure(text="Sin archivos")
        else:
            self.progress.set(0)
            self.progress_label.configure(text=f"0 / {total}  (0%)")

    def _update_progress(self, done, total):
        pct = done / total if total else 0
        self.progress.set(pct)
        self.progress_label.configure(text=f"{done} / {total}  ({int(pct*100)}%)")

    # ------------------------------------------------------------------
    # Flujo principal
    # ------------------------------------------------------------------

    def _start(self):
        paths = [r.get_pair() for r in self._rows]
        paths = [p for p in paths if p is not None]
        if not paths:
            messagebox.showwarning("Faltan datos", "Agrega al menos un par Origen/Destino.")
            return
        incomplete = [
            r.idx + 1 for r in self._rows
            if r.get_pair() is None
            and (r.src_var.get().strip() or r.dst_var.get().strip())
        ]
        if incomplete:
            messagebox.showwarning(
                "Rutas incompletas",
                f"Las rutas #{', #'.join(map(str, incomplete))} tienen campos vacíos."
            )
            return
        try:
            year, date_from, date_to = self._parse_date_inputs()
        except ValueError as e:
            messagebox.showwarning("Filtro de fecha inválido", str(e))
            return

        # Robocopy: validar hilos
        use_robocopy = self.robocopy_var.get()
        rc_threads   = 8
        rc_log_dir   = None
        rc_flags     = None
        if use_robocopy:
            try:
                rc_threads = int(self.rc_threads_var.get().strip() or "8")
                if not (1 <= rc_threads <= 128):
                    raise ValueError
            except ValueError:
                messagebox.showwarning(
                    "Hilos inválidos",
                    "/MT debe ser un número entre 1 y 128."
                )
                return
            rc_log_dir = self.rc_log_var.get().strip() or None
            raw_flags  = self.rc_flags_var.get().strip()
            rc_flags   = raw_flags.split() if raw_flags else None

        self.results = {}
        self._global_done  = 0
        self._global_total = 0
        self._per_path_totals = {}
        self._start_btn.configure(state="disabled")

        mode = "paralelo" if self.parallel_var.get() else "secuencial"
        mode_tag = " [ROBOCOPY]" if use_robocopy else " [Python]"
        self._log(f"{'─' * 50}", "header")
        self._log(
            f"Iniciando migración de {len(paths)} ruta(s) [{mode}]{mode_tag}",
            "header"
        )
        for i, (src, dst) in enumerate(paths):
            self._log(f"  #{i+1}  {src}  →  {dst}")
        if use_robocopy:
            self._log(
                f"  Robocopy: /MT:{rc_threads}  log→{rc_log_dir or 'sin log'}"
                + (f"  flags: {' '.join(rc_flags)}" if rc_flags else ""),
                "robocopy"
            )
        if year:
            self._log(f"  Filtro: año {year}")
        if date_from or date_to:
            self._log(f"  Filtro: {date_from or '—'} → {date_to or '—'}")

        self._set_scanning_mode()
        Thread(
            target=self._worker,
            args=(paths, year, date_from, date_to,
                  use_robocopy, rc_threads, rc_log_dir, rc_flags),
            daemon=True
        ).start()

    def _worker(
        self, paths, year, date_from, date_to,
        use_robocopy, rc_threads, rc_log_dir, rc_flags
    ):
        """Hilo principal de migración multi-path."""
        first_file_seen = [False]
        rc_line_count   = [0]

        def cb(path_idx, src, done, total, r):
            with self._lock:
                # ── Modo Robocopy: progreso por líneas de stdout ────────
                if use_robocopy:
                    line = r.get("line", "") if isinstance(r, dict) else str(r)
                    if line:
                        rc_line_count[0] += 1
                        # Mostrar líneas relevantes (archivos copiados) en el log
                        # Robocopy prefija archivos copiados con el nombre de archivo
                        # Omitir líneas de encabezado / separadores
                        stripped = line.strip()
                        if stripped and not stripped.startswith("-") and len(stripped) > 4:
                            self.parent.after(
                                0, lambda l=stripped: self._log(f"  ▸ {l}", "robocopy")
                            )
                        # La barra permanece indeterminada durante Robocopy
                        self.parent.after(
                            0, lambda n=rc_line_count[0]: self.progress_label.configure(
                                text=f"Robocopy… {n} líneas"
                            )
                        )
                    return

                # ── Modo Python: progreso determinado ────────────────────
                if not first_file_seen[0]:
                    first_file_seen[0] = True
                    total_all = sum(self._per_path_totals.values())
                    self.parent.after(0, lambda t=total_all: self._set_progress_mode(t))

                self._per_path_totals[path_idx] = max(
                    self._per_path_totals.get(path_idx, 0), total
                )
                self._global_done += 1
                done_g = self._global_done
                total_g = sum(self._per_path_totals.values())
                self.parent.after(
                    0, lambda d=done_g, t=total_g: self._update_progress(d, t)
                )

                # Tag según resultado
                status = r.get("status", "")
                tag = {"ok": "ok", "updated": "updated",
                       "skipped": "skipped", "error": "error"}.get(status, None)
                src_file = r.get("src", "")
                if status == "error":
                    msg = f"  ❌ ERR  {src_file}  |  {r.get('error', '')}"
                elif status == "skipped":
                    msg = f"  ⏭ SKIP {src_file}"
                elif status in ("ok", "updated"):
                    msg = f"  ✔ {status.upper():7} {src_file}"
                else:
                    msg = f"  {src_file}"
                self.parent.after(0, lambda m=msg, t=tag: self._log(m, t))

        try:
            self.results = migrate_multi_paths(
                paths=paths,
                verify=self.verify_var.get(),
                overwrite=self.overwrite_var.get(),
                sync_only=self.sync_var.get(),
                parallel_paths=self.parallel_var.get(),
                progress_callback=cb,
                date_from=date_from,
                date_to=date_to,
                year=year,
                use_robocopy=use_robocopy,
                robocopy_threads=rc_threads,
                robocopy_log_dir=rc_log_dir,
                robocopy_extra_flags=rc_flags,
            )
        except Exception as exc:
            self.parent.after(
                0, lambda e=str(exc): self._log(f"❌ Error crítico: {e}", "error")
            )
        finally:
            self.parent.after(0, self._on_done)

    def _on_done(self):
        """Llamado en el hilo principal al terminar la migración."""
        # Si estaba en modo indeterminado (Robocopy), parar y poner a 100%
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(1.0)

        use_robocopy = self.robocopy_var.get()
        if use_robocopy:
            # Resumen agregado desde los resultados Robocopy
            copied = skipped = failed = 0
            for results_list in self.results.values():
                for r in results_list:
                    copied  += r.get("files_copied",  0)
                    skipped += r.get("files_skipped", 0)
                    failed  += r.get("files_failed",  0)
            self._log(
                f"Robocopy finalizado — ✔ {copied} copiados  "
                f"⏭ {skipped} omitidos  ❌ {failed} fallidos",
                "header"
            )
            self.progress_label.configure(
                text=f"✔ {copied} | ⏭ {skipped} | ❌ {failed}"
            )
        else:
            all_results = [
                r for results in self.results.values() for r in results
            ]
            ok      = sum(1 for r in all_results if r["status"] == "ok")
            updated = sum(1 for r in all_results if r["status"] == "updated")
            skipped = sum(1 for r in all_results if r["status"] == "skipped")
            errors  = sum(1 for r in all_results if r["status"] == "error")
            self._log(
                f"Completado — ✔ {ok} nuevos  ↺ {updated} actualizados  "
                f"⏭ {skipped} omitidos  ❌ {errors} errores",
                "header"
            )
            self.progress_label.configure(
                text=f"✔ {ok + updated} | ⏭ {skipped} | ❌ {errors}"
            )

        self._start_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Exportar / Rollback
    # ------------------------------------------------------------------

    def _export(self, fmt: str):
        if not self.results:
            messagebox.showinfo("Sin datos", "Ejecuta una migración primero.")
            return
        flat = [r for v in self.results.values() for r in v]
        try:
            auto_export(flat, fmt)
            self._log(f"Exportado a {fmt.upper()}", "ok")
        except Exception as e:
            self._log(f"Error exportando: {e}", "error")

    def _gui_rollback(self):
        log_path = filedialog.askopenfilename(
            title="Seleccionar log JSON de migración",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")]
        )
        if not log_path:
            return
        if not messagebox.askyesno(
            "Confirmar Rollback",
            "Esto eliminará los archivos copiados en destino.\n¿Continuar?"
        ):
            return
        try:
            res = rollback_migration(log_path)
            self._log(
                f"Rollback: {res['deleted']} eliminados, "
                f"{res['not_found']} no encontrados, {res['errors']} errores",
                "ok"
            )
        except Exception as e:
            self._log(f"Error en rollback: {e}", "error")
