#!/usr/bin/env python3
"""Clip-on cap for the top of the sled's sensor post: holds the three jumper sockets down on the hall sensor's legs.

    python3 tools/wire_clip.py [out_dir]      # writes sled-wire-clip.stl (print orientation) and checks it on the V45 sled

The hall sensor sits in the post's front face with its legs up; the three jumper sockets (2.54 mm square, about
14 mm long) are pushed onto the legs and folded back flat along the top of the post. Nothing held them there, so
a tug on the wires pulled them off. The cap drops over them from above:

  * a 3.4 mm high channel over the sockets (they can't lift off the legs);
  * a lip at the back that comes down to 2 mm above the post: the wires pass under it, the sockets can't
    (they can't slide back off the legs);
  * two skirts down the sides of the post with a 0.3 mm ridge each: they spring over the post and grip it.
    A friction fit, since the post has nothing to hook under. Nothing hangs over the post's front face,
    where the blade is.

Printed upside down (roof on the bed), no supports. Model coordinates as tools/back_gate.py (sled at home):
the post is x -22..-2.5, z -7..7, top at y 68.
"""
import sys, math, pathlib
import numpy as np, trimesh
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
_a, sys.argv = sys.argv, sys.argv[:1]
from back_gate import M, T, box3, vol, STL      # noqa: E402
sys.argv = _a

X0, X1, HALF, TOP = -22.0, -2.5, 7.0, 68.0      # the post
FIT, SKIRT_T, SKIRT_L = 0.15, 1.6, 12.0
CH_HALF, CH_H, ROOF = 4.3, 3.4, 1.6             # channel for three sockets side by side (7.62 wide, 2.54 high)
LIP_X, LIP_GAP = 1.6, 2.0
RIDGE = 0.3


def build():
    zo = HALF + FIT + SKIRT_T
    body = box3(X0, X1, TOP, TOP + CH_H + ROOF, -zo, zo)
    body = body - box3(X0 + LIP_X, X1 + 0.1, TOP - 0.1, TOP + CH_H, -CH_HALF, CH_HALF)        # the channel, open at the front
    body = body - box3(X0 - 0.1, X0 + LIP_X + 0.1, TOP - 0.1, TOP + LIP_GAP, -CH_HALF, CH_HALF)   # under the back lip: wires only
    for s in (1, -1):
        z0, z1 = sorted((s * (HALF + FIT), s * zo))
        body = body + box3(X0, X1, TOP - SKIRT_L, TOP + 0.1, z0, z1)
        r0, r1 = sorted((s * (HALF - RIDGE), s * (HALF + FIT + 0.05)))
        body = body + box3(X0 + 3.0, X1 - 3.0, TOP - SKIRT_L + 1.0, TOP - SKIRT_L + 2.6, r0, r1)   # grip ridge near the skirt's end
    return body


def to_print(t):
    m = t.copy(); v = m.vertices.copy()
    m.vertices = np.column_stack([v[:, 0], v[:, 2], -v[:, 1]])      # roof down
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    return m


def main():
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else STL
    c = build(); t = T(c)
    sled = trimesh.load(STL / "v45" / "v45-sled.stl", force="mesh"); v = sled.vertices.copy()
    sled.vertices = np.column_stack([v[:, 2] - 22.0, v[:, 1] + 36.5, -v[:, 0]])
    blade = trimesh.load(STL / "v45" / "v45-blade.stl", force="mesh"); v = blade.vertices.copy()
    blade.vertices = np.column_stack([v[:, 2] + 2.1, v[:, 1] + 43.5, -v[:, 0]])
    grip = vol(c ^ M(sled))
    expect = 2 * RIDGE * (X1 - X0 - 6.0) * 1.6
    bl = vol(c ^ M(blade))
    gap = -trimesh.proximity.signed_distance(t, blade.sample(4000)).max()
    ok = t.is_watertight and len(t.split(only_watertight=False)) == 1 and abs(grip - expect) < 0.6 and bl < 0.01 and gap >= 1.0
    print(f"watertight {t.is_watertight}; overlaps the post only at the two grip ridges: {grip:.2f} mm3 (ridges are {expect:.2f}); blade overlap {bl:.3f} mm3, closest {gap:.1f} mm")
    p = to_print(t)
    z0 = p.bounds[0][2]; bed = p.area_faces[(p.face_normals[:, 2] < -0.99) & (np.abs(p.triangles_center[:, 2] - z0) < 0.02)].sum()
    print(f"print size {np.round(p.extents, 1)} mm, {bed:.0f} mm2 on the bed")
    out.mkdir(parents=True, exist_ok=True); p.export(out / "sled-wire-clip.stl"); print("wrote", out / "sled-wire-clip.stl")
    if not ok: sys.exit("check failed")


if __name__ == "__main__":
    main()
