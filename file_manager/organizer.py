"""File organization helpers with undo log and collision handling.

Provides simple, robust implementations for organizing files and undoing moves.

Functions:
- organize_by_type(files, target_root, dry_run=True)
- organize_by_date(files, target_root, dry_run=True)
- undo_moves(log_path, dry_run=False)
"""
from pathlib import Path
import shutil
from typing import List, Dict, Tuple
import json
import time
from datetime import datetime


def _unique_dest(dest: Path) -> Path:
    """Return a non-colliding destination by appending an index suffix.

    E.g. file.txt -> file_1.txt, file_2.txt, ...
    """
    if not dest.exists():
        return dest
    base = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    i = 1
    while True:
        candidate = parent / f"{base}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def _record_action(actions: List[Dict], src: Path, dst: Path, **extra) -> None:
    entry = {"src": str(src), "dst": str(dst), "time": datetime.utcnow().isoformat() + "Z"}
    entry.update(extra)
    actions.append(entry)


def _write_log(actions: List[Dict], target_root: Path) -> Path:
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    logp = target_root / f"fm_organize_{stamp}.json"
    with logp.open("w", encoding="utf-8") as f:
        json.dump(actions, f, indent=2)
    return logp


def _do_move(src: Path, dst: Path) -> Tuple[Path, Path]:
    dst_parent = dst.parent
    dst_parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst = _unique_dest(dst)
    shutil.move(str(src), str(dst))
    return src, dst


def organize_by_type(files: List[Dict], target_root: Path, dry_run: bool = True) -> List[Dict]:
    """Move files into subfolders under `target_root` by file extension.

    Each action is recorded as a dict with at least `src`, `dst`, and `time`.
    If not `dry_run`, moves are performed and a log file is written under
    `target_root`; its path is appended as a final action under key `log`.
    """
    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for f in files:
        src = Path(f["path"])
        ext = f.get("ext") or "unknown"
        dest_dir = target_root / ext
        dest = dest_dir / src.name
        if not src.exists():
            _record_action(actions, src, dest, status="missing")
            continue
        if dry_run:
            _record_action(actions, src, dest, status="dry-run")
            continue
        try:
            srcp, dstp = _do_move(src, dest)
            _record_action(actions, srcp, dstp, status="moved")
        except Exception as e:
            _record_action(actions, src, dest, status="error", error=str(e))
    if not dry_run and actions:
        logp = _write_log(actions, target_root)
        actions.append({"log": str(logp)})
    return actions


def organize_by_date(files: List[Dict], target_root: Path, dry_run: bool = True) -> List[Dict]:
    """Move files into year/month folders under `target_root` based on creation time."""
    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for f in files:
        src = Path(f["path"])
        if not src.exists():
            # determine a best-effort destination for logging
            try:
                t = time.localtime(f.get("ctime", src.stat().st_ctime))
            except Exception:
                t = time.localtime()
            year = t.tm_year
            month = f"{t.tm_mon:02d}"
            dest = target_root / str(year) / month / src.name
            _record_action(actions, src, dest, status="missing")
            continue
        try:
            t = time.localtime(f.get("ctime", src.stat().st_ctime))
        except Exception:
            t = time.localtime(src.stat().st_ctime)
        year = t.tm_year
        month = f"{t.tm_mon:02d}"
        dest_dir = target_root / str(year) / month
        dest = dest_dir / src.name
        if dry_run:
            _record_action(actions, src, dest, status="dry-run")
            continue
        try:
            srcp, dstp = _do_move(src, dest)
            _record_action(actions, srcp, dstp, status="moved")
        except Exception as e:
            _record_action(actions, src, dest, status="error", error=str(e))
    if not dry_run and actions:
        logp = _write_log(actions, target_root)
        actions.append({"log": str(logp)})
    return actions


