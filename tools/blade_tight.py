#!/usr/bin/env python3
"""Tighter-fitting stiff blades: v45-blade-stiff.stl with its foot thickened so it cannot lean in the sled.

    python3 tools/blade_tight.py        # writes v45-blade-stiff-snug.stl (+0.10 mm), -tight.stl (+0.20) and -xtight.stl (+0.30)

Why: the blade's foot sits only about 7 mm deep in the sled's pocket, with about 0.25 mm of clearance front to
back. That much play over 7 mm lets the top of the blade, 40 mm up, lean about 1 mm toward the sensor post,
out of a 1.5 mm gap. On a real unit the blade rested at 1210 counts instead of the 1500 it reads upright, so
40% of the force range was gone before a press started, and the rest position drifted.

The foot (everything below the top of the pocket) is made thicker front to back; the back face stays flat on
the bed. Each has a raised digit on its front face: 1, 2 or 3, for +0.1, +0.2, +0.3 mm. Print all three, and use the
tightest one that pushes in by hand. Only the blade changes: the sled, and a
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


def labelled(b, digit):
    z_front = float(b.section(plane_origin=[0, -4.0, 0], plane_normal=[0, 1, 0]).bounds[1][2])   # the plate's front face here
    return trimesh.boolean.union([b] + label(digit, z_front), engine="manifold")


SEG = {"1": "bc", "2": "abged", "3": "abgcd"}     # seven-segment digits: no font needed, and every stroke prints


def label(digit, z0, h=0.6):
    """a raised digit on the plate's front face: strokes 1.0 mm wide (two passes of a 0.4 mm nozzle and a bit), 0.6 mm tall"""
    w, hh, t, cy = 5.0, 9.0, 1.0, -4.0          # digit 5 x 9 mm, centred on the plate, clear of the foot and the stem
    x0, x1, yb, ym, yt = -w / 2, w / 2, cy - hh / 2, cy, cy + hh / 2
    seg = {"a": (x0, x1, yt - t, yt), "g": (x0, x1, ym - t / 2, ym + t / 2), "d": (x0, x1, yb, yb + t),
           "f": (x0, x0 + t, ym, yt), "b": (x1 - t, x1, ym, yt), "e": (x0, x0 + t, yb, ym), "c": (x1 - t, x1, yb, ym)}
    boxes = []
    for k in SEG[digit]:
        a, b, c, d = seg[k]
        bx = trimesh.creation.box(extents=[b - a, d - c, h + 0.2])
        bx.apply_translation([(a + b) / 2, (c + d) / 2, z0 - 0.2 + (h + 0.2) / 2])     # sunk 0.2 mm into the plate so it fuses
        boxes.append(bx)
    return boxes


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
    for name, extra, digit in (("snug", 0.10, "1"), ("tight", 0.20, "2"), ("xtight", 0.30, "3")):
        plain = build(extra)
        t = labelled(plain, digit)
        i = trimesh.boolean.intersection([in_model(t), sled], engine="manifold").volume
        assert t.bounds[1][2] <= plain.bounds[1][2] + 1e-6 and abs(t.bounds[0][2] - plain.bounds[0][2]) < 1e-6   # label adds nothing proud of the pad, nothing under the bed
        good = t.is_watertight and t.volume > base.volume and i < 12.0
        ok &= good
        print(f"{name} (marked {digit}): foot +{extra:.2f} mm, watertight {t.is_watertight}, volume +{t.volume - base.volume:.1f} mm3, "
              f"squeeze into the sled {i:.2f} mm3 (stock fit: {i0:.2f})" + ("" if good else "  CHECK FAILED"))
        t.export(STL / f"v45-blade-stiff-{name}.stl")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
