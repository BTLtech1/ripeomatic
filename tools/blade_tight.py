#!/usr/bin/env python3
"""Tighter-fitting stiff blades: v45-blade-stiff.stl with its foot thickened so it cannot lean in the sled.

    python3 tools/blade_tight.py        # writes v45-blade-stiff-snug.stl (+0.10 mm), -tight.stl (+0.20) and -xtight.stl (+0.30)

Why: the blade's foot sits only about 7 mm deep in the sled's pocket, with about 0.25 mm of clearance front to
back. That much play over 7 mm lets the top of the blade, 40 mm up, lean about 1 mm toward the sensor post,
out of a 1.5 mm gap. On a real unit the blade rested at 1210 counts instead of the 1500 it reads upright, so
40% of the force range was gone before a press started, and the rest position drifted.

The foot (everything below the top of the pocket) is made thicker front to back; the back face stays flat on
the bed. Print all three, and use the tightest one that pushes in by hand. Only the blade changes: the sled, and a
sensor glued into it, stay as they are. Redo the force and blade calibrations afterwards.
"""
import pathlib, sys
import numpy as np, trimesh

STL = pathlib.Path(__file__).resolve().parent.parent / "hardware" / "stl" / "v45"
Y_FOOT_TOP = -17.6      # print y: the foot is everything below this (the pocket's top edge)
LEG_T = 4.4             # print z: thickness of the foot's legs


def build(extra):
    b = trimesh.load(STL / "v45-blade-stiff.stl", force="mesh")
    v = b.vertices.copy()
    foot = v[:, 1] <= Y_FOOT_TOP
    v[foot, 2] += extra * np.clip(v[foot, 2] / LEG_T, 0.0, 1.0)     # bed face stays put; the front of the foot moves out
    b.vertices = v
    return b


def in_model(m):
    m = m.copy(); v = m.vertices.copy()
    m.vertices = np.column_stack([v[:, 2] + 2.1, v[:, 1] + 43.5, -v[:, 0]])
    return m


def main():
    sled = trimesh.load(STL / "v45-sled.stl", force="mesh"); s = sled.vertices.copy()
    sled.vertices = np.column_stack([s[:, 2] - 22.0, s[:, 1] + 36.5, -s[:, 0]])
    base = trimesh.load(STL / "v45-blade-stiff.stl", force="mesh")
    i0 = trimesh.boolean.intersection([in_model(base), sled], engine="manifold").volume
    ok = True
    for name, extra in (("snug", 0.10), ("tight", 0.20), ("xtight", 0.30)):
        t = build(extra)
        i = trimesh.boolean.intersection([in_model(t), sled], engine="manifold").volume
        good = t.is_watertight and t.volume > base.volume and i < 12.0
        ok &= good
        print(f"{name}: foot +{extra:.2f} mm, watertight {t.is_watertight}, volume +{t.volume - base.volume:.1f} mm3, "
              f"squeeze into the sled {i:.2f} mm3 (stock fit: {i0:.2f})" + ("" if good else "  CHECK FAILED"))
        t.export(STL / f"v45-blade-stiff-{name}.stl")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
