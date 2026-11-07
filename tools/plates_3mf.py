#!/usr/bin/env python3
"""Pack the print-oriented STLs into one 3MF, grouped by plate, for a 180 x 180 bed.

    python3 tools/plates_3mf.py [out.3mf]
    python3 tools/plates_3mf.py --split [out_dir]   # one 3MF per plate, each on its own bed

The --split files are the safer ones: some Bambu Studio versions crash opening a
single file with objects spread ~1 m along X.

Plates sit side by side 200 mm apart in X. Open the file in Bambu Studio and
each group lands on its own plate (add plates with the + button if it shows
only one, or press A to arrange). TPU parts are on their own plate.
"""
import sys
import pathlib
import numpy as np
import trimesh

ROOT = pathlib.Path(__file__).resolve().parent.parent
STL = ROOT / "hardware" / "stl"
BED = 180.0
STRIDE = 200.0

# plate -> (file, centre x, centre y, rotation about Z in degrees)
PLATES = {
    1: [("base.stl", 90, 90, 0)],
    2: [("nest.stl", 68, 43, 0), ("blade.stl", 150, 110, 0),
        ("thumbscrew-knob.stl", 150, 30, 0), ("servo-horn-v2.stl", 150, 60, 0)],
    3: [("u-yoke.stl", 90, 30, 0), ("sled.stl", 60, 95, 0), ("lead-screw-TR10x2.stl", 120, 95, 0)],
    4: [("nest-liner-TPU.stl", 65, 45, 0), ("pad-TPU.stl", 150, 45, 0)],
    # the two electronics boxes (the ESP32 case is BTL's v6 case, printed as supplied)
    5: [("esp32-case/esp32-case-base.stl", 25, 36, 0), ("esp32-case/esp32-case-lid-firm-key.stl", 25, 102, 0),
        ("driver-box.stl", 75, 32, 0), ("driver-box-lid.stl", 75, 88, 0),
        ("esp32-case/esp32-case-keycap.stl", 125, 30, 0), ("esp32-case/esp32-case-mx-adapter-1.25.stl", 125, 55, 0),
        ("esp32-case/esp32-case-mx-adapter-1.30.stl", 125, 72, 0), ("esp32-case/esp32-case-mx-adapter-1.35.stl", 125, 89, 0)],
}


def main():
    split = "--split" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = pathlib.Path(args[0]) if args else (STL / "plates" if split else STL / "ripeomatic-all-parts.3mf")
    scene = trimesh.Scene()
    scenes = {}
    boxes = {}
    for k, items in PLATES.items():
        for name, cx, cy, rot in items:
            m = trimesh.load(STL / name, force="mesh")
            label = pathlib.Path(name).stem
            if rot:
                m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 0, 1]))
            lo, hi = m.bounds
            m.apply_translation([(k - 1) * STRIDE + cx - (lo[0] + hi[0]) / 2, cy - (lo[1] + hi[1]) / 2, -lo[2]])
            scene.add_geometry(m, node_name=label, geom_name=label)
            mp = m.copy(); mp.apply_translation([-(k - 1) * STRIDE, 0, 0])
            scenes.setdefault(k, trimesh.Scene()).add_geometry(mp, node_name=label, geom_name=label)
            lo, hi = m.bounds
            boxes.setdefault(k, []).append((label, lo[0] - (k - 1) * STRIDE, hi[0] - (k - 1) * STRIDE, lo[1], hi[1]))
    ok = True
    for k, bl in boxes.items():
        for n, x0, x1, y0, y1 in bl:
            mg = 0.5 if n == "base" else 2
            if not (x0 >= mg and x1 <= BED - mg and y0 >= mg and y1 <= BED - mg):
                ok = False; print(f"plate {k}: {n} is outside the bed [{x0:.0f}-{x1:.0f}, {y0:.0f}-{y1:.0f}]")
        for i in range(len(bl)):
            for j in range(i + 1, len(bl)):
                a, b = bl[i], bl[j]
                gap = max(a[1] - b[2], b[1] - a[2], a[3] - b[4], b[3] - a[4])
                if gap < 4:
                    ok = False; print(f"plate {k}: {a[0]} and {b[0]} are {gap:.1f} mm apart")
        print(f"plate {k}: " + ", ".join(f"{n} [{x0:.0f}-{x1:.0f}, {y0:.0f}-{y1:.0f}]" for n, x0, x1, y0, y1 in bl))
    if not ok:
        sys.exit(1)
    if split:
        out.mkdir(parents=True, exist_ok=True)
        names = {1: "base", 2: "nest-blade-knob-horn", 3: "yoke-sled-screw", 4: "TPU-liner-pad", 5: "electronics-boxes"}
        for k, sc in scenes.items():
            f = out / f"plate{k}-{names.get(k, k)}.3mf"
            sc.export(f)
            print(f"wrote {f} ({f.stat().st_size // 1024} kB, {len(sc.geometry)} objects)")
        return
    scene.export(out)
    print(f"wrote {out} ({out.stat().st_size // 1024} kB, {len(trimesh.load(out).geometry)} objects)")


if __name__ == "__main__":
    main()
