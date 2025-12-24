"""Reporting utilities"""
import json
from pathlib import Path
import csv

def generate_report(scan_json: Path | None, out: Path | None):
    data = None
    if scan_json and scan_json.exists():
        with scan_json.open("r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        print("No scan JSON provided or file not found")
        return
    summary = {
        "files": len(data),
        "total_bytes": sum(item.get("size", 0) for item in data),
    }
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            json.dump({"summary": summary, "files": data}, f, indent=2)
        csvp = out.with_suffix(".csv")
        with csvp.open("w", newline="", encoding="utf-8") as cf:
            writer = csv.writer(cf)
            writer.writerow(["path", "size", "mtime", "ctime", "ext", "mime"])
            for item in data:
                writer.writerow([item.get(k, "") for k in ("path", "size", "mtime", "ctime", "ext", "mime")])
        print(f"Wrote report to {out} and {csvp}")
