"""Utility helpers"""
from pathlib import Path
import shutil
from typing import Tuple

def safe_move(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    return src.replace(dst)


def safe_copy(src: Path, dst: Path) -> Tuple[Path, Path]:
    """Copy `src` to `dst`, creating parent dirs and avoiding name collisions.

    Returns a tuple (src_path, dst_path) where dst_path may be a renamed
    destination if a collision was avoided.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    # if destination exists, append an index suffix
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

def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def estimate_size(items) -> int:
    """Estimate total size in bytes for a list of file-like items.

    `items` may be:
    - a list of `pathlib.Path` or string paths
    - a list of dicts containing a `path` or `src` key (organizer/deduper actions)

    Missing files are ignored and contribute 0.
    """
    total = 0
    for it in items or []:
        p = None
        if isinstance(it, dict):
            if "path" in it:
                p = it.get("path")
            elif "src" in it:
                p = it.get("src")
        else:
            p = it
        if p is None:
            continue
        try:
            path = Path(p)
            if path.exists() and path.is_file():
                total += path.stat().st_size
        except Exception:
            continue
    return int(total)
