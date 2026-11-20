#!/usr/bin/env python3
"""Calibration stand: holds the machine upright on its motor end (pad pointing at the ceiling) for the force calibration.

    python3 tools/cal_stand.py [out_dir]      # writes cal-stand.stl (print orientation) and checks it against the base

The force calibration stacks weights on the pad, so the machine has to stand on end. On its own it balances on
the 5 mm edge of the base. The stand is a slot for that edge:

  * a floor the base's two corner ears rest on;
  * a 40 mm back plate behind the base's flat underside;
  * two 18 mm lips in front, either side of the motor (the deck is bare there for the first 18 mm);
  * two long feet: the pad and its weights are 62 mm in front of the base, so the feet run 125 mm forward.

The slot is 5.3 mm for the 5 mm base (0.15 mm a side): the machine leans less than 1 degree. Printed as it
stands, floor on the bed, no supports. 168 x 170 mm: it needs a 180 mm bed.

Model coordinates as the machine (x = toward the holder, y = up from the table, z = across); the base's motor
end is at x -68.5, its underside at y 0 and its deck at y 5.
"""
import sys, pathlib
import numpy as np, trimesh
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
_a, sys.argv = sys.argv, sys.argv[:1]
import back_gate as g                              # noqa: E402
from back_gate import M, T, box3, vol, prism, STL  # noqa: E402
sys.argv = _a

END = -68.5                 # the base's motor end
FLOOR, FIT = 4.0, 0.15
BACK_T, BACK_H, BACK_HALF = 4.0, 40.0, 70.0
LIP_T, LIP_H, LIP_Z = 5.0, 18.0, (30.0, 68.0)
HALF, FOOT_W = 84.0, 20.0
FOOT_BACK, FOOT_FRONT = 45.0, 125.0


def tri(x0, x1, pts_yx):
    """a triangular rib: polygon given as (y, x) points, extruded along z from x0 to x1 (x0, x1 are z here)"""
    p = prism([(q[1], q[0]) for q in pts_yx], x0, x1)      # prism extrudes an (x, y) polygon along z
    return p


def build():
    y_back0, y_back1 = -FIT - BACK_T, -FIT
    y_lip0, y_lip1 = 5.0 + FIT, 5.0 + FIT + LIP_T
    s = box3(END - FLOOR, END, y_back0, y_lip1, -HALF, HALF)                                  # floor under the base's end
    s = s + box3(END - 0.01, END + BACK_H, y_back0, y_back1, -BACK_HALF, BACK_HALF)           # back plate
    for sg in (1, -1):
        z0, z1 = sorted((sg * LIP_Z[0], sg * LIP_Z[1]))
        s = s + box3(END - 0.01, END + LIP_H, y_lip0, y_lip1, z0, z1)                         # front lip
        f0, f1 = sorted((sg * (HALF - FOOT_W), sg * HALF))
        s = s + box3(END - FLOOR, END, -FOOT_BACK, FOOT_FRONT, f0, f1)                        # foot
        # ribs: behind the back plate, and in front of each lip's two ends
        r0, r1 = sorted((sg * (BACK_HALF - 4.0), sg * BACK_HALF))
        s = s + tri(r0, r1, [(y_back0 + 0.01, END - 0.01), (y_back0 + 0.01, END + BACK_H - 4), (-FOOT_BACK + 6, END - 0.01)])
        for zc in (LIP_Z[0] + 2.0, LIP_Z[1] - 2.0):
            a, b = sorted((sg * (zc - 2.0), sg * (zc + 2.0)))
            s = s + tri(a, b, [(y_lip1 - 0.01, END - 0.01), (y_lip1 - 0.01, END + LIP_H - 2), (y_lip1 + 16, END - 0.01)])
    s = s + box3(END - FLOOR, END, FOOT_FRONT - 18.0, FOOT_FRONT, -HALF, HALF)               # cross bar joining the feet at the front
    return s


def main():
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else STL
    s = build(); t = T(s)
    base = g.build_base()
    hit = vol(s ^ base)
    lifted = vol(s ^ base.translate([-0.3, 0, 0]))          # pushed 0.3 mm into the floor: it must touch (it rests on the floor)
    p = t.copy(); v = p.vertices.copy(); p.vertices = np.column_stack([v[:, 2], v[:, 1], v[:, 0]]); p.invert()
    lo, hi = p.bounds; p.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    z0 = p.bounds[0][2]; bed = p.area_faces[(p.face_normals[:, 2] < -0.99) & (np.abs(p.triangles_center[:, 2] - z0) < 0.02)].sum()
    one = len(t.split(only_watertight=False))
    print(f"watertight {t.is_watertight}, {one} piece; overlap with the base {hit:.3f} mm3; pushed 0.3 mm down it overlaps {lifted:.1f} mm3 (it rests on the floor)")
    print(f"print size {np.round(p.extents, 1)} mm, {t.volume / 1000:.0f} cm3, {bed:.0f} mm2 on the bed")
    ok = t.is_watertight and one == 1 and hit < 0.05 and lifted > 1.0 and p.extents[0] <= 176 and p.extents[1] <= 176
    out.mkdir(parents=True, exist_ok=True); p.export(out / "cal-stand.stl"); print("wrote", out / "cal-stand.stl")
    if not ok: sys.exit("check failed")


if __name__ == "__main__":
    main()
