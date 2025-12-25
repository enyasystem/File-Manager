"""Tkinter GUI frontend for the File-Manager tools (no external deps).

Lightweight UI exposing Scan / Organize / Dedupe / Report / Undo actions
from the `file_manager` package. Fixes: proper progress updates, button
disable while tasks run, and scan results saved to the target folder.
"""
import threading
from pathlib import Path
import json
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime


def _run_background(fn, on_done, *args, **kwargs):
    def _worker():
        try:
            res = fn(*args, **kwargs)
            root.after(0, lambda: on_done(True, res))
        except Exception as e:
            root.after(0, lambda: on_done(False, str(e)))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def build_ui():
    global root
    root = tk.Tk()
    root.title("File Manager (Tk)")

    frm = ttk.Frame(root, padding=10)
    frm.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frm, text="Source Paths (comma-separated):").grid(row=0, column=0, sticky="w")
    src_var = tk.StringVar()
    src_entry = ttk.Entry(frm, textvariable=src_var, width=80)
    src_entry.grid(row=0, column=1, sticky="ew")

    def browse_src():
        d = filedialog.askdirectory()
        if d:
            src_var.set(d)

    ttk.Button(frm, text="Browse", command=browse_src).grid(row=0, column=2)

    ttk.Label(frm, text="Target Root:").grid(row=1, column=0, sticky="w")
    tgt_var = tk.StringVar()
    tgt_entry = ttk.Entry(frm, textvariable=tgt_var, width=80)
    tgt_entry.grid(row=1, column=1, sticky="ew")

    def browse_tgt():
        d = filedialog.askdirectory()
        if d:
            tgt_var.set(d)

    ttk.Button(frm, text="Browse", command=browse_tgt).grid(row=1, column=2)

    dry_var = tk.BooleanVar(value=True)
    rec_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(frm, text="Dry run", variable=dry_var).grid(row=2, column=0, sticky="w")
    ttk.Checkbutton(frm, text="Recursive", variable=rec_var).grid(row=2, column=1, sticky="w")

    ttk.Label(frm, text="Organize by:").grid(row=3, column=0, sticky="w")
    by_var = tk.StringVar(value="type")
    by_cb = ttk.Combobox(frm, textvariable=by_var, values=["type", "date"], state="readonly", width=10)
    by_cb.grid(row=3, column=1, sticky="w")
    # Mode selector for organize operations
    ttk.Label(frm, text="Mode:").grid(row=3, column=2, sticky="w")
    mode_var = tk.StringVar(value="move")
    mode_cb = ttk.Combobox(frm, textvariable=mode_var, values=["move", "copy", "hardlink", "index"], state="readonly", width=10)
    mode_cb.grid(row=3, column=3, sticky="w")
    # Info / warning for selected mode
    mode_info_var = tk.StringVar(value="")
    mode_info_lbl = ttk.Label(frm, textvariable=mode_info_var, foreground="orange")
    mode_info_lbl.grid(row=4, column=3, sticky='w')

    def update_mode_info(*_):
        sel = mode_var.get()
        if sel == 'hardlink':
            mode_info_var.set('Hardlinks may fail across devices; fallback to copy')
        elif sel == 'index':
            mode_info_var.set('Index mode: generates index files (backend pending)')
        else:
            mode_info_var.set('')

    mode_var.trace_add('write', update_mode_info)
    update_mode_info()

    # Buttons
    btn_frame = ttk.Frame(frm)
    btn_frame.grid(row=4, column=0, columnspan=3, pady=(8, 0), sticky="w")

    # Preview controls: top-N and size buckets
    top_n_var = tk.IntVar(value=10)
    ttk.Label(frm, text="Top N:").grid(row=3, column=4, sticky='e')
    top_spin = ttk.Spinbox(frm, from_=1, to=100, textvariable=top_n_var, width=5)
    top_spin.grid(row=3, column=5, sticky='w')

    ttk.Label(frm, text="Size buckets (MB):").grid(row=4, column=4, sticky='e')
    small_mb_var = tk.IntVar(value=1)
    medium_mb_var = tk.IntVar(value=10)
    small_entry = ttk.Entry(frm, textvariable=small_mb_var, width=6)
    small_entry.grid(row=4, column=5, sticky='w')
    medium_entry = ttk.Entry(frm, textvariable=medium_mb_var, width=6)
    medium_entry.grid(row=4, column=6, sticky='w')

    # Date source for organize-by-date
    date_src_var = tk.StringVar(value='ctime')
    ttk.Label(frm, text='Date source:').grid(row=5, column=0, sticky='w')
    date_cb = ttk.Combobox(frm, textvariable=date_src_var, values=['ctime', 'mtime', 'exif'], state='readonly', width=10)
    date_cb.grid(row=5, column=1, sticky='w')

    out_text = tk.Text(frm, width=100, height=20)
    out_text.grid(row=5, column=0, columnspan=3, pady=(8, 0))

    progress = ttk.Progressbar(frm, mode='determinate', length=460)
    progress.grid(row=6, column=0, columnspan=2, pady=(8, 0), sticky='w')
    progress['value'] = 0
    progress['maximum'] = 100

    percent_var = tk.StringVar(value='')
    percent_label = ttk.Label(frm, textvariable=percent_var, width=6)
    percent_label.grid(row=6, column=2, pady=(8, 0), sticky='w')

    buttons = []

    def set_buttons_enabled(enabled: bool):
        for b in buttons:
            try:
                b.config(state='normal' if enabled else 'disabled')
            except Exception:
                pass

    def append(msg):
        out_text.insert(tk.END, str(msg) + "\n")
        out_text.see(tk.END)

    # import backend lazily so module import is fast
    from file_manager import scanner, organizer, deduper, reporter

    def start_progress(mode='indeterminate', maximum=None):
        try:
            if mode == 'determinate' and maximum:
                progress.config(mode='determinate', maximum=maximum)
                progress['value'] = 0
                percent_var.set('0%')
            else:
                progress.config(mode='indeterminate')
                progress.start(50)
                percent_var.set('')
        except Exception:
            pass

    def stop_progress():
        try:
            progress.stop()
        except Exception:
            pass
        try:
            # when stopping, if determinate show 100%
            if progress['mode'] == 'determinate' and progress['maximum']:
                percent_var.set('100%')
        except Exception:
            pass

    def on_scan_done(ok, payload):
        stop_progress()
        set_buttons_enabled(True)
        if not ok:
            append(f"Scan error: {payload}")
            return
        items = payload
        count = len(items)
        append(f"Scan completed: {count} items")
        try:
            append(json.dumps(items[:5], indent=2))
        except Exception:
            pass

        # Save scan results to target folder if specified
        try:
            tgt = Path(tgt_var.get() or '.')
            if not tgt.exists():
                tgt.mkdir(parents=True, exist_ok=True)
            stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            outp = tgt / f'fm_scan_{stamp}.json'
            with outp.open('w', encoding='utf-8') as f:
                json.dump(items, f, indent=2)
            append(f"Scan saved: {str(outp)}")
        except Exception as e:
            append(f"Failed to save scan: {e}")
        finally:
            # ensure percent shows 100% on done
            try:
                percent_var.set('100%')
            except Exception:
                pass

    def do_scan():
        paths = [p.strip() for p in src_var.get().split(',') if p.strip()]
        items = []
        # fast count pass to set progress maximum
        total = 0
        try:
            for p in paths:
                pp = Path(p)
                if pp.is_file():
                    total += 1
                elif pp.is_dir():
                    for _root, _dirs, files in os.walk(pp):
                        total += len(files)
        except Exception:
            total = 0

        try:
            if total > 0:
                root.after(0, lambda: start_progress('determinate', maximum=total))
            else:
                root.after(0, lambda: start_progress('indeterminate'))
        except Exception:
            pass

        done = 0
        for p in paths:
            for it in scanner.scan_paths([p], recursive=rec_var.get()):
                items.append(it)
                done += 1
                if total > 0:
                    try:
                        # update bar value
                        root.after(0, lambda v=done: progress.config(value=v))
                        # update percent label
                        pct = int(done / total * 100) if total else 0
                        root.after(0, lambda p=pct: percent_var.set(f"{p}%"))
                    except Exception:
                        pass
        return items

    def on_organize_done(ok, payload):
        stop_progress()
        set_buttons_enabled(True)
        if not ok:
            append(f"Organize error: {payload}")
            return
        try:
            # payload is a list of actions; last entry may be a log path
            if isinstance(payload, list) and payload and isinstance(payload[-1], dict) and 'log' in payload[-1]:
                logp = payload[-1]['log']
                append(f"Organize completed: {len(payload)-1} actions; log: {logp}")
                try:
                    append(json.dumps(payload[:-1][:10], indent=2))
                except Exception:
                    pass
            else:
                append(f"Organize completed: {len(payload)} actions")
                try:
                    append(json.dumps(payload[:10], indent=2))
                except Exception:
                    pass
        except Exception:
            append(str(payload))

    def do_organize():
        from file_manager import scanner as sc
        paths = [p.strip() for p in src_var.get().split(',') if p.strip()]
        items = []
        for p in paths:
            for it in sc.scan_paths([p], recursive=rec_var.get()):
                items.append(it)
        targ = Path(tgt_var.get() or '.')
        sel_mode = mode_var.get()
        if by_var.get() == 'type':
            return organizer.organize_by_type(items, targ, dry_run=dry_var.get(), mode=sel_mode)
        return organizer.organize_by_date(items, targ, dry_run=dry_var.get(), mode=sel_mode)

    # Preview/apply flow for organize: run a dry-run preview first, show modal,
    # then apply if user confirms.
    def show_preview_window(actions, title='Preview'):
        win = tk.Toplevel(root)
        win.title(title)
        win.transient(root)
        win.grab_set()

        ttk.Label(win, text=f"Operation: Organize (preview)").grid(row=0, column=0, sticky='w', padx=8, pady=(8,0))
        ttk.Label(win, text=f"Actions: {len(actions)}").grid(row=1, column=0, sticky='w', padx=8)
        try:
            from file_manager.utils import estimate_size, human_size
            size_bytes = estimate_size(actions)
            ttk.Label(win, text=f"Estimated disk usage: {human_size(size_bytes)}").grid(row=1, column=1, sticky='w', padx=8)
        except Exception:
            pass

        txt = tk.Text(win, width=100, height=20)
        txt.grid(row=2, column=0, padx=8, pady=8)
        try:
            txt.insert(tk.END, json.dumps(actions[:50], indent=2))
        except Exception:
            txt.insert(tk.END, str(actions[:50]))
        txt.config(state='disabled')

        # show top-N largest files (per-action) on the right
        try:
            from file_manager.utils import human_size
            sizes = []
            for a in actions:
                p = None
                if isinstance(a, dict):
                    p = a.get('src') or a.get('path') or a.get('dst')
                else:
                    p = a
                if not p:
                    continue
                try:
                    sp = Path(p)
                    if sp.exists() and sp.is_file():
                        sizes.append((sp.stat().st_size, str(sp)))
                except Exception:
                    continue
            sizes.sort(key=lambda x: x[0], reverse=True)
            topn = sizes[:top_n_var.get() if isinstance(top_n_var.get(), int) else 10]
            if topn:
                lbl_top = ttk.Label(win, text=f"Largest {len(topn)} files:")
                lbl_top.grid(row=2, column=1, sticky='nw', padx=8, pady=(0,8))
                top_txt = tk.Text(win, width=60, height=min(15, len(topn)))
                top_txt.grid(row=3, column=1, padx=8, pady=(0,8))
                try:
                    for sz, path in topn:
                        top_txt.insert(tk.END, f"{human_size(sz):>8}  {path}\n")
                except Exception:
                    top_txt.insert(tk.END, str(topn))
                top_txt.config(state='disabled')
            # also show bucket counts using size thresholds from GUI
            try:
                small_mb = int(small_mb_var.get())
                medium_mb = int(medium_mb_var.get())
                small_thresh = small_mb * 1024 * 1024
                medium_thresh = medium_mb * 1024 * 1024
                small_count = sum(1 for s, _ in sizes if s <= small_thresh)
                medium_count = sum(1 for s, _ in sizes if small_thresh < s <= medium_thresh)
                large_count = sum(1 for s, _ in sizes if s > medium_thresh)
                ttk.Label(win, text=f"Buckets (<= {small_mb}MB / {small_mb}-{medium_mb}MB / >{medium_mb}MB): {small_count} / {medium_count} / {large_count}").grid(row=4, column=1, sticky='w', padx=8)
            except Exception:
                pass
        except Exception:
            pass

        confirm_var = tk.BooleanVar(value=False)
        chk = ttk.Checkbutton(win, text="I understand this will move files when applied", variable=confirm_var)
        chk.grid(row=3, column=0, sticky='w', padx=8)

        decision = {'confirmed': False}

        def do_proceed():
            decision['confirmed'] = True
            win.destroy()

        def do_cancel():
            win.destroy()

        btn_frame = ttk.Frame(win)
        btn_frame.grid(row=4, column=0, sticky='e', padx=8, pady=(0,8))
        btn_proceed = ttk.Button(btn_frame, text='Proceed', command=do_proceed)
        btn_proceed.grid(row=0, column=0, padx=(0,8))
        btn_cancel = ttk.Button(btn_frame, text='Cancel', command=do_cancel)
        btn_cancel.grid(row=0, column=1)

        # disable proceed until confirmed
        def toggle_proceed(*_):
            try:
                btn_proceed.config(state='normal' if confirm_var.get() else 'disabled')
            except Exception:
                pass

        confirm_var.trace_add('write', toggle_proceed)
        toggle_proceed()

        root.wait_window(win)
        return decision['confirmed']

    def do_organize_preview():
        # identical to do_organize but force dry_run=True
        from file_manager import scanner as sc
        paths = [p.strip() for p in src_var.get().split(',') if p.strip()]
        items = []
        for p in paths:
            for it in sc.scan_paths([p], recursive=rec_var.get()):
                items.append(it)
        targ = Path(tgt_var.get() or '.')
        sel_mode = mode_var.get()
        if by_var.get() == 'type':
            return organizer.organize_by_type(items, targ, dry_run=True, mode=sel_mode)
        return organizer.organize_by_date(items, targ, dry_run=True, mode=sel_mode)

    def do_organize_apply():
        # perform actual organize (non-dry)
        from file_manager import scanner as sc
        paths = [p.strip() for p in src_var.get().split(',') if p.strip()]
        items = []
        for p in paths:
            for it in sc.scan_paths([p], recursive=rec_var.get()):
                items.append(it)
        targ = Path(tgt_var.get() or '.')
        sel_mode = mode_var.get()
        if by_var.get() == 'type':
            return organizer.organize_by_type(items, targ, dry_run=False, mode=sel_mode)
        return organizer.organize_by_date(items, targ, dry_run=False, mode=sel_mode)

    def on_organize_preview_done(ok, payload):
        # called after preview is ready
        set_buttons_enabled(True)
        stop_progress()
        if not ok:
            append(f"Organize preview error: {payload}")
            return
        actions = payload
        confirmed = show_preview_window(actions, title='Organize Preview')
        if not confirmed:
            append('Organize cancelled by user')
            return
        # user confirmed; run actual organize in background
        set_buttons_enabled(False)
        start_progress('indeterminate')
        _run_background(do_organize_apply, on_organize_done)

    def on_dedupe_done(ok, payload):
        stop_progress()
        set_buttons_enabled(True)
        if not ok:
            append(f"Dedupe error: {payload}")
            return
        try:
            groups = payload
            count = sum(1 for g in groups if len(g) > 1)
            append(f"Dedupe completed: {count} duplicate groups")
            append(json.dumps(groups, indent=2))
        except Exception:
            append(str(payload))

    def do_dedupe():
        paths = [p.strip() for p in src_var.get().split(',') if p.strip()]
        return deduper.find_duplicates(paths)

    # Dedupe preview/apply flow
    def do_dedupe_preview():
        paths = [p.strip() for p in src_var.get().split(',') if p.strip()]
        return deduper.find_duplicates(paths)

    def do_dedupe_apply(groups):
        # decide files to delete using default strategy
        to_delete = []
        try:
            from file_manager import deduper as dd
            for g in groups:
                to_delete.extend(dd.choose_to_delete(g, strategy='keep-first'))
            # perform safe delete (move to trash)
            res = dd.delete_files(to_delete, dry_run=False)
            return res
        except Exception as e:
            return str(e)

    def on_dedupe_preview_done(ok, payload):
        stop_progress()
        set_buttons_enabled(True)
        if not ok:
            append(f"Dedupe preview error: {payload}")
            return
        groups = payload
        # show preview modal
        confirmed = show_preview_window(groups, title='Dedupe Preview')
        if not confirmed:
            append('Dedupe cancelled by user')
            return
        # user confirmed: run deletion in background
        set_buttons_enabled(False)
        start_progress('indeterminate')
        _run_background(lambda: do_dedupe_apply(groups), lambda ok, p: append(json.dumps(p, indent=2) if ok else f"Dedupe apply error: {p}"))

    def on_report_done(ok, payload):
        stop_progress()
        set_buttons_enabled(True)
        if not ok:
            append(f"Report error: {payload}")
            return
        append(f"Report generated: {payload}")

    def do_report():
        paths = [p.strip() for p in src_var.get().split(',') if p.strip()]
        if not paths:
            return 'No scan.json provided'
        p = Path(paths[0])
        out = tgt_var.get() or 'report.json'
        if p.exists() and p.suffix == '.json':
            reporter.generate_report(str(p), out)
            return out
        return 'No valid scan.json provided'

    def on_undo_done(ok, payload):
        stop_progress()
        set_buttons_enabled(True)
        if not ok:
            append(f"Undo error: {payload}")
            return
        append(f"Undo completed: {len(payload)} entries")
        try:
            append(json.dumps(payload[:10], indent=2))
        except Exception:
            pass

    # Undo preview/apply flow
    def do_undo_preview():
        logp = src_var.get().strip()
        return organizer.undo_moves(Path(logp), dry_run=True)

    def do_undo_apply():
        logp = src_var.get().strip()
        return organizer.undo_moves(Path(logp), dry_run=False)

    def on_undo_preview_done(ok, payload):
        stop_progress()
        set_buttons_enabled(True)
        if not ok:
            append(f"Undo preview error: {payload}")
            return
        actions = payload
        confirmed = show_preview_window(actions, title='Undo Preview')
        if not confirmed:
            append('Undo cancelled by user')
            return
        # perform undo
        set_buttons_enabled(False)
        start_progress('indeterminate')
        _run_background(do_undo_apply, on_undo_done)

    def do_undo():
        logp = src_var.get().strip()
        return organizer.undo_moves(Path(logp), dry_run=dry_var.get())

    # buttons with wrappers that start progress and disable buttons while running
    b_scan = ttk.Button(btn_frame, text="Scan", command=lambda: (set_buttons_enabled(False), _run_background(do_scan, on_scan_done)))
    b_scan.grid(row=0, column=0)
    b_org = ttk.Button(btn_frame, text="Organize", command=lambda: (set_buttons_enabled(False), start_progress('indeterminate'), _run_background(do_organize_preview, on_organize_preview_done)))
    b_org.grid(row=0, column=1)
    b_ded = ttk.Button(btn_frame, text="Dedupe", command=lambda: (set_buttons_enabled(False), start_progress('indeterminate'), _run_background(do_dedupe_preview, on_dedupe_preview_done)))
    b_ded.grid(row=0, column=2)
    b_rep = ttk.Button(btn_frame, text="Report", command=lambda: (set_buttons_enabled(False), start_progress('indeterminate'), _run_background(do_report, on_report_done)))
    b_rep.grid(row=0, column=3)
    b_undo = ttk.Button(btn_frame, text="Undo", command=lambda: (set_buttons_enabled(False), start_progress('indeterminate'), _run_background(do_undo_preview, on_undo_preview_done)))
    b_undo.grid(row=0, column=4)

    buttons.extend([b_scan, b_org, b_ded, b_rep, b_undo])

    return root


if __name__ == '__main__':
    try:
        app = build_ui()
        app.mainloop()
    except KeyboardInterrupt:
        try:
            app.destroy()
        except Exception:
            pass
        print('\nGUI interrupted, exiting.')
