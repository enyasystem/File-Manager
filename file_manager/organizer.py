"""File organization helpers"""
from pathlib import Path
import shutil
from typing import List, Dict

def organize_by_type(files: List[Dict], target_root: Path, dry_run: bool = True):
    actions = []
    target_root.mkdir(parents=True, exist_ok=True)
    for f in files:
        src = Path(f["path"])
        ext = f.get("ext") or "unknown"
        dest_dir = target_root / ext
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        actions.append((str(src), str(dest)))
        if not dry_run:
            try:
                shutil.move(str(src), str(dest))
            except Exception:
                pass
    return actions

def organize_by_date(files: List[Dict], target_root: Path, dry_run: bool = True):
    actions = []
    target_root.mkdir(parents=True, exist_ok=True)
    for f in files:
        src = Path(f["path"])
        import time
        t = time.localtime(f.get("ctime", src.stat().st_ctime))
        year = t.tm_year
        month = f"{t.tm_mon:02d}"
        dest_dir = target_root / str(year) / month
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        actions.append((str(src), str(dest)))
        if not dry_run:
            try:
                shutil.move(str(src), str(dest))
            except Exception:
                pass
    return actions
