"""Tkinter GUI frontend for the File-Manager tools (no external deps).

This is a lightweight, dependency-free fallback UI that exposes basic
Scan / Organize / Dedupe / Report / Undo actions using the existing
`file_manager` package.
"""
import threading
from pathlib import Path
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


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

    # Buttons
    btn_frame = ttk.Frame(frm)
    btn_frame.grid(row=4, column=0, columnspan=3, pady=(8,0), sticky="w")

    out_text = tk.Text(frm, width=100, height=20)
    out_text.grid(row=5, column=0, columnspan=3, pady=(8,0))

    def append(msg):
        out_text.insert(tk.END, str(msg) + "\n")
        out_text.see(tk.END)

    # import backend lazily so module import is fast
    from file_manager import scanner, organizer, deduper, reporter

    def on_scan_done(ok, payload):
        if not ok:
            append(f"Scan error: {payload}")
            return
        append(f"Scan completed: {len(payload)} items")
        try:
            append(json.dumps(payload[:5], indent=2))
        except Exception:
            pass

    def do_scan():
        paths = [p.strip() for p in src_var.get().split(',') if p.strip()]
        items = []
        for p in paths:
            for it in scanner.scan_paths([p], recursive=rec_var.get()):
                items.append(it)
        return items

    def on_organize_done(ok, payload):
        if not ok:
            append(f"Organize error: {payload}")
            return
        append(f"Organize completed: {len(payload)} actions")
        try:
            append(json.dumps(payload[:10], indent=2))
        except Exception:
            pass

    def do_organize():
        from file_manager import scanner as sc
        paths = [p.strip() for p in src_var.get().split(',') if p.strip()]
        items = []
        for p in paths:
            for it in sc.scan_paths([p], recursive=rec_var.get()):
                items.append(it)
        targ = Path(tgt_var.get() or '.')
        if by_var.get() == 'type':
            return organizer.organize_by_type(items, targ, dry_run=dry_var.get())
        return organizer.organize_by_date(items, targ, dry_run=dry_var.get())

    def on_dedupe_done(ok, payload):
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

    def on_report_done(ok, payload):
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
        if not ok:
            append(f"Undo error: {payload}")
            return
        append(f"Undo completed: {len(payload)} entries")
        try:
            append(json.dumps(payload[:10], indent=2))
        except Exception:
            pass

    def do_undo():
        logp = src_var.get().strip()
        return organizer.undo_moves(Path(logp), dry_run=dry_var.get())

    ttk.Button(btn_frame, text="Scan", command=lambda: _run_background(do_scan, on_scan_done)).grid(row=0, column=0)
    ttk.Button(btn_frame, text="Organize", command=lambda: _run_background(do_organize, on_organize_done)).grid(row=0, column=1)
    ttk.Button(btn_frame, text="Dedupe", command=lambda: _run_background(do_dedupe, on_dedupe_done)).grid(row=0, column=2)
    ttk.Button(btn_frame, text="Report", command=lambda: _run_background(do_report, on_report_done)).grid(row=0, column=3)
    ttk.Button(btn_frame, text="Undo", command=lambda: _run_background(do_undo, on_undo_done)).grid(row=0, column=4)

    return root


if __name__ == '__main__':
    app = build_ui()
    app.mainloop()
