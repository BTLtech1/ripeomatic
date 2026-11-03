#!/usr/bin/env python3
"""Write data/sample/sample.csv: SYNTHETIC readings for trying the dashboard and the merge script.

Not real avocados. device_id 000000 so it can never be mistaken for a contribution
(the merge script only reads data/contrib/). Deterministic: same output every run.
"""
import csv
import math
import pathlib
import random
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sample" / "sample.csv"
COLUMNS = [
    "schema", "device_id", "fw_version", "hw_version", "timestamp", "fruit_id", "variety", "fruit_mass_g", "room_temp_c",
    "contact_pos_mm", "stiffness_n_per_mm", "squish_at_cap_mm", "force_cap_n", "blade_k_n_per_mm", "cal_points", "curve",
    "human_rating", "cut_open", "notes",
]

rng = random.Random(7)
DEV = "000000"
start = datetime(2026, 11, 1, 7, 30, tzinfo=timezone.utc)
# (first stiffness N/mm, days to ripe at 20 C, room temp, mass g, what happened)
fruits = [
    (6.2, 5.0, 21.0, 185, "ate_perfect"),
    (4.1, 3.0, 22.5, 170, "ate_perfect"),
    (7.0, 7.5, 18.0, 210, "overripe"),
    (5.4, 4.5, 20.0, 160, "in_progress"),
]
RIPE_K = 2.2   # where these synthetic fruits are "perfect"

rows = []
t = start
for i, (k0, days20, temp, mass, fate) in enumerate(fruits, start=1):
    fid = f"{DEV}-{i:04d}"
    # exponential decay to RIPE_K in `days` at this temperature (2x per 10 C)
    days = days20 * 2 ** ((20 - temp) / 10)
    rate = math.log(k0 / RIPE_K) / days
    contact = 20 + rng.uniform(-3, 3)
    n_readings = int(days * 2) + (4 if fate == "overripe" else 1)
    if fate == "in_progress":
        n_readings = int(days * 2 * 0.6)
    rated_firm = False
    for r in range(n_readings):
        ts = t + timedelta(hours=12 * r + rng.uniform(-0.3, 0.3))
        d = (ts - t).total_seconds() / 86400
        k = k0 * math.exp(-rate * d) * (1 + rng.gauss(0, 0.03))
        squish = 2.3 / k
        pts = [(s, 0.2 + k * s) for s in [j * squish / 20 for j in range(21)]]
        curve = ";".join(f"{s:.2f}:{f:.2f}" for s, f in pts)
        rows.append([1, DEV, "0.1.0", "v1", ts.strftime("%Y-%m-%dT%H:%M:%SZ"), fid, "hass", mass, f"{temp + rng.uniform(-0.5, 0.5):.1f}",
                     f"{contact + rng.uniform(-0.2, 0.2):.2f}", f"{k:.3f}", f"{squish:.2f}", "2.50", "3.10", "0:0;100.0:2281;200.0:2563", curve, "", "", ""])
        if not rated_firm and k < k0 * 0.7:
            rated_firm = True
            rows.append([1, DEV, "0.1.0", "v1", (ts + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), fid, "hass", "", "", "", "", "", "", "", "", "", "firm", "", "thumb test"])
    last_ts = t + timedelta(hours=12 * (n_readings - 1))
    if fate == "ate_perfect":
        rows.append([1, DEV, "0.1.0", "v1", (last_ts + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"), fid, "hass", "", "", "", "", "", "", "", "", "", "perfect", "no_bruise", "guacamole"])
    elif fate == "overripe":
        rows.append([1, DEV, "0.1.0", "v1", (last_ts + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"), fid, "hass", "", "", "", "", "", "", "", "", "", "overripe", "bruise_elsewhere", "forgot about it"])
    t = last_ts + timedelta(hours=20)

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(COLUMNS)
    w.writerows(rows)
print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} rows, {len(fruits)} synthetic fruit")
