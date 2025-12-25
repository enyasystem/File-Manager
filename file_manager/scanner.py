"""Scanning utilities with optional EXIF/ID3 metadata extraction."""
from pathlib import Path
import os
import mimetypes
from typing import Iterable, Dict, Optional

# Optional dependencies for metadata extraction
try:
    from PIL import Image, ExifTags
    _HAS_PIL = True
except Exception:
    Image = None
    ExifTags = None
    _HAS_PIL = False

try:
    import mutagen
    _HAS_MUTAGEN = True
except Exception:
    mutagen = None
    _HAS_MUTAGEN = False


def scan_paths(paths: Iterable[Path], recursive: bool = True):
    """Yield metadata dicts for files under given paths.

    Each yielded dict includes keys: path, size, mtime, ctime, ext, mime, meta
    where `meta` contains optional extracted EXIF/ID3 information.
    """
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


def _extract_image_exif(path: Path) -> Dict:
    """Return a small dict of useful EXIF fields if available.

    Gracefully returns empty dict if Pillow is not available or image has no EXIF.
    """
    if not _HAS_PIL:
        return {}
    try:
        with Image.open(path) as img:
            exif = img._getexif() or {}
            if not exif:
                return {}
            out = {}
            for tag_id, value in exif.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                out[tag] = value
            # normalize common fields
            result = {}
            if "DateTimeOriginal" in out:
                result["datetime_original"] = out.get("DateTimeOriginal")
            elif "DateTime" in out:
                result["datetime"] = out.get("DateTime")
            if "Make" in out:
                result["camera_make"] = out.get("Make")
            if "Model" in out:
                result["camera_model"] = out.get("Model")
            # GPS info is nested; keep raw if present
            if "GPSInfo" in out:
                result["gps"] = out.get("GPSInfo")
            return result
    except Exception:
        return {}


def _extract_audio_tags(path: Path) -> Dict:
    """Return a small dict of useful audio tags (ID3, etc).

    Gracefully returns empty dict if `mutagen` is not available or file has no tags.
    """
    if not _HAS_MUTAGEN:
        return {}
    try:
        af = mutagen.File(str(path), easy=True)
        if not af or not getattr(af, "tags", None):
            return {}
        tags = {}
        # easy keys: artist, album, title, date, tracknumber
        for k in ("artist", "album", "title", "date", "tracknumber"):
            v = af.tags.get(k)
            if v:
                tags[k] = v[0] if isinstance(v, (list, tuple)) else v
        return tags
    except Exception:
        return {}


def _file_info(path: Path) -> Dict:
    stat = path.stat()
    mime, _ = mimetypes.guess_type(str(path))
    ext = path.suffix.lower().lstrip(".")
    meta: Dict = {}
    # attempt to extract image EXIF
    if ext in ("jpg", "jpeg", "tiff", "tif", "png"):
        meta = _extract_image_exif(path)
    # attempt to extract audio tags
    elif ext in ("mp3", "flac", "m4a", "wav", "aac"):
        meta = _extract_audio_tags(path)

    return {
        "path": str(path),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "ctime": stat.st_ctime,
        "ext": ext,
        "mime": mime or "unknown",
        "meta": meta,
    }
