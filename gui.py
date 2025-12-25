"""Simple PySimpleGUI front-end for the File-Manager CLI utilities.

This is a lightweight prototype UI that calls into the existing
`file_manager` package. `PySimpleGUI` is imported inside `main()` so
the module can be imported without the dependency for tests.
"""
from pathlib import Path
import threading
import json
from typing import List


def _run_in_thread(window, event_key, func, *args, **kwargs):
    def _worker():
        try:
            res = func(*args, **kwargs)
            window.write_event_value(event_key, (True, res))
        except Exception as e:
            window.write_event_value(event_key, (False, str(e)))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def main():
    try:
        import PySimpleGUI as sg
    except Exception:
        raise RuntimeError("PySimpleGUI is required to run the GUI. Install with: pip install PySimpleGUI")

    from file_manager import scanner, organizer, deduper, reporter

    sg.theme("DefaultNoMoreNagging")

    layout = [
        [sg.Text("Source Paths (comma-separated):"), sg.Input(key="-PATHS-", size=(60,1)), sg.FolderBrowse(button_text="Browse")],
        [sg.Text("Target Root:"), sg.Input(key="-TARGET-", size=(60,1)), sg.FolderBrowse(button_text="Browse")],
        [sg.Checkbox("Dry run", default=True, key="-DRY-"), sg.Checkbox("Recursive", default=True, key="-REC-")],
        [sg.Text("Organize by:"), sg.Combo(["type","date"], default_value="type", key="-BY-")],
        [sg.Button("Scan", key="-SCAN-"), sg.Button("Organize", key="-ORGANIZE-"), sg.Button("Dedupe", key="-DEDUPE-"), sg.Button("Report", key="-REPORT-"), sg.Button("Undo", key="-UNDO-")],
        [sg.ProgressBar(100, orientation="h", size=(40, 10), key="-PROG-")],
        [sg.Multiline(size=(100,20), key="-OUT-")],
        [sg.Button("Exit")]
    ]

    window = sg.Window("File Manager GUI", layout, finalize=True)

    def append(msg: str):
        window['-OUT-'].print(msg)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            break

        if event == '-SCAN-':
            paths = [p.strip() for p in values['-PATHS-'].split(',') if p.strip()]
            if not paths:
                append('No paths provided for scan')
                continue
            append(f'Starting scan: {paths} (recursive={values["-REC-"]})')

            def do_scan():
                out = []
                for p in paths:
                    for item in scanner.scan_paths([p], recursive=values['-REC-']):
                        out.append(item)
                return out

            _run_in_thread(window, '-SCAN_DONE-', do_scan)

        if event == '-SCAN_DONE-':
            ok, payload = values['-SCAN_DONE-']
            if not ok:
                append(f"Scan error: {payload}")
            else:
                append(f"Scan completed: {len(payload)} items")
                # briefly show sample
                try:
                    window['-OUT-'].print(json.dumps(payload[:5], indent=2))
                except Exception:
                    pass

        if event == '-ORGANIZE-':
            paths = [p.strip() for p in values['-PATHS-'].split(',') if p.strip()]
            target = values['-TARGET-'] or '.'
            dry = values['-DRY-']
            by = values['-BY-']
            if not paths:
                append('No source paths provided')
                continue
            append(f'Organize {paths} -> {target} by {by} (dry={dry})')

            def do_org():
                items = []
                for p in paths:
                    for it in scanner.scan_paths([p], recursive=values['-REC-']):
                        items.append(it)
                targ = Path(target)
                if by == 'type':
                    return organizer.organize_by_type(items, targ, dry_run=dry)
                return organizer.organize_by_date(items, targ, dry_run=dry)

            _run_in_thread(window, '-ORG_DONE-', do_org)

        if event == '-ORG_DONE-':
            ok, payload = values['-ORG_DONE-']
            if not ok:
                append(f'Organize error: {payload}')
            else:
                append(f'Organize completed: actions={len(payload)}')
                try:
                    window['-OUT-'].print(json.dumps(payload[:10], indent=2))
                except Exception:
                    pass

        if event == '-DEDUPE-':
            paths = [p.strip() for p in values['-PATHS-'].split(',') if p.strip()]
            if not paths:
                append('No paths provided for dedupe')
                continue
            append(f'Starting dedupe on: {paths}')

            def do_dedupe():
                # deduper.find_duplicates expects paths; may vary by implementation
                return deduper.find_duplicates(paths)

            _run_in_thread(window, '-DEDUPE_DONE-', do_dedupe)

        if event == '-DEDUPE_DONE-':
            ok, payload = values['-DEDUPE_DONE-']
            if not ok:
                append(f'Dedupe error: {payload}')
            else:
                # payload may be dict of groups
                try:
                    groups = payload
                    count = sum(1 for g in groups.values() if len(g) > 1)
                    append(f'Dedupe completed: {count} duplicate groups')
                    window['-OUT-'].print(json.dumps(groups, indent=2))
                except Exception:
                    append(str(payload))

        if event == '-REPORT-':
            out_file = values['-TARGET-'] or 'report.json'
            paths = [p.strip() for p in values['-PATHS-'].split(',') if p.strip()]
            if not paths:
                append('No scan JSON path provided for report')
                continue
            append(f'Generating report to {out_file}')

            def do_report():
                # try to treat first path as scan json
                p = Path(paths[0])
                if p.exists() and p.suffix == '.json':
                    reporter.generate_report(str(p), out_file)
                    return out_file
                return 'No valid scan.json provided'

            _run_in_thread(window, '-REPORT_DONE-', do_report)

        if event == '-REPORT_DONE-':
            ok, payload = values['-REPORT_DONE-']
            if not ok:
                append(f'Report error: {payload}')
            else:
                append(f'Report done: {payload}')

        if event == '-UNDO-':
            logp = values['-PATHS-'].strip()
            dry = values['-DRY-']
            if not logp:
                append('Provide path to organize log JSON in the Paths field')
                continue
            append(f'Undo from {logp} (dry={dry})')

            def do_undo():
                return organizer.undo_moves(Path(logp), dry_run=dry)

            _run_in_thread(window, '-UNDO_DONE-', do_undo)

        if event == '-UNDO_DONE-':
            ok, payload = values['-UNDO_DONE-']
            if not ok:
                append(f'Undo error: {payload}')
            else:
                append(f'Undo completed: {len(payload)} entries')
                try:
                    window['-OUT-'].print(json.dumps(payload[:10], indent=2))
                except Exception:
                    pass

    window.close()


if __name__ == '__main__':
    main()
