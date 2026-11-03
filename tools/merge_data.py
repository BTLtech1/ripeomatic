#!/usr/bin/env python3
"""Validate contributed readings and merge them into data/all.csv.

    python3 tools/merge_data.py            # validate + write data/all.csv
    python3 tools/merge_data.py --check    # validate only (CI on pull requests)

Layout: data/contrib/<device_id>/*.csv, each in schema v1 (docs/data-sharing.md).
Rules:
  - header must be exactly the schema v1 columns
  - every row's device_id must match the folder name, and fruit_id must start with it
  - timestamps are ISO 8601 UTC ("...Z") or blank
  - numeric columns parse as numbers or are blank
  - human_rating / cut_open use the fixed vocabularies
Rows are de-duplicated on (device_id, fruit_id, timestamp, stiffness, human_rating).
"""
import argparse
import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRIB = ROOT / "data" / "contrib"
OUT = ROOT / "data" / "all.csv"

COLUMNS = [
    "schema", "device_id", "fw_version", "hw_version", "timestamp", "fruit_id", "variety", "fruit_mass_g", "room_temp_c",
    "contact_pos_mm", "stiffness_n_per_mm", "squish_at_cap_mm", "force_cap_n", "blade_k_n_per_mm", "cal_points", "curve",
    "human_rating", "cut_open", "notes",
]
NUMERIC = ["fruit_mass_g", "room_temp_c", "contact_pos_mm", "stiffness_n_per_mm", "squish_at_cap_mm", "force_cap_n", "blade_k_n_per_mm"]
RATINGS = {"", "hard", "firm", "ready", "perfect", "overripe"}
CUTS = {"", "no_bruise", "bruise_at_pad", "bruise_elsewhere"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
DEVICE = re.compile(r"^[0-9a-f]{6}$")
CURVE = re.compile(r"^(-?\d+(\.\d+)?:-?\d+(\.\d+)?)(;-?\d+(\.\d+)?:-?\d+(\.\d+)?)*$")


def validate_file(path: pathlib.Path, device: str, errors: list) -> list:
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            errors.append(f"{path}: empty file")
            return rows
        if header != COLUMNS:
            errors.append(f"{path}: header is not schema v1\n  got:      {header}\n  expected: {COLUMNS}")
            return rows
        for ln, r in enumerate(reader, start=2):
            if not any(r):
                continue
            if len(r) != len(COLUMNS):
                errors.append(f"{path}:{ln}: {len(r)} columns, expected {len(COLUMNS)}")
                continue
            d = dict(zip(COLUMNS, r))
            where = f"{path}:{ln}"
            if d["schema"] != "1":
                errors.append(f"{where}: schema {d['schema']!r}, only 1 is known")
            if d["device_id"] != device:
                errors.append(f"{where}: device_id {d['device_id']!r} does not match folder {device!r}")
            if not d["fruit_id"].startswith(device + "-"):
                errors.append(f"{where}: fruit_id {d['fruit_id']!r} should start with {device}-")
            if d["timestamp"] and not ISO.match(d["timestamp"]):
                errors.append(f"{where}: timestamp {d['timestamp']!r} is not ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ)")
            for c in NUMERIC:
                if d[c]:
                    try:
                        float(d[c])
                    except ValueError:
                        errors.append(f"{where}: {c}={d[c]!r} is not a number")
            if d["human_rating"] not in RATINGS:
                errors.append(f"{where}: human_rating {d['human_rating']!r} not in {sorted(RATINGS - {''})}")
            if d["cut_open"] not in CUTS:
                errors.append(f"{where}: cut_open {d['cut_open']!r} not in {sorted(CUTS - {''})}")
            if d["curve"] and not CURVE.match(d["curve"]):
                errors.append(f"{where}: curve is not 'squish:force;squish:force;...'")
            is_reading = d["stiffness_n_per_mm"] != ""
            if not is_reading and not d["human_rating"] and not d["notes"]:
                errors.append(f"{where}: neither a reading (stiffness) nor an event (human_rating/notes)")
            if is_reading and (d["force_cap_n"] == "" or d["contact_pos_mm"] == ""):
                errors.append(f"{where}: a reading needs contact_pos_mm and force_cap_n")
            rows.append(d)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate only, do not write data/all.csv")
    a = ap.parse_args()

    errors: list = []
    all_rows: list = []
    seen = set()
    n_files = 0
    if CONTRIB.exists():
        for devdir in sorted(p for p in CONTRIB.iterdir() if p.is_dir()):
            device = devdir.name
            if not DEVICE.match(device):
                errors.append(f"{devdir}: folder name must be the 6-hex-char device id")
                continue
            for path in sorted(devdir.glob("*.csv")):
                n_files += 1
                for d in validate_file(path, device, errors):
                    key = (d["device_id"], d["fruit_id"], d["timestamp"], d["stiffness_n_per_mm"], d["human_rating"])
                    if key in seen:
                        continue
                    seen.add(key)
                    all_rows.append(d)

    all_rows.sort(key=lambda d: (d["device_id"], d["fruit_id"], d["timestamp"]))
    devices = {d["device_id"] for d in all_rows}
    fruits = {d["fruit_id"] for d in all_rows}
    readings = sum(1 for d in all_rows if d["stiffness_n_per_mm"])
    ratings = sum(1 for d in all_rows if d["human_rating"])
    print(f"{n_files} file(s), {len(devices)} device(s), {len(fruits)} fruit(s), {readings} reading(s), {ratings} rating(s)")

    if errors:
        print(f"\n{len(errors)} problem(s):")
        for e in errors:
            print("  " + e)
        return 1

    if not a.check:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(all_rows)
        print(f"wrote {OUT.relative_to(ROOT)} ({len(all_rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
