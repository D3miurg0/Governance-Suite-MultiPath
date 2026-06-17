"""
Governance-Suite — Tab GUI: Migración de archivos (Multi-Path - CustomTkinter)
Permite configurar N pares Origen→Destino y ejecutarlos en paralelo o secuencial.
Soporta filtro por año o rango de fechas de modificación.
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

        # Número de ruta
        self.lbl_idx = ctk.CTkLabel(
            self.frame, text=f"#{idx + 1}", width=30, anchor="e",
            text_color=c["fg"], font=ctk.CTkFont("Segoe UI", 11)
        )
        self.lbl_idx.pack(side="left")

        # Origen
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

        # Flecha separadora
        self.lbl_arrow = ctk.CTkLabel(
            self.frame, text="→", text_color=c["fg"], width=20
        )
        self.lbl_arrow.pack(side="left", padx=4)

        # Destino
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

        # Botón eliminar
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
        """Devuelve (src, dst) o None si alguno está vacío."""
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
        # Contadores globales para progreso multi-path
        self._global_done = 0
        self._global_total = 0
        # Totales por ruta (para calcular el global antes de empezar)
        self._per_path_totals: dict[int, int] = {}

    def build(self):
        c = self.colors
        frame = self.parent
        pad = {"padx": 12, "pady": 4}

        # ── Sección de rutas ──────────────────────────────────────────
        paths_frame = ctk.CTkFrame(frame, fg_color=c["bg"])
        paths_frame.pack(fill="x", padx=12, pady=(8, 2))

        ctk.CTkLabel(
            paths_frame, text=" Rutas de migración (Multi-Path) ", text_color=c["accent"],
            font=ctk.CTkFont("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=6, pady=(4, 2))

        # CTkScrollableFrame reemplaza Canvas + Scrollbar manual
        self.scroll_frame = ctk.CTkScrollableFrame(
            paths_frame, height=120, fg_color=c["bg"],
            scrollbar_button_color=c["surface"],
            scrollbar_button_hover_color=c["accent"]
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Botón agregar ruta
        add_row_frame = ctk.CTkFrame(paths_frame, fg_color=c["bg"])
        add_row_frame.pack(fill="x", padx=4, pady=(2, 4))
        
        self.btn_add = ctk.CTkButton(
            add_row_frame, text="+ Agregar ruta", fg_color=c["surface"], text_color=c["fg"],
            hover_color=c["accent"], font=ctk.CTkFont("Segoe UI", 11), width=120,
            command=self._add_row
        )
        self.btn_add.pack(side="left", padx=4)

        # Agregar la primera fila por defecto
        self._add_row()

        # ── Modo de ejecución ─────────────────────────────────────────
        mode_frame = ctk.CTkFrame(frame, fg_color=c["bg"])
        mode_frame.pack(fill="x", **pad)
        
        self.parallel_var = ctk.BooleanVar(value=True)
        self.chk_parallel = ctk.CTkCheckBox(
            mode_frame, text="Ejecutar rutas en paralelo",
            variable=self.parallel_var,
            text_color=c["fg"], fg_color=c["accent"], hover_color=c["surface"]
        )
        self.chk_parallel.pack(side="left", padx=8)

        # ── Filtro por fecha ──────────────────────────────────────────
        date_frame = ctk.CTkFrame(frame, fg_color=c["surface"], corner_radius=8)
        date_frame.pack(fill="x", padx=12, pady=(6, 2))

        ctk.CTkLabel(
            date_frame, text=" Filtro por fecha de modificación ", text_color=c["accent"],
            font=ctk.CTkFont("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=10, pady=(6, 2))

        year_row = ctk.CTkFrame(date_frame, fg_color=c["surface"])
        year_row.pack(fill="x", padx=8, pady=3)
        
        self.year_enabled = ctk.BooleanVar(value=False)
        self.chk_year = ctk.CTkCheckBox(
            year_row, text="Solo año:", variable=self.year_enabled,
            text_color=c["fg"], fg_color=c["accent"], hover_color=c["surface"],
            command=self._toggle_date_fields
        )
        self.chk_year.pack(side="left", padx=8)
        
        self.year_var = ctk.StringVar(value=str(datetime.now().year))
        self.year_entry = ctk.CTkEntry(
            year_row, textvariable=self.year_var, width=80,
            fg_color=c["bg"], text_color=c["fg"], border_width=0, state="disabled"
        )
        self.year_entry.pack(side="left", padx=6)

        range_row = ctk.CTkFrame(date_frame, fg_color=c["surface"])
        range_row.pack(fill="x", padx=8, pady=(0, 6))
        
        self.range_enabled = ctk.BooleanVar(value=False)
        self.chk_range = ctk.CTkCheckBox(
            range_row, text="Rango:", variable=self.range_enabled,
            text_color=c["fg"], fg_color=c["accent"], hover_color=c["surface"],
            command=self._toggle_date_fields
        )
        self.chk_range.pack(side="left", padx=8)
        
        ctk.CTkLabel(
            range_row, text="Desde (YYYY-MM-DD):", text_color=c["fg"],
            font=ctk.CTkFont("Segoe UI", 11)
        ).pack(side="left", padx=(12, 2))
        
        self.date_from_var = ctk.StringVar()
        self.date_from_entry = ctk.CTkEntry(
            range_row, textvariable=self.date_from_var, width=110,
            fg_color=c["bg"], text_color=c["fg"], border_width=0, state="disabled"
        )
        self.date_from_entry.pack(side="left", padx=4)
        
        ctk.CTkLabel(
            range_row, text="Hasta:", text_color=c["fg"],
            font=ctk.CTkFont("Segoe UI", 11)
        ).pack(side="left", padx=(8, 2))
        
        self.date_to_var = ctk.StringVar()
        self.date_to_entry = ctk.CTkEntry(
            range_row, textvariable=self.date_to_var, width=110,
            fg_color=c["bg"], text_color=c["fg"], border_width=0, state="disabled"
        )
        self.date_to_entry.pack(side="left", padx=4)

        # ── Opciones generales ────────────────────────────────────────
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

        # ── Botón iniciar ─────────────────────────────────────────────
        self._start_btn = ctk.CTkButton(
            frame, text="  ▶  Iniciar migración",
            fg_color=c["accent"], text_color="#1e1e2e",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            hover_color="#74c7ec",
            command=self._start
        )
        self._start_btn.pack(pady=8)

        # ── Progreso global ───────────────────────────────────────────
        pb_frame = ctk.CTkFrame(frame, fg_color=c["bg"])
        pb_frame.pack(fill="x", padx=12, pady=(0, 2))
        
        self.progress = ctk.CTkProgressBar(
            pb_frame, mode="determinate", fg_color=c["surface"], progress_color=c["accent"]
        )
        self.progress.pack(side="left", fill="x", expand=True)
        self.progress.set(0)
        
        self.progress_label = ctk.CTkLabel(
            pb_frame, text="", text_color=c["fg"],
            font=ctk.CTkFont("Segoe UI", 11), width=150, anchor="e"
        )
        self.progress_label.pack(side="left", padx=(6, 0))

        # ── Log ───────────────────────────────────────────────────────
        self.log = tk.Text(
            frame, height=14, bg=c["surface"], fg=c["fg"],
            font=("Consolas", 9), relief="flat", state="disabled"
        )
        self.log.pack(fill=tk.BOTH, expand=True, padx=12)

        # Color tags para el log
        self.log.tag_configure("ok",      foreground="#a6e3a1")
        self.log.tag_configure("error",   foreground="#f38ba8")
        self.log.tag_configure("skipped", foreground="#a6adc8")
        self.log.tag_configure("updated", foreground="#89b4fa")
        self.log.tag_configure("header",  foreground="#cba6f7", font=("Consolas", 9, "bold"))

        # ── Exportar ──────────────────────────────────────────────────
        btns = ctk.CTkFrame(frame, fg_color=c["bg"])
        btns.pack(fill="x", padx=12, pady=6)
        for fmt in ("CSV", "Excel", "JSON"):
            ctk.CTkButton(
                btns, text=f"Exportar {fmt}", fg_color=c["surface"], text_color=c["fg"],
                hover_color=c["accent"], width=110,
                command=lambda f=fmt.lower(): self._export(f)
            ).pack(side="left", padx=4)

        # Botón Rollback
        ctk.CTkButton(
            btns, text="⏪ Rollback desde Log", fg_color=c["bg"], text_color="#f38ba8",
            hover_color=c["surface"], width=150, border_width=1, border_color="#f38ba8",
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
        pct_int = int(pct * 100)
        self.progress_label.configure(text=f"{done} / {total}  ({pct_int}%)")

    # ------------------------------------------------------------------
    # Flujo principal
    # ------------------------------------------------------------------

    def _start(self):
        paths = [r.get_pair() for r in self._rows]
        paths = [p for p in paths if p is not None]
        if not paths:
            messagebox.showwarning("Faltan datos", "Agrega al menos un par Origen/Destino.")
            return
        # Validar que no haya filas con campos incompletos
        incomplete = [r.idx + 1 for r in self._rows if r.get_pair() is None
                      and (r.src_var.get().strip() or r.dst_var.get().strip())]
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

        self.results = {}
        self._global_done = 0
        self._global_total = 0
        self._per_path_totals = {}
        self._start_btn.configure(state="disabled")

        mode = "paralelo" if self.parallel_var.get() else "secuencial"
        self._log(f"{'─' * 50}", "header")
        self._log(f"Iniciando migración de {len(paths)} ruta(s) [{mode}]", "header")
        for i, (src, dst) in enumerate(paths):
            self._log(f"  #{i+1}  {src}  →  {dst}")
        if year:
            self._log(f"  Filtro: año {year}")
        if date_from or date_to:
            self._log(f"  Filtro: {date_from or '—'} → {date_to or '—'}")

        self._set_scanning_mode()
        Thread(
            target=self._worker,
            args=(paths, year, date_from, date_to),
            daemon=True
        ).start()

    def _worker(self, paths, year, date_from, date_to):
        """Hilo principal de migración multi-path."""
        first_file_seen = [False]

        def cb(path_idx, src, done, total, r):
            """Callback invocado por migrate_multi_paths para cada archivo."""
            with self._lock:
                # Primera vez que llega un callback → activar modo determinado
                if not first_file_seen[0]:
                    first_file_seen[0] = True
                    # Estimamos total global sumando totales conocidos
                    # (pueden actualizarse si las rutas van en paralelo)

                # Actualizar total conocido para esta ruta
                prev = self._per_path_totals.get(path_idx, 0)
                if total > prev:
                    self._global_total += (total - prev)
                    self._per_path_totals[path_idx] = total

                # Si done == 1 y es la primera de esta ruta, mostramos cabecera
                if done == 1:
                    self.parent.after(
                        0,
                        lambda s=src, t=total, i=path_idx: self._log(
                            f"\n📂 Ruta #{i+1} — {t} archivo(s): {s}", "header"
                        )
                    )
                    # Activar modo determinado la primera vez
                    if not first_file_seen[0] or self._global_total > 0:
                        self.parent.after(0, lambda gt=self._global_total:
                                          self._set_progress_mode(gt))

                self._global_done += 1
                gd = self._global_done
                gt = self._global_total

            status = r.get("status", "?")
            tag = status if status in ("ok", "error", "skipped", "updated") else None
            self.parent.after(
                0,
                lambda s=status, rr=r, tg=tag: self._log(
                    f"  [{s.upper():8}] {rr.get('src', '')}", tg
                )
            )
            self.parent.after(0, lambda d=gd, t=gt: self._update_progress(d, t))

        try:
            self.results = migrate_multi_paths(
                paths=paths,
                verify=self.verify_var.get(),
                overwrite=self.overwrite_var.get(),
                sync_only=self.sync_var.get(),
                parallel_paths=self.parallel_var.get(),
                progress_callback=cb,
                year=year,
                date_from=date_from,
                date_to=date_to,
            )

            # Resumen global
            all_r = [r for v in self.results.values() for r in v]
            total_f = len(all_r)
            ok      = sum(1 for r in all_r if r["status"] == "ok")
            updated = sum(1 for r in all_r if r["status"] == "updated")
            skipped = sum(1 for r in all_r if r["status"] == "skipped")
            errors  = sum(1 for r in all_r if r["status"] == "error")

            summary = (
                f"\n{'─' * 50}\n"
                f"  Migración finalizada — {len(paths)} ruta(s), {total_f} archivo(s)\n"
                f"  ✅  Nuevos:       {ok}\n"
                f"  🔄  Actualizados: {updated}\n"
                f"  ⏭️  Saltados:     {skipped}\n"
                f"  ❌  Errores:      {errors}\n"
                f"{'─' * 50}"
            )
            self.parent.after(0, lambda: self._log(summary, "header"))
            if total_f > 0:
                self.parent.after(0, lambda: self._update_progress(total_f, total_f))
                # Auto-guardado de log de migración para posible rollback
                try:
                    log_path = auto_export(all_r, "migration_log", "json")
                    self.parent.after(0, lambda: self._log(f"  Log automático guardado en:\n  {log_path}"))
                except Exception as e:
                    self.parent.after(0, lambda: self._log(f"  ⚠️ No se pudo guardar el log automático: {e}"))
            else:
                self.parent.after(0, lambda: self._set_progress_mode(0))
                self.parent.after(
                    0,
                    lambda: self._log("⚠️  No se encontraron archivos con los filtros indicados.")
                )

        except FileNotFoundError as e:
            self.parent.after(0, self.progress.stop)
            self.parent.after(0, lambda: messagebox.showerror("Directorio no encontrado", str(e)))
        except Exception as e:
            self.parent.after(0, self.progress.stop)
            self.parent.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.parent.after(0, lambda: self._start_btn.configure(state="normal"))

    def _export(self, fmt):
        if not self.results:
            messagebox.showinfo("Sin datos", "Primero realiza una migración.")
            return
        all_r = [r for v in self.results.values() for r in v]
        path = auto_export(all_r, "migration", fmt)
        messagebox.showinfo("Exportado", f"Guardado en:\n{path}")

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def _gui_rollback(self):
        log_path = filedialog.askopenfilename(
            title="Seleccionar Log de Migración para Rollback",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")]
        )
        if not log_path:
            return
            
        confirm = messagebox.askyesno(
            "Confirmar Rollback",
            f"¿Estás seguro de deshacer la migración registrada en este log?\n\n"
            f"Se eliminarán los archivos copiados en el destino.\n"
            f"Archivos sobreescritos (actualizados) también serán eliminados del destino de manera irreversible.\n\n"
            f"Log seleccionado: {log_path}"
        )
        if not confirm:
            return
            
        self._start_btn.configure(state="disabled")
        self._set_scanning_mode()
        
        self._log(f"\n{'─' * 50}", "header")
        self._log(f"Iniciando ROLLBACK desde: {log_path}", "header")
        
        Thread(
            target=self._rollback_worker,
            args=(log_path,),
            daemon=True
        ).start()

    def _rollback_worker(self, log_path: str):
        self._global_done = 0
        self._global_total = 0
        first_file_seen = [False]
        
        def cb(done, total, item):
            with self._lock:
                if not first_file_seen[0]:
                    first_file_seen[0] = True
                    self._global_total = total
                    self.parent.after(0, lambda gt=self._global_total: self._set_progress_mode(gt))
                
                self._global_done = done
                gd = self._global_done
                gt = self._global_total
            
            # Log de cada archivo en tiempo real
            dst = item.get("dst", "?")
            self.parent.after(
                0,
                lambda d=dst: self._log(f"  [DELETED] {d}", "error")
            )
            self.parent.after(0, lambda d=gd, t=gt: self._update_progress(d, t))

        try:
            results = rollback_migration(log_path, cb)
            
            summary = (
                f"\n{'─' * 50}\n"
                f"  Rollback finalizado\n"
                f"  ✅  Eliminados:      {results['deleted']}\n"
                f"  ⚠️  No encontrados:  {results['not_found']}\n"
                f"  ❌  Errores:         {results['errors']}\n"
                f"{'─' * 50}"
            )
            self.parent.after(0, lambda: self._log(summary, "header"))
            
        except Exception as e:
            self.parent.after(0, self.progress.stop)
            self.parent.after(0, lambda: messagebox.showerror("Error de Rollback", str(e)))
            self.parent.after(0, lambda: self._log(f"Error en Rollback: {e}", "error"))
        finally:
            self.parent.after(0, lambda: self._start_btn.configure(state="normal"))
            if self._global_total > 0:
                self.parent.after(0, lambda: self._update_progress(self._global_total, self._global_total))
            else:
                self.parent.after(0, lambda: self._set_progress_mode(0))