def undo_moves(log_path: Path, dry_run: bool = False) -> List[Dict]:
    """Undo moves recorded in an organizer log file.

    For each entry with `src` and `dst`, attempts to move `dst` back to `src`.
    Returns a list of result dicts with `status` fields.
    """
    with open(log_path, "r", encoding="utf-8") as f:
        actions = json.load(f)
    results: List[Dict] = []
    for a in actions:
        if not isinstance(a, dict) or "src" not in a or "dst" not in a:
            continue
        src = Path(a["src"])
        dst = Path(a["dst"])
        if not dst.exists():
            results.append({"src": str(src), "dst": str(dst), "status": "missing"})
            continue
        if dry_run:
            results.append({"src": str(src), "dst": str(dst), "status": "dry-run"})
            continue
        dest_restore = src
        if dest_restore.exists():
            base = dest_restore.stem
            suffix = dest_restore.suffix
            parent = dest_restore.parent
            i = 1
            while True:
                cand = parent / f"{base}_restored_{i}{suffix}"
                if not cand.exists():
                    dest_restore = cand
                    break
                i += 1
        try:
            dest_restore.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(dest_restore))
            results.append({"src": str(src), "dst": str(dst), "status": "restored", "restored_to": str(dest_restore)})
        except Exception as e:
            results.append({"src": str(src), "dst": str(dst), "status": "error", "error": str(e)})
    return results
"""File organization helpers with undo log and collision handling.

Simple, robust implementations for organizing files and undoing moves.
"""
from pathlib import Path
import shutil
from typing import List, Dict, Tuple
import json
import time
from datetime import datetime


def _unique_dest(dest: Path) -> Path:
    if not dest.exists():
        return dest
    base = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    i = 1
    while True:
        candidate = parent / f"{base}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def _record_action(actions: List[Dict], src: Path, dst: Path, **extra) -> None:
    entry = {"src": str(src), "dst": str(dst), "time": datetime.utcnow().isoformat() + "Z"}
    entry.update(extra)
    actions.append(entry)


def _write_log(actions: List[Dict], target_root: Path) -> Path:
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    logp = target_root / f"fm_organize_{stamp}.json"
    with logp.open("w", encoding="utf-8") as f:
        json.dump(actions, f, indent=2)
    return logp


def _do_move(src: Path, dst: Path) -> Tuple[Path, Path]:
    dst_parent = dst.parent
    dst_parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst = _unique_dest(dst)
    shutil.move(str(src), str(dst))
    return src, dst


def organize_by_type(files: List[Dict], target_root: Path, dry_run: bool = True) -> List[Dict]:
    """Move files into subfolders under `target_root` by file extension.

    Returns a list of action dicts. When not in dry-run mode, writes a log
    file under `target_root` named `fm_organize_*.json` and appends its path
    as the last element of the returned list under key `log`.
    """
    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for f in files:
        src = Path(f["path"])
        ext = f.get("ext") or "unknown"
        dest_dir = target_root / ext
        dest = dest_dir / src.name
        if dry_run:
            _record_action(actions, src, dest)
            continue
        if not src.exists():
            _record_action(actions, src, dest)
            actions[-1]["status"] = "missing"
            continue
        srcp, dstp = _do_move(src, dest)
        _record_action(actions, srcp, dstp)
    if not dry_run and actions:
        logp = _write_log(actions, target_root)
        actions.append({"log": str(logp)})
    return actions


def organize_by_date(files: List[Dict], target_root: Path, dry_run: bool = True) -> List[Dict]:
    """Move files into year/month folders under `target_root` based on creation time."""
    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for f in files:
        src = Path(f["path"])
        try:
            t = time.localtime(f.get("ctime", src.stat().st_ctime))
        except Exception:
            t = time.localtime(src.stat().st_ctime)
        year = t.tm_year
        month = f"{t.tm_mon:02d}"
        dest_dir = target_root / str(year) / month
        dest = dest_dir / src.name
        if dry_run:
            _record_action(actions, src, dest)
            continue
        if not src.exists():
            _record_action(actions, src, dest)
            actions[-1]["status"] = "missing"
            continue
        srcp, dstp = _do_move(src, dest)
        _record_action(actions, srcp, dstp)
    if not dry_run and actions:
        logp = _write_log(actions, target_root)
        actions.append({"log": str(logp)})
    return actions


