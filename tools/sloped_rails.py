"""Sloped rail lips: a matched base and sled that print without the drooping strands under the lips.

Each rail on the base holds the sled down with a lip that reaches 2 mm sideways over the channel. Its
underside was flat, so it printed over air and sagged. Here the underside is a 45-degree slope that the
printer can build, and the sled's shoulder gets the same slope with 0.6 mm above it.

    base-sloped-rails.stl        hardware/stl/base.stl with a wedge under each lip
    v45/v45-sled-sloped.stl      hardware/stl/v45/v45-sled.stl with its two top outer edges cut to match

They only work as a pair: a square-shouldered sled jams under the sloped lips. Not printed or tested yet.
"""
import sys
from pathlib import Path
import numpy as np, trimesh
from shapely.geometry import Polygon

STL = Path(__file__).resolve().parent.parent / "hardware" / "stl"
RAIL_Y = (-46.5, 49.5)        # the rails, along the base (print coords)
LIP_IN, LIP_OUT, LIP_UNDER = 18.0, 20.0, 11.0     # the lip: from the upright's face at 20 in to 18, underside at 11
GAP = 0.6                     # vertical room between the two slopes
SHOULDER = 19.7               # the sled's foot reaches this far out; its top is at 10.5 (model height)
SHOULDER_TOP = 10.5


def prism_xz(poly_xz, y0, y1):
    """extrude an (x across, height) outline along the base's length"""
    m = trimesh.creation.extrude_polygon(Polygon(poly_xz), y1 - y0)
    v = m.vertices.copy()
    m.vertices = np.column_stack([v[:, 0], v[:, 2] + y0, v[:, 1]])
    if m.volume < 0:
        m.invert()
    return m


def U(a, b): return trimesh.boolean.union([a, b], engine="manifold")
def D(a, b): return trimesh.boolean.difference([a, b], engine="manifold")
def I(a, b): return trimesh.boolean.intersection([a, b], engine="manifold")


def base():
    b = trimesh.load(STL / "base.stl", force="mesh")
    drop = LIP_OUT - LIP_IN
    for s in (-1, 1):
        # 0.05 into the upright and the lip so the union is one solid
        w = [(s * (LIP_OUT + 0.05), LIP_UNDER - drop), (s * (LIP_OUT + 0.05), LIP_UNDER + 0.05), (s * LIP_IN, LIP_UNDER + 0.05), (s * LIP_IN, LIP_UNDER)]
        b = U(b, prism_xz(w, *RAIL_Y))
    return b


def sled():
    s = trimesh.load(STL / "v45" / "v45-sled.stl", force="mesh")
    # sled print coords: x across, y = model height - 36.5, z along. The base's slope is height = 29 - |x|.
    line = lambda x: (LIP_UNDER + LIP_IN) - x - GAP
    x0 = (LIP_UNDER + LIP_IN) - GAP - SHOULDER_TOP          # where the cut meets the shoulder's top
    for sg in (-1, 1):
        cut = [(sg * x0, SHOULDER_TOP - 36.5), (sg * (SHOULDER + 0.5), line(SHOULDER + 0.5) - 36.5), (sg * (SHOULDER + 0.5), SHOULDER_TOP + 0.02 - 36.5), (sg * x0, SHOULDER_TOP + 0.02 - 36.5)]
        m = trimesh.creation.extrude_polygon(Polygon(cut), 60.0)
        m.apply_translation([0, 0, -5.0])
        s = D(s, m)
    return s


def in_model(sl, travel):
    """the sled in the base's print coords at a given travel (base print y = press axis - 20.5)"""
    m = sl.copy(); v = m.vertices.copy()
    # sled print (x, y, z) -> model (z - 22 + travel, y + 36.5, -x) -> base print (-x, model_x - 20.5, model_y)
    m.vertices = np.column_stack([-v[:, 0], v[:, 2] - 22.0 + travel - 20.5, v[:, 1] + 36.5])
    if m.volume < 0: m.invert()
    return m


def main():
    b, s = base(), sled()
    old_b, old_s = trimesh.load(STL / "base.stl", force="mesh"), trimesh.load(STL / "v45" / "v45-sled.stl", force="mesh")
    ok = True
    def flag(good, text):
        nonlocal ok; ok &= bool(good); print(("  ok  " if good else "  BAD ") + text)
    flag(b.is_watertight and s.is_watertight, "both parts are closed solids")
    flag(abs((b.volume - old_b.volume) - 2 * 0.5 * 2 * 2 * (RAIL_Y[1] - RAIL_Y[0])) < 15, f"base gained {b.volume - old_b.volume:.0f} mm3 (two wedges)")
    flag(0 < old_s.volume - s.volume < 250, f"sled lost {old_s.volume - s.volume:.0f} mm3 (two edges)")
    for t in (0.0, 21.0, 42.0, 46.0):
        v = I(b, in_model(s, t)).volume
        flag(v < 0.05, f"sloped sled in sloped base at travel {t:.0f}: overlap {v:.3f} mm3")
    v = I(old_b, in_model(old_s, 0.0)).volume
    flag(v < 0.05, f"(reference) stock sled in stock base: overlap {v:.3f} mm3")
    v = I(b, in_model(old_s, 0.0)).volume
    print(f"       a stock sled in the sloped base overlaps {v:.0f} mm3: it jams, as expected")
    # lift play: raise the sloped sled until it touches
    for lift in (0.5, 0.7):
        m = in_model(s, 21.0); m.apply_translation([0, 0, lift])
        print(f"       lifted {lift} mm: overlap {I(b, m).volume:.2f} mm3")
    for side in (0.25, 0.45):
        m = in_model(s, 21.0); m.apply_translation([side, 0, 0])
        print(f"       pushed {side} mm sideways: overlap {I(b, m).volume:.2f} mm3")
    b.export(STL / "base-sloped-rails.stl"); s.export(STL / "v45" / "v45-sled-sloped.stl")
    print("wrote base-sloped-rails.stl and v45/v45-sled-sloped.stl" + ("" if ok else "  (CHECKS FAILED)"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
