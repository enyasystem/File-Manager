"""File organization helpers with undo log and collision handling.

Provides organize_by_type and organize_by_date with dry-run, copy/move
semantics, optional EXIF date support, size-threshold bucketing, and
extension filtering. Actions are logged to a JSON undo file written under
the provided `target_root`.
"""
from pathlib import Path
import shutil
from typing import List, Dict, Tuple, Optional
import json
import time
from datetime import datetime
import calendar

try:
    from .utils import safe_copy
except Exception:
    # safe_copy is optional for some environments; fallback to shutil.copy2
    def safe_copy(src: Path, dst: Path) -> Tuple[Path, Path]:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            # append a suffix
            base = dst.stem
            suffix = dst.suffix
            parent = dst.parent
            i = 1
            while True:
                candidate = parent / f"{base}_{i}{suffix}"
                if not candidate.exists():
                    dst = candidate
                    break
                i += 1
        shutil.copy2(str(src), str(dst))
        return src, dst


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


def organize_by_type(
    files: List[Dict],
    target_root: Path,
    dry_run: bool = True,
    mode: str = "move",
    extensions: Optional[List[str]] = None,
) -> List[Dict]:
    """Organize files into subfolders by extension.

    If `extensions` is provided (list of extensions without leading dot), only
    those types will be processed; others are recorded as `skipped`.
    """
    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)

    ext_filter = None
    """File organization helpers with undo log and collision handling.

    Simple, focused implementations for organizing files and undoing moves.
    Features:
    - organize_by_type: group files into extension folders
    - organize_by_date: group files by date with optional month/year filter
    - size-bucket placement and EXIF/ctime/mtime date source support
    - dry-run mode and per-operation JSON undo log
    """
    from pathlib import Path
    import shutil
    from typing import List, Dict, Tuple, Optional
    import json
    import time
    from datetime import datetime
    import calendar

    try:
        from .utils import safe_copy
    except Exception:
        def safe_copy(src: Path, dst: Path) -> Tuple[Path, Path]:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                base = dst.stem
                suffix = dst.suffix
                parent = dst.parent
                i = 1
                while True:
                    candidate = parent / f"{base}_{i}{suffix}"
                    if not candidate.exists():
                        dst = candidate
                        break
                    i += 1
            shutil.copy2(str(src), str(dst))
            return src, dst


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


    def organize_by_type(
        files: List[Dict],
        target_root: Path,
        dry_run: bool = True,
        mode: str = "move",
        extensions: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Organize files into subfolders by extension.

        If `extensions` is provided, only those extensions are processed.
        """
        actions: List[Dict] = []
        target_root.mkdir(parents=True, exist_ok=True)

        ext_filter = None
        if extensions:
            ext_filter = {e.lower().lstrip('.') for e in extensions}

        for f in files:
            src = Path(f["path"])
            # only operate on files (skip directories)
            if not src.exists() or not src.is_file():
                _record_action(actions, src, target_root / src.name, status="skipped", reason="not-file", mode=mode)
                continue

            ext = (f.get("ext") or src.suffix or "").lstrip('.').lower() or "unknown"
            dest_dir = target_root / ext
            dest = dest_dir / src.name

            if ext_filter is not None and ext not in ext_filter:
                _record_action(actions, src, dest, status="skipped", mode=mode)
                continue

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


    def organize_by_date(
        files: List[Dict],
        target_root: Path,
        dry_run: bool = True,
        mode: str = "move",
        selected_month: Optional[int] = None,
        selected_year: Optional[int] = None,
        size_threshold_mb: Optional[int] = None,
        size_folder_name: str = "Large",
        date_source: str = "ctime",
    ) -> List[Dict]:
        """Organize files by date with optional month-selection and size bucket.

        date_source: 'ctime', 'mtime', or 'exif' (EXIF requires Pillow; falls back).
        """
        actions: List[Dict] = []
        target_root.mkdir(parents=True, exist_ok=True)

        has_pillow = False
        exif_tag_map = {}
        if date_source == "exif":
            try:
                from PIL import Image, ExifTags

                exif_tag_map = {v: k for k, v in ExifTags.TAGS.items()}
                has_pillow = True
            except Exception:
                has_pillow = False

        for f in files:
            src = Path(f["path"])

            # timestamp selection
            try:
                if date_source == "mtime":
                    t = time.localtime(f.get("mtime", src.stat().st_mtime))
                elif date_source == "exif" and has_pillow and src.exists():
                    try:
                        from PIL import Image

                        with Image.open(str(src)) as im:
                            exif = im._getexif() or {}
                        dt = None
                        for tag_name in ("DateTimeOriginal", "DateTime"):
                            tag_key = exif_tag_map.get(tag_name)
                            if tag_key and exif.get(tag_key):
                                dt = exif.get(tag_key)
                                break
                        if dt:
                            dt_clean = dt.replace(':', '-', 2)
                            try:
                                parsed = datetime.strptime(dt_clean, "%Y-%m-%d %H:%M:%S")
                                t = parsed.timetuple()
                            except Exception:
                                t = time.localtime(src.stat().st_ctime)
                        else:
                            t = time.localtime(src.stat().st_ctime)
                    except Exception:
                        t = time.localtime(src.stat().st_ctime)
                else:
                    t = time.localtime(f.get("ctime", src.stat().st_ctime))
            except Exception:
                try:
                    t = time.localtime(src.stat().st_ctime)
                except Exception:
                    t = time.localtime()

            # size
            try:
                size_bytes = src.stat().st_size if src.exists() else int(f.get("size", 0) or 0)
            except Exception:
                size_bytes = int(f.get("size", 0) or 0)

            year = t.tm_year
            month_num = t.tm_mon

            # skip non-files (avoid moving directories)
            if not src.exists() or not src.is_file():
                _record_action(actions, src, target_root / src.name, status="skipped", reason="not-file", mode=mode)
                continue

            # size-bucket precedence
            if size_threshold_mb is not None:
                try:
                    if size_bytes >= int(size_threshold_mb) * 1024 * 1024:
                        dest_dir = target_root / size_folder_name
                        dest = dest_dir / src.name
                        if dry_run:
                            _record_action(actions, src, dest, status="dry-run", mode=mode, reason="size")
                            continue
                        if not src.exists():
                            _record_action(actions, src, dest, status="missing", mode=mode, reason="size")
                            continue
                        try:
                            if mode == "copy":
                                srcp, dstp = safe_copy(src, dest)
                                _record_action(actions, srcp, dstp, status="copied", mode=mode, reason="size")
                            else:
                                srcp, dstp = _do_move(src, dest)
                                _record_action(actions, srcp, dstp, status="moved", mode=mode, reason="size")
                        except Exception as e:
                            _record_action(actions, src, dest, status="error", error=str(e), mode=mode, reason="size")
                        continue
                except Exception:
                    pass

            # month filter
            if selected_month is not None and selected_year is not None:
                if not (year == int(selected_year) and month_num == int(selected_month)):
                    _record_action(actions, src, target_root, status="skipped", mode=mode)
                    continue
                month_name = calendar.month_name[month_num]
                dest_dir = target_root / f"{month_name} {year}"
            else:
                dest_dir = target_root / str(year) / f"{month_num:02d}"

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
                    try:
                        dst.unlink()
                        status = "deleted_copy" if mode == "copy" else "deleted_hardlink"
                        results.append({"src": str(src), "dst": str(dst), "status": status})
                    except FileNotFoundError:
                        results.append({"src": str(src), "dst": str(dst), "status": "missing"})
                    except Exception as e:
                        results.append({"src": str(src), "dst": str(dst), "status": "error", "error": str(e)})
                elif mode == "index":
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
            srcp, dstp = _do_move(src, dest)
            _record_action(actions, srcp, dstp, status="moved")
        if not dry_run and actions:
            logp = _write_log(actions, target_root)
            actions.append({"log": str(logp)})
        return actions
    
    def organize_by_date(
        files: List[Dict],
        target_root: Path,
        dry_run: bool = True,
        mode: str = "move",
        selected_month: int | None = None,
        selected_year: int | None = None,
        size_threshold_mb: int | None = None,
        size_folder_name: str = "Large",
    ) -> List[Dict]:
        """Organize files by date with optional month-selection and size bucket."""
        actions: List[Dict] = []
        target_root.mkdir(parents=True, exist_ok=True)
        for f in files:
            src = Path(f["path"])
            # resolve time and size where possible
            try:
                t = time.localtime(f.get("ctime", src.stat().st_ctime))
            except Exception:
                try:
                    t = time.localtime(src.stat().st_ctime)
                except Exception:
                    t = time.localtime()
            try:
                size_bytes = src.stat().st_size if src.exists() else f.get("size", 0)
            except Exception:
                size_bytes = f.get("size", 0)
            year = t.tm_year
            month_num = t.tm_mon
            # size bucket check (takes precedence)
            if size_threshold_mb is not None:
                try:
                    if size_bytes >= int(size_threshold_mb) * 1024 * 1024:
                        dest_dir = target_root / size_folder_name
                        dest = dest_dir / src.name
                        if dry_run:
                            _record_action(actions, src, dest, status="dry-run", mode=mode, reason="size")
                            continue
                        if not src.exists():
                            _record_action(actions, src, dest, status="missing", mode=mode, reason="size")
                            continue
                        try:
                            if mode == "copy":
                                srcp, dstp = safe_copy(src, dest)
                                _record_action(actions, srcp, dstp, status="copied", mode=mode, reason="size")
                            else:
                                srcp, dstp = _do_move(src, dest)
                                _record_action(actions, srcp, dstp, status="moved", mode=mode, reason="size")
                        except Exception as e:
                            _record_action(actions, src, dest, status="error", error=str(e), mode=mode, reason="size")
                        continue
                except Exception:
                    pass
            # if month/year selection provided, only operate on matching files
            if selected_month is not None and selected_year is not None:
                if not (year == int(selected_year) and month_num == int(selected_month)):
                    _record_action(actions, src, target_root, status="skipped", mode=mode)
                    continue
                # use friendly month folder name
                month_name = calendar.month_name[month_num]
                dest_dir = target_root / f"{month_name} {year}"
            else:
                # default year/month layout
                dest_dir = target_root / str(year) / f"{month_num:02d}"
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

def organize_by_type(
    files: List[Dict],
    target_root: Path,
    dry_run: bool = True,
    mode: str = "move",
    extensions: List[str] | None = None,
) -> List[Dict]:
    """Organize files into subfolders by extension.

    Returns list of actions (dicts). Each action includes a `mode` field.
    If not dry_run, performs moves and writes a log under the target root
    and returns the log path in the last action as 'log'.
    """
    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)
    # normalize extensions filter if provided (no leading dot, lowercase)
    ext_filter = None
    if extensions:
        ext_filter = {e.lower().lstrip('.') for e in extensions}

    for f in files:
        src = Path(f["path"])
        ext = f.get("ext") or "unknown"
        dest_dir = target_root / ext
        dest = dest_dir / src.name
        # if an extensions filter is provided, skip non-matching extensions
        if ext_filter is not None:
            if (ext or "").lstrip('.').lower() not in ext_filter:
                _record_action(actions, src, dest, status="skipped", mode=mode)
                continue
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


def organize_by_date(
    files: List[Dict],
    target_root: Path,
    dry_run: bool = True,
    mode: str = "move",
    selected_month: int | None = None,
    selected_year: int | None = None,
    size_threshold_mb: int | None = None,
    size_folder_name: str = "Large",
) -> List[Dict]:
    """Organize files by date with optional month-selection and size bucket.

    Behavior:
    - If `selected_month` and `selected_year` are provided, only files whose
      creation time matches that month/year are targeted and moved into a
      folder named like "December 2025" under `target_root`.
    - If `size_threshold_mb` is provided and a file's size is >= threshold,
      it will be placed into `target_root / size_folder_name` (size bucket).
      Size-bucket placement takes precedence over month grouping when both
      criteria apply.

    Keeps same return semantics as `organize_by_type` and records `mode`.
    """
    import calendar

    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for f in files:
        src = Path(f["path"])
        # resolve time and size where possible
        try:
            t = time.localtime(f.get("ctime", src.stat().st_ctime))
        except Exception:
            try:
                t = time.localtime(src.stat().st_ctime)
            except Exception:
                t = time.localtime()
        try:
            size_bytes = src.stat().st_size if src.exists() else f.get("size", 0)
        except Exception:
            size_bytes = f.get("size", 0)

        year = t.tm_year
        month_num = t.tm_mon

        # size bucket check (takes precedence)
        if size_threshold_mb is not None:
            try:
                if size_bytes >= int(size_threshold_mb) * 1024 * 1024:
                    dest_dir = target_root / size_folder_name
                    dest = dest_dir / src.name
                    if dry_run:
                        _record_action(actions, src, dest, status="dry-run", mode=mode, reason="size")
                        continue
                    if not src.exists():
                        _record_action(actions, src, dest, status="missing", mode=mode, reason="size")
                        continue
                    try:
                        if mode == "copy":
                            srcp, dstp = safe_copy(src, dest)
                            _record_action(actions, srcp, dstp, status="copied", mode=mode, reason="size")
                        else:
                            srcp, dstp = _do_move(src, dest)
                            _record_action(actions, srcp, dstp, status="moved", mode=mode, reason="size")
                    except Exception as e:
                        _record_action(actions, src, dest, status="error", error=str(e), mode=mode, reason="size")
                    continue
            except Exception:
                pass

        # if month/year selection provided, only operate on matching files
        if selected_month is not None and selected_year is not None:
            if not (year == int(selected_year) and month_num == int(selected_month)):
                _record_action(actions, src, target_root, status="skipped", mode=mode)
                continue
            # use friendly month folder name
            month_name = calendar.month_name[month_num]
            dest_dir = target_root / f"{month_name} {year}"
        else:
            # default year/month layout
            dest_dir = target_root / str(year) / f"{month_num:02d}"

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