def undo_moves(log_path: Path, dry_run: bool = False) -> List[Dict]:
    """Undo moves recorded in an organizer log file.

    For each entry with `src` and `dst`, attempts to move `dst` back to `src`.
    Returns list of result dicts with `status` fields.
    """
    with open(log_path, "r", encoding="utf-8") as f:
        actions = json.load(f)
    results: List[Dict] = []
    for a in actions:
        if not isinstance(a, dict) or "src" not in a or "dst" not in a:
            continue
        src = Path(a["src"])
        dst = Path(a["dst"])
        if not dst.exists():
            results.append({"src": str(src), "dst": str(dst), "status": "missing"})
            continue
        if dry_run:
            results.append({"src": str(src), "dst": str(dst), "status": "dry-run"})
            continue
        dest_restore = src
        if dest_restore.exists():
            base = dest_restore.stem
            suffix = dest_restore.suffix
            parent = dest_restore.parent
            i = 1
            while True:
                cand = parent / f"{base}_restored_{i}{suffix}"
                if not cand.exists():
                    dest_restore = cand
                    break
                i += 1
        try:
            dest_restore.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(dest_restore))
            results.append({"src": str(src), "dst": str(dst), "status": "restored", "restored_to": str(dest_restore)})
        except Exception as e:
            results.append({"src": str(src), "dst": str(dst), "status": "error", "error": str(e)})
    return results
"""File organization helpers with undo log and collision handling."""
from pathlib import Path
import shutil
from typing import List, Dict, Tuple
import json
import time
from datetime import datetime


def _unique_dest(dest: Path) -> Path:
    """Return a destination path that does not collide by appending a suffix."""
    if not dest.exists():
        return dest
    base = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    i = 1
    while True:
        candidate = parent / f"{base}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def _record_action(actions: List[Dict], src: Path, dst: Path) -> None:
    actions.append({
        "src": str(src),
        "dst": str(dst),
        "time": datetime.utcnow().isoformat() + "Z",
    })


def _write_log(actions: List[Dict], target_root: Path) -> Path:
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    logp = target_root / f"fm_organize_{stamp}.json"
    with logp.open("w", encoding="utf-8") as f:
        json.dump(actions, f, indent=2)
    return logp


def _do_move(src: Path, dst: Path) -> Tuple[Path, Path]:
    dst_parent = dst.parent
    dst_parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst = _unique_dest(dst)
    shutil.move(str(src), str(dst))
    return src, dst


