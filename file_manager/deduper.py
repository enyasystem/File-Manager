"""Duplicate detection via hashing with safe deletion utilities."""
from pathlib import Path
import hashlib
from collections import defaultdict
from typing import List, Iterable, Optional, Tuple
import shutil
import logging
from datetime import datetime
import concurrent.futures
import threading
import time

_LOG = logging.getLogger(__name__)


def _hash_file(path: Path, algo: str = "sha256", chunk_size: int = 8192) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def find_duplicates(paths: Iterable[str], algo: str = "sha256") -> List[List[str]]:
    """Return list of duplicate groups (lists of file paths).

    Strategy: group by size first, then hash candidates to confirm duplicates.
    """
    by_size = defaultdict(list)
    for p in paths:
        try:
            s = Path(p).stat().st_size
            by_size[s].append(p)
        except Exception as e:
            _LOG.debug("Skipping %s: %s", p, e)
            continue
    candidates = [group for size, group in by_size.items() if len(group) > 1]
    # default to concurrent hashing for candidate files
    candidate_files = [p for group in candidates for p in group]
    hashes = defaultdict(list)
    for h, p in _hash_files_concurrent(candidate_files, algo=algo, workers=min(8, max(1, (len(candidate_files) // 10) + 1)), show_progress=False):
        hashes[h].append(p)
    dup_groups = [g for g in hashes.values() if len(g) > 1]
    return dup_groups


def _hash_files_concurrent(paths: Iterable[str], algo: str = "sha256", workers: int = 4, show_progress: bool = False) -> Iterable[Tuple[str, str]]:
    """Hash files concurrently, yielding (hash, path) tuples.

    This uses a ThreadPoolExecutor which is suitable for I/O bound hashing.
    """
    paths = list(paths)
    total = len(paths)
    if total == 0:
        return []

    lock = threading.Lock()
    done = 0

    def _worker(p: str) -> Optional[Tuple[str, str]]:
        try:
            h = _hash_file(Path(p), algo=algo)
            return (h, p)
        except Exception as e:
            _LOG.debug("Hash failed for %s: %s", p, e)
            return None

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_worker, p) for p in paths]
        for fut in concurrent.futures.as_completed(futures):
            try:
                res = fut.result()
            except Exception as e:
                _LOG.debug("Worker exception: %s", e)
                res = None
            with lock:
                done += 1
                if show_progress:
                    print(f"Hashed {done}/{total}", end='\r')
            if res:
                results.append(res)
    if show_progress:
        print()
    return results


def choose_to_delete(group: List[str], strategy: str = "keep-first") -> List[str]:
    if not group:
        return []
    if strategy == "keep-first":
        return group[1:]
    if strategy == "keep-largest":
        sizes = [(Path(p).stat().st_size, p) for p in group]
        sizes.sort(reverse=True)
        keep = sizes[0][1]
        return [p for _, p in sizes if p != keep]
    if strategy == "keep-newest":
        times = [(Path(p).stat().st_mtime, p) for p in group]
        times.sort(reverse=True)
        keep = times[0][1]
        return [p for _, p in times if p != keep]
    return []


def delete_files(paths: Iterable[str], trash_dir: Optional[Path] = None, permanent: bool = False, dry_run: bool = False) -> List[dict]:
    """Delete (or move to trash) the given files safely.

    Returns list of action dicts with keys: path, action, dest (if moved).
    """
    actions = []
    if trash_dir is None:
        trash_dir = Path.home() / ".fm_trash"
    trash_dir = Path(trash_dir)
    trash_dir.mkdir(parents=True, exist_ok=True)
    for p in paths:
        src = Path(p)
        if not src.exists():
            actions.append({"path": p, "action": "missing"})
            continue
        if dry_run:
            actions.append({"path": p, "action": "dry-run"})
            continue
        try:
            if permanent:
                src.unlink()
                actions.append({"path": p, "action": "deleted"})
            else:
                dest = trash_dir / f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{src.name}"
                shutil.move(str(src), str(dest))
                actions.append({"path": p, "action": "moved", "dest": str(dest)})
        except Exception as e:
            _LOG.exception("Failed to delete %s", p)
            actions.append({"path": p, "action": "error", "error": str(e)})
    return actions
