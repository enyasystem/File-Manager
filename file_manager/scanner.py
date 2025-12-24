"""Scanning utilities"""
from pathlib import Path
import os
import mimetypes
from typing import Iterable, Dict

def scan_paths(paths: Iterable[Path], recursive: bool = True):
    """Yield metadata dicts for files under given paths."""
    for p in paths:
        p = Path(p)
        if p.is_file():
            yield _file_info(p)
        elif p.is_dir():
            if recursive:
                for root, _, files in os.walk(p):
                    for fn in files:
                        fp = Path(root) / fn
                        yield _file_info(fp)
            else:
                for fp in p.iterdir():
                    if fp.is_file():
                        yield _file_info(fp)

def _file_info(path: Path) -> Dict:
    stat = path.stat()
    mime, _ = mimetypes.guess_type(str(path))
    return {
        "path": str(path),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "ctime": stat.st_ctime,
        "ext": path.suffix.lower().lstrip("."),
        "mime": mime or "unknown",
    }