def organize_by_type(files: List[Dict], target_root: Path, dry_run: bool = True) -> List[Dict]:
    """File organization helpers with undo log and collision handling."""
    from pathlib import Path
    import shutil
    from typing import List, Dict, Tuple
    import json
    import time
    from datetime import datetime


    def _unique_dest(dest: Path) -> Path:
        if not dest.exists():
            return dest
        base = dest.stem
        suffix = dest.suffix
        parent = dest.parent
        i = 1
        while True:
            candidate = parent / f"{base}_{i}{suffix}"
            if not candidate.exists():
                return candidate
            i += 1


    def _record_action(actions: List[Dict], src: Path, dst: Path) -> None:
        actions.append({
            "src": str(src),
            "dst": str(dst),
            "time": datetime.utcnow().isoformat() + "Z",
        })


    def _write_log(actions: List[Dict], target_root: Path) -> Path:
        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        logp = target_root / f"fm_organize_{stamp}.json"
        with logp.open("w", encoding="utf-8") as f:
            json.dump(actions, f, indent=2)
        return logp


    def _do_move(src: Path, dst: Path) -> Tuple[Path, Path]:
        dst_parent = dst.parent
        dst_parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst = _unique_dest(dst)
        shutil.move(str(src), str(dst))
        return src, dst


    def organize_by_type(files: List[Dict], target_root: Path, dry_run: bool = True) -> List[Dict]:
        actions: List[Dict] = []
        target_root.mkdir(parents=True, exist_ok=True)
        for f in files:
            src = Path(f["path"])
            ext = f.get("ext") or "unknown"
            dest_dir = target_root / ext
            dest = dest_dir / src.name
            if dry_run:
                _record_action(actions, src, dest)
                continue
            if not src.exists():
                _record_action(actions, src, dest)
                actions[-1]["status"] = "missing"
                continue
            srcp, dstp = _do_move(src, dest)
            _record_action(actions, srcp, dstp)
        if not dry_run and actions:
            logp = _write_log(actions, target_root)
            actions.append({"log": str(logp)})
        return actions


    def organize_by_date(files: List[Dict], target_root: Path, dry_run: bool = True) -> List[Dict]:
        actions: List[Dict] = []
        target_root.mkdir(parents=True, exist_ok=True)
        for f in files:
            src = Path(f["path"])
            try:
                t = time.localtime(f.get("ctime", src.stat().st_ctime))
            except Exception:
                t = time.localtime(src.stat().st_ctime)
            year = t.tm_year
            month = f"{t.tm_mon:02d}"
            dest_dir = target_root / str(year) / month
            dest = dest_dir / src.name
            if dry_run:
                _record_action(actions, src, dest)
                continue
            if not src.exists():
                _record_action(actions, src, dest)
                actions[-1]["status"] = "missing"
                continue
            srcp, dstp = _do_move(src, dest)
            _record_action(actions, srcp, dstp)
        if not dry_run and actions:
            logp = _write_log(actions, target_root)
            actions.append({"log": str(logp)})
        return actions


    def undo_moves(log_path: Path, dry_run: bool = False) -> List[Dict]:
        with open(log_path, "r", encoding="utf-8") as f:
            actions = json.load(f)
        results: List[Dict] = []
        for a in actions:
            if not isinstance(a, dict) or "src" not in a or "dst" not in a:
                continue
            src = Path(a["src"])
            dst = Path(a["dst"])
            if not dst.exists():
                results.append({"src": str(src), "dst": str(dst), "status": "missing"})
                continue
            if dry_run:
                results.append({"src": str(src), "dst": str(dst), "status": "dry-run"})
                continue
            dest_restore = src
            if dest_restore.exists():
                base = dest_restore.stem
                suffix = dest_restore.suffix
                parent = dest_restore.parent
                i = 1
                while True:
                    cand = parent / f"{base}_restored_{i}{suffix}"
                    if not cand.exists():
                        dest_restore = cand
                        break
                    i += 1
            try:
                dest_restore.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst), str(dest_restore))
                results.append({"src": str(src), "dst": str(dst), "status": "restored", "restored_to": str(dest_restore)})
            except Exception as e:
                results.append({"src": str(src), "dst": str(dst), "status": "error", "error": str(e)})
        return results

def organize_by_type(files: List[Dict], target_root: Path, dry_run: bool = True, mode: str = "move") -> List[Dict]:
    """Organize files into subfolders by extension.

    Returns list of actions (dicts). Each action includes a `mode` field.
    If not dry_run, performs moves and writes a log under the target root
    and returns the log path in the last action as 'log'.
    """
    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for f in files:
        src = Path(f["path"])
        ext = f.get("ext") or "unknown"
        dest_dir = target_root / ext
        dest = dest_dir / src.name
        if dry_run:
            _record_action(actions, src, dest, status="dry-run", mode=mode)
            continue
        if not src.exists():
            _record_action(actions, src, dest, status="missing", mode=mode)
            continue
        try:
            srcp, dstp = _do_move(src, dest)
            _record_action(actions, srcp, dstp, status="moved", mode=mode)
        except Exception as e:
            _record_action(actions, src, dest, status="error", error=str(e), mode=mode)
    if not dry_run and actions:
        logp = _write_log(actions, target_root)
        actions.append({"log": str(logp)})
    return actions


def organize_by_date(files: List[Dict], target_root: Path, dry_run: bool = True, mode: str = "move") -> List[Dict]:
    """Organize files into year/month folders based on creation time.

    Same return semantics as `organize_by_type`. Each action includes `mode`.
    """
    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for f in files:
        src = Path(f["path"])
        try:
            t = time.localtime(f.get("ctime", src.stat().st_ctime))
        except Exception:
            t = time.localtime(src.stat().st_ctime)
        year = t.tm_year
        month = f"{t.tm_mon:02d}"
        dest_dir = target_root / str(year) / month
        dest = dest_dir / src.name
        if dry_run:
            _record_action(actions, src, dest, status="dry-run", mode=mode)
            continue
        if not src.exists():
            _record_action(actions, src, dest, status="missing", mode=mode)
            continue
        try:
            srcp, dstp = _do_move(src, dest)
            _record_action(actions, srcp, dstp, status="moved", mode=mode)
        except Exception as e:
            _record_action(actions, src, dest, status="error", error=str(e), mode=mode)
    if not dry_run and actions:
        logp = _write_log(actions, target_root)
        actions.append({"log": str(logp)})
    return actions


