# File-Manager

A small CLI toolset for scanning, organizing, deduplicating, and reporting on local files.

Core modules:
- `cli.py` — command-line entrypoint (scan, organize, dedupe, report, undo)
- `file_manager` — package with `scanner`, `organizer`, `deduper`, `reporter`, `utils`
- `gui.py` — optional PySimpleGUI frontend (prototype)

## Running the GUI

1. Install dependencies (recommended in a virtualenv):

```bash
pip install -r requirements.txt
```

2. Launch the GUI:

```bash
python gui.py
```

Notes:
- The GUI is a lightweight PySimpleGUI prototype that calls the existing backend in `file_manager`.
- Use the "Source Paths" field to enter one or more paths (comma-separated) and set a "Target Root" for organize/report actions.
- Keep the "Dry run" checkbox enabled for safety when trying organize/undo operations.
- If you prefer CLI usage, see `cli.py --help` for full options.

## Quick CLI examples

Scan a folder:
```bash
python cli.py scan C:\path\to\folder --out scan.json
```

Organize by type (dry run):
```bash
python cli.py organize C:\path\to\folder --target C:\path\to\out --by type --dry-run
```

Undo an organize log:
```bash
python cli.py undo C:\path\to\out\fm_organize_YYYYMMDDT...json
```
