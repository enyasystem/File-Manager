"""Clean organizer implementation used as an override during testing."""
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
    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)

    ext_filter = None
    if extensions:
        ext_filter = {e.lower().lstrip('.') for e in extensions}

    for f in files:
        srcp = f.get('path') or f.get('src')
        if not srcp:
            continue
        src = Path(srcp)
        if not src.exists() or not src.is_file():
            _record_action(actions, src, target_root / (src.name if src else ''), status='skipped', reason='not-file', mode=mode)
            continue

        ext = (f.get('ext') or src.suffix or '').lstrip('.').lower() or 'unknown'
        dest_dir = target_root / ext
        dest = dest_dir / src.name

        if ext_filter is not None and ext not in ext_filter:
            _record_action(actions, src, dest, status='skipped', mode=mode)
            continue

        if dry_run:
            _record_action(actions, src, dest, status='dry-run', mode=mode)
            continue

        try:
            if mode == 'copy':
                srcp2, dstp = safe_copy(src, dest)
                _record_action(actions, srcp2, dstp, status='copied', mode=mode)
            else:
                srcp2, dstp = _do_move(src, dest)
                _record_action(actions, srcp2, dstp, status='moved', mode=mode)
        except Exception as e:
            _record_action(actions, src, dest, status='error', error=str(e), mode=mode)

    if not dry_run and actions:
        logp = _write_log(actions, target_root)
        actions.append({'log': str(logp)})
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
    actions: List[Dict] = []
    target_root.mkdir(parents=True, exist_ok=True)

    has_pillow = False
    exif_tag_map = {}
    if date_source == 'exif':
        try:
            from PIL import Image, ExifTags
            exif_tag_map = {v: k for k, v in ExifTags.TAGS.items()}
            has_pillow = True
        except Exception:
            has_pillow = False

    for f in files:
        srcp = f.get('path') or f.get('src')
        if not srcp:
            continue
        src = Path(srcp)
        if not src.exists() or not src.is_file():
            _record_action(actions, src, target_root / (src.name if src else ''), status='skipped', reason='not-file', mode=mode)
            continue

        # determine timestamp
        try:
            if date_source == 'mtime':
                t = time.localtime(f.get('mtime', src.stat().st_mtime))
            elif date_source == 'exif' and has_pillow:
                try:
                    from PIL import Image
                    with Image.open(str(src)) as im:
                        exif = im._getexif() or {}
                    dt = None
                    for tag_name in ('DateTimeOriginal', 'DateTime'):
                        tag_key = exif_tag_map.get(tag_name)
                        if tag_key and exif.get(tag_key):
                            dt = exif.get(tag_key)
                            break
                    if dt:
                        dt_clean = dt.replace(':', '-', 2)
                        try:
                            parsed = datetime.strptime(dt_clean, '%Y-%m-%d %H:%M:%S')
                            t = parsed.timetuple()
                        except Exception:
                            t = time.localtime(src.stat().st_ctime)
                    else:
                        t = time.localtime(src.stat().st_ctime)
                except Exception:
                    t = time.localtime(src.stat().st_ctime)
            else:
                t = time.localtime(f.get('ctime', src.stat().st_ctime))
        except Exception:
            try:
                t = time.localtime(src.stat().st_ctime)
            except Exception:
                t = time.localtime()

        try:
            size_bytes = src.stat().st_size
        except Exception:
            size_bytes = int(f.get('size', 0) or 0)

        year = t.tm_year
        month_num = t.tm_mon

        # size bucket precedence
        if size_threshold_mb is not None:
            try:
                if size_bytes >= int(size_threshold_mb) * 1024 * 1024:
                    dest_dir = target_root / size_folder_name
                    dest = dest_dir / src.name
                    if dry_run:
                        _record_action(actions, src, dest, status='dry-run', mode=mode, reason='size')
                        continue
                    try:
                        if mode == 'copy':
                            srcp2, dstp = safe_copy(src, dest)
                            _record_action(actions, srcp2, dstp, status='copied', mode=mode, reason='size')
                        else:
                            srcp2, dstp = _do_move(src, dest)
                            _record_action(actions, srcp2, dstp, status='moved', mode=mode, reason='size')
                    except Exception as e:
                        _record_action(actions, src, dest, status='error', error=str(e), mode=mode, reason='size')
                    continue
            except Exception:
                pass

        if selected_month is not None and selected_year is not None:
            if not (year == int(selected_year) and month_num == int(selected_month)):
                _record_action(actions, src, target_root, status='skipped', mode=mode)
                continue
            month_name = calendar.month_name[month_num]
            dest_dir = target_root / f"{month_name} {year}"
        else:
            dest_dir = target_root / str(year) / f"{month_num:02d}"

        dest = dest_dir / src.name
        if dry_run:
            _record_action(actions, src, dest, status='dry-run', mode=mode)
            continue

        try:
            if mode == 'copy':
                srcp2, dstp = safe_copy(src, dest)
                _record_action(actions, srcp2, dstp, status='copied', mode=mode)
            else:
                srcp2, dstp = _do_move(src, dest)
                _record_action(actions, srcp2, dstp, status='moved', mode=mode)
        except Exception as e:
            _record_action(actions, src, dest, status='error', error=str(e), mode=mode)

    if not dry_run and actions:
        logp = _write_log(actions, target_root)
        actions.append({'log': str(logp)})
    return actions


def undo_moves(log_path: Path, dry_run: bool = False) -> List[Dict]:
    with open(log_path, 'r', encoding='utf-8') as f:
        actions = json.load(f)
    results: List[Dict] = []
    for a in actions:
        if not isinstance(a, dict) or 'src' not in a or 'dst' not in a:
            continue
        src = Path(a['src']) if a.get('src') else Path('')
        dst = Path(a['dst']) if a.get('dst') else Path('')
        mode = a.get('mode', 'move')
        if not dst.exists():
            results.append({'src': str(src), 'dst': str(dst), 'status': 'missing'})
            continue
        if dry_run:
            results.append({'src': str(src), 'dst': str(dst), 'status': 'dry-run'})
            continue
        try:
            if mode in ('copy', 'hardlink'):
                try:
                    dst.unlink()
                    status = 'deleted_copy' if mode == 'copy' else 'deleted_hardlink'
                    results.append({'src': str(src), 'dst': str(dst), 'status': status})
                except FileNotFoundError:
                    results.append({'src': str(src), 'dst': str(dst), 'status': 'missing'})
                except Exception as e:
                    results.append({'src': str(src), 'dst': str(dst), 'status': 'error', 'error': str(e)})
            elif mode == 'index':
                try:
                    if dst.is_file():
                        dst.unlink()
                        results.append({'src': str(src), 'dst': str(dst), 'status': 'deleted_index'})
                    elif dst.is_dir():
                        shutil.rmtree(str(dst))
                        results.append({'src': str(src), 'dst': str(dst), 'status': 'deleted_index_dir'})
                    else:
                        results.append({'src': str(src), 'dst': str(dst), 'status': 'missing'})
                except Exception as e:
                    results.append({'src': str(src), 'dst': str(dst), 'status': 'error', 'error': str(e)})
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
                results.append({'src': str(src), 'dst': str(dst), 'status': 'restored', 'restored_to': str(dest_restore)})
        except Exception as e:
            results.append({'src': str(src), 'dst': str(dst), 'status': 'error', 'error': str(e)})
    return results