def undo_moves(log_path: Path, dry_run: bool = False) -> List[Dict]:
    """Undo moves recorded in a log file created by the organizer.

    Returns list of undo actions with status.
    """
    with open(log_path, "r", encoding="utf-8") as f:
        actions = json.load(f)
    results: List[Dict] = []
    for a in actions:
        if not isinstance(a, dict) or "src" not in a or "dst" not in a:
            continue
        src = Path(a["src"])
        dst = Path(a["dst"])
        if not dst.exists():
            results.append({"src": str(src), "dst": str(dst), "status": "missing"})
            continue
        if dry_run:
            results.append({"src": str(src), "dst": str(dst), "status": "dry-run"})
            continue
        # if original src exists, make a unique name to avoid overwrite
        dest_restore = src
        if dest_restore.exists():
            base = dest_restore.stem
            suffix = dest_restore.suffix
            parent = dest_restore.parent
            i = 1
            while True:
                cand = parent / f"{base}_restored_{i}{suffix}"
                if not cand.exists():
                    dest_restore = cand
                    break
                i += 1
        try:
            dest_restore.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(dest_restore))
            results.append({"src": str(src), "dst": str(dst), "status": "restored", "restored_to": str(dest_restore)})
        except Exception as e:
            results.append({"src": str(src), "dst": str(dst), "status": "error", "error": str(e)})
    return results
"""File organization helpers with undo log and collision handling."""
from pathlib import Path
import shutil
from typing import List, Dict, Tuple
import json
import time
from datetime import datetime
from .utils import safe_copy


def _unique_dest(dest: Path) -> Path:
    """Return a destination path that does not collide by appending a suffix."""
    if not dest.exists():
        return dest
    base = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    i = 1
    while True:
        candidate = parent / f"{base}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def _record_action(actions: List[Dict], src: Path, dst: Path, **extra) -> None:
    entry = {
        "src": str(src),
        "dst": str(dst),
        "time": datetime.utcnow().isoformat() + "Z",
    }
    if extra:
        entry.update(extra)
    actions.append(entry)


def _write_log(actions: List[Dict], target_root: Path) -> Path:
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    logp = target_root / f"fm_organize_{stamp}.json"
    with logp.open("w", encoding="utf-8") as f:
        json.dump(actions, f, indent=2)
    return logp


def _do_move(src: Path, dst: Path) -> Tuple[Path, Path]:
    dst_parent = dst.parent
    dst_parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst = _unique_dest(dst)
    shutil.move(str(src), str(dst))
    return src, dst


def organize_by_type(files: List[Dict], target_root: Path, dry_run: bool = True, mode: str = "move") -> List[Dict]:
    """Organize files into subfolders by extension.

    Returns list of actions (dicts). When not in dry-run mode, writes a log
    file under `target_root` and appends its path as the last element.
    Each action includes a `mode` and `status` field.
    """
    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for f in files:
        src = Path(f["path"])
        ext = f.get("ext") or "unknown"
        dest_dir = target_root / ext
        dest = dest_dir / src.name
        if dry_run:
            _record_action(actions, src, dest, status="dry-run", mode=mode)
            continue
        if not src.exists():
            _record_action(actions, src, dest, status="missing", mode=mode)
            continue
        try:
            if mode == "copy":
                srcp, dstp = safe_copy(src, dest)
                _record_action(actions, srcp, dstp, status="copied", mode=mode)
            else:
                srcp, dstp = _do_move(src, dest)
                _record_action(actions, srcp, dstp, status="moved", mode=mode)
        except Exception as e:
            _record_action(actions, src, dest, status="error", error=str(e), mode=mode)
    if not dry_run and actions:
        logp = _write_log(actions, target_root)
        actions.append({"log": str(logp)})
    return actions


