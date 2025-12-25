#!/usr/bin/env python3
"""Simple File Manager CLI"""
import argparse
import json
import sys
from pathlib import Path

from file_manager import scanner, organizer, deduper, reporter

def cmd_scan(args):
    paths = [Path(p) for p in args.paths]
    files = list(scanner.scan_paths(paths, recursive=not args.no_recursive))
    print(f"Found {len(files)} files")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(files, f, default=str, indent=2)
        print(f"Saved scan to {args.out}")

def cmd_organize(args):
    paths = [Path(p) for p in args.paths]
    files = list(scanner.scan_paths(paths, recursive=not args.no_recursive))
    actions = []
    if args.by == "type":
        actions = organizer.organize_by_type(files, Path(args.target), dry_run=args.dry_run)
    else:
        actions = organizer.organize_by_date(files, Path(args.target), dry_run=args.dry_run)
    print(f"Planned {len(actions)} moves")
    if actions and not args.dry_run:
        print("Moves applied.")

def cmd_dedupe(args):
    paths = [Path(p) for p in args.paths]
    files = list(scanner.scan_paths(paths, recursive=not args.no_recursive))
    groups = deduper.find_duplicates([f["path"] for f in files], algo=args.algo)
    if not groups:
        print("No duplicates found.")
        return
    print(f"Found {len(groups)} duplicate groups")
    for i, grp in enumerate(groups, 1):
        print(f"Group {i}: {len(grp)} files")
        for idx, p in enumerate(grp, start=1):
            print(f"  [{idx}] {p}")
        if args.auto:
            to_delete = deduper.choose_to_delete(grp, strategy=args.auto)
            if to_delete:
                print(f"Auto-resolving {len(to_delete)} files (strategy={args.auto})")
                actions = deduper.delete_files(to_delete, permanent=args.permanent, dry_run=args.dry_run)
                for a in actions:
                    print("  ", a)
        else:
            resp = input("Enter comma-separated indexes to delete (or blank to skip): ")
            if resp.strip():
                idxs = [int(x.strip()) for x in resp.split(",") if x.strip().isdigit()]
                selected = []
                for idx in idxs:
                    if 1 <= idx <= len(grp):
                        selected.append(grp[idx - 1])
                if selected:
                    confirm_all = args.yes or input(f"Delete {len(selected)} files? [y/N] ") in ("y", "Y")
                    if confirm_all:
                        actions = deduper.delete_files(selected, permanent=args.permanent, dry_run=args.dry_run)
                        for a in actions:
                            print("  ", a)

def cmd_report(args):
    reporter.generate_report(Path(args.scan) if args.scan else None, Path(args.out) if args.out else None)

def main():
    parser = argparse.ArgumentParser(prog="file-manager")
    sub = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan")
    p_scan.add_argument("paths", nargs="+", help="Paths to scan")
    p_scan.add_argument("--no-recursive", action="store_true")
    p_scan.add_argument("--out", help="Write JSON scan output")
    p_scan.set_defaults(func=cmd_scan)

    p_org = sub.add_parser("organize")
    p_org.add_argument("paths", nargs="+", help="Paths to organize")
    p_org.add_argument("--target", required=True, help="Target root to place organized files")
    p_org.add_argument("--by", choices=("type", "date"), default="type")
    p_org.add_argument("--dry-run", action="store_true")
    p_org.add_argument("--no-recursive", action="store_true")
    p_org.set_defaults(func=cmd_organize)

    p_undo = sub.add_parser("undo")
    p_undo.add_argument("log", help="Path to an organizer log JSON file to undo")
    p_undo.add_argument("--dry-run", action="store_true")
    p_undo.set_defaults(func=lambda args: print('\n'.join(str(x) for x in organizer.undo_moves(Path(args.log), dry_run=args.dry_run))))

    p_dup = sub.add_parser("dedupe")
    p_dup.add_argument("paths", nargs="+", help="Paths to scan for duplicates")
    p_dup.add_argument("--algo", choices=("md5", "sha256"), default="sha256")
    p_dup.add_argument("--auto", choices=("keep-newest", "keep-largest", "keep-first"), help="Auto-resolve duplicates")
    p_dup.add_argument("--yes", action="store_true", help="Answer yes to all prompts")
    p_dup.add_argument("--no-recursive", action="store_true")
    p_dup.add_argument("--permanent", action="store_true", help="Permanently delete files (default moves to trash)")
    p_dup.add_argument("--dry-run", action="store_true", help="Don't perform deletions; show planned actions")
    p_dup.add_argument("--workers", type=int, default=4, help="Number of worker threads for hashing")
    p_dup.add_argument("--progress", action="store_true", help="Show hashing progress")
    p_dup.set_defaults(func=cmd_dedupe)

    p_rep = sub.add_parser("report")
    p_rep.add_argument("--scan", help="Path to JSON scan output to base report on")
    p_rep.add_argument("--out", help="Output path for report (JSON)")
    p_rep.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    args.func(args)

if __name__ == "__main__":
    main()
