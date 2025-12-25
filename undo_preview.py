#!/usr/bin/env python3
r"""undo_preview.py

Safely preview or apply an organizer undo log created by the GUI.

Usage examples:
  # preview only (safe)
  python undo_preview.py "C:\Users\Enyasystem\Downloads\New folder\fm_organize_20251225T051538Z.json"

  # actually perform restore (will move files)
  python undo_preview.py "...fm_organize_...json" --apply

By default the script runs in dry-run mode and only prints what would be
restored. Use `--apply` to perform the undo (use with caution).
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

try:
    from file_manager.organizer import undo_moves
except Exception as e:
    print("Failed to import file_manager.organizer:", e, file=sys.stderr)
    raise


def summarize(results: list[dict]) -> dict:
    summary = {"total": len(results), "restored": 0, "missing": 0, "dry-run": 0, "error": 0}
    for r in results:
        s = r.get("status")
        if s == "restored":
            summary["restored"] += 1
        elif s == "missing":
            summary["missing"] += 1
        elif s == "dry-run":
            summary["dry-run"] += 1
        elif s == "error":
            summary["error"] += 1
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Preview or apply undo for fm_organize logs")
    p.add_argument("log", help="Path to fm_organize_*.json log file")
    p.add_argument("--apply", action="store_true", help="Perform the undo (moves files). Dangerous")
    p.add_argument("--show", type=int, default=20, help="How many entries to show in the preview")
    args = p.parse_args(argv)

    logp = Path(args.log)
    if not logp.exists():
        print(f"Log file not found: {logp}", file=sys.stderr)
        return 2

    dry = not args.apply
    print(f"Running undo preview on: {logp}")
    print(f"Mode: {'DRY-RUN (preview)' if dry else 'APPLY (will move files)'}")

    try:
        results = undo_moves(logp, dry_run=dry)
    except Exception as e:
        print("undo_moves raised an exception:", e, file=sys.stderr)
        return 3

    summary = summarize(results)
    print(json.dumps(summary, indent=2))

    to_show = results[: args.show]
    if to_show:
        print('\nSample entries:')
        print(json.dumps(to_show, indent=2))

    if not dry:
        moved = sum(1 for r in results if r.get("status") == "restored")
        print(f"\nRestore completed, restored entries: {moved}")
    else:
        print("\nPreview only. Use --apply to perform the restore.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