def organize_by_date(files: List[Dict], target_root: Path, dry_run: bool = True, mode: str = "move") -> List[Dict]:
    """Organize files into year/month folders based on creation time.

    Same return semantics as `organize_by_type`. Each action includes `mode`.
    """
    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for f in files:
        src = Path(f["path"])
        try:
            t = time.localtime(f.get("ctime", src.stat().st_ctime))
        except Exception:
            t = time.localtime(src.stat().st_ctime)
        year = t.tm_year
        month = f"{t.tm_mon:02d}"
        dest_dir = target_root / str(year) / month
        dest = dest_dir / src.name
        if dry_run:
            _record_action(actions, src, dest, status="dry-run", mode=mode)
            continue
        if not src.exists():
            _record_action(actions, src, dest, status="missing", mode=mode)
            continue
        try:
            if mode == "copy":
                srcp, dstp = safe_copy(src, dest)
                _record_action(actions, srcp, dstp, status="copied", mode=mode)
            else:
                srcp, dstp = _do_move(src, dest)
                _record_action(actions, srcp, dstp, status="moved", mode=mode)
        except Exception as e:
            _record_action(actions, src, dest, status="error", error=str(e), mode=mode)
    if not dry_run and actions:
        logp = _write_log(actions, target_root)
        actions.append({"log": str(logp)})
    return actions


def undo_moves(log_path: Path, dry_run: bool = False) -> List[Dict]:
    """Undo moves recorded in a log file created by the organizer.

    For `copy` mode entries the undo operation will remove the copied `dst` file.
    For `move` mode entries it will attempt to move `dst` back to `src` (with
    collision-avoidance if the original exists).
    Returns list of undo actions with status.
    """
    with open(log_path, "r", encoding="utf-8") as f:
        actions = json.load(f)
    results: List[Dict] = []
    for a in actions:
        if not isinstance(a, dict) or "src" not in a or "dst" not in a:
            continue
        src = Path(a["src"])
        dst = Path(a["dst"])
        mode = a.get("mode", "move")
        if not dst.exists():
            results.append({"src": str(src), "dst": str(dst), "status": "missing"})
            continue
        if dry_run:
            results.append({"src": str(src), "dst": str(dst), "status": "dry-run"})
            continue
        try:
            if mode in ("copy", "hardlink"):
                # For copy and hardlink modes, undo means removing the target link/file.
                try:
                    dst.unlink()
                    status = "deleted_copy" if mode == "copy" else "deleted_hardlink"
                    results.append({"src": str(src), "dst": str(dst), "status": status})
                except FileNotFoundError:
                    results.append({"src": str(src), "dst": str(dst), "status": "missing"})
                except Exception as e:
                    results.append({"src": str(src), "dst": str(dst), "status": "error", "error": str(e)})
            elif mode == "index":
                # Index mode: dst may be a generated file or folder; remove it.
                try:
                    if dst.is_file():
                        dst.unlink()
                        results.append({"src": str(src), "dst": str(dst), "status": "deleted_index"})
                    elif dst.is_dir():
                        shutil.rmtree(str(dst))
                        results.append({"src": str(src), "dst": str(dst), "status": "deleted_index_dir"})
                    else:
                        results.append({"src": str(src), "dst": str(dst), "status": "missing"})
                except Exception as e:
                    results.append({"src": str(src), "dst": str(dst), "status": "error", "error": str(e)})
            else:
                # move (default): move the file back to original location
                dest_restore = src
                if dest_restore.exists():
                    base = dest_restore.stem
                    suffix = dest_restore.suffix
                    parent = dest_restore.parent
                    i = 1
                    while True:
                        cand = parent / f"{base}_restored_{i}{suffix}"
                        if not cand.exists():
                            dest_restore = cand
                            break
                        i += 1
                dest_restore.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst), str(dest_restore))
                results.append({"src": str(src), "dst": str(dst), "status": "restored", "restored_to": str(dest_restore)})
        except Exception as e:
            results.append({"src": str(src), "dst": str(dst), "status": "error", "error": str(e)})
    return results
