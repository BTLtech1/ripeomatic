#!/usr/bin/env python3
"""A stiffer blade: hardware/stl/v45/v45-blade.stl with its plate thickened on the front face.

    python3 tools/blade_stiff.py [out_dir] [extra_mm]     # writes v45-blade-stiff.stl, checks it on the sled

Why: the V45 blade's plate is 2.5 mm thick (not the 3 mm the notes say). From the top of its ridge to the pad
that is a 36 mm cantilever of about 2.5 N/mm, so a full 2.5 N press bends it 1.0 mm at the magnet, and the
gap to the post is only 1.5 mm when the blade stands perfectly straight. Any lean toward the post and the
blade touches it part-way through a press: the sensor stops changing and the reading is lost.

This adds EXTRA (0.9 mm) to the front face from just above the ridge to the top: 3.4 mm thick, about 2.5
times stiffer (6 N/mm), 0.4 mm of bend at 2.5 N. The back face, magnet pocket, ridge, stem and pad position
are unchanged, so it drops into the same sled. The sensor moves about 2.5 times less per newton, so redo the
force calibration, then the blade calibration.
"""
import sys, pathlib
import numpy as np, trimesh
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
_a, sys.argv = sys.argv, sys.argv[:1]
from back_gate import M, T, box3, vol, STL      # noqa: E402
sys.argv = _a

T0 = 2.49                  # the plate's front face in print coordinates (z); the bed is its back face
Y_RIDGE_END = -17.7        # print y where the ridge (inside the sled's arch) stops


def build(extra):
    b = trimesh.load(STL / "v45" / "v45-blade.stl", force="mesh")
    add = box3(-6.0, 6.0, Y_RIDGE_END + 0.3, 24.5, T0 - 0.2, T0 + extra)
    return T(M(b) + add)


def main():
    args = sys.argv[1:]
    out = pathlib.Path(args[0]) if args else STL / "v45"
    extra = float(args[1]) if len(args) > 1 else 0.9
    t = build(extra)
    m = t.copy(); v = m.vertices.copy(); m.vertices = np.column_stack([v[:, 2] + 2.1, v[:, 1] + 43.5, -v[:, 0]])   # model, sled at home
    m.invert()
    sled = trimesh.load(STL / "v45" / "v45-sled.stl", force="mesh"); s = sled.vertices.copy()
    sled.vertices = np.column_stack([s[:, 2] - 22.0, s[:, 1] + 36.5, -s[:, 0]])
    old = trimesh.load(STL / "v45" / "v45-blade.stl", force="mesh"); o = old.vertices.copy()
    old.vertices = np.column_stack([o[:, 2] + 2.1, o[:, 1] + 43.5, -o[:, 0]]); old.invert()
    i_new, i_old = vol(M(m) ^ M(sled)), vol(M(old) ^ M(sled))
    tk = T0 + extra
    k_old, k_new = 3 * 2500 * (12 * 2.5 ** 3 / 12) / 36.2 ** 3, 3 * 2500 * (12 * tk ** 3 / 12) / 36.2 ** 3
    z0 = t.bounds[0][2]; bed = t.area_faces[(t.face_normals[:, 2] < -0.99) & (np.abs(t.triangles_center[:, 2] - z0) < 0.02)].sum()
    print(f"plate {tk:.1f} mm thick (was 2.5): about {k_new:.1f} N/mm (was {k_old:.1f}); bends {2.5 / k_new:.2f} mm at 2.5 N (was {2.5 / k_old:.2f}); gap to the post 1.5 mm")
    print(f"watertight {t.is_watertight}; overlap with the sled {i_new:.3f} mm3 (the stock blade: {i_old:.3f}); {bed:.0f} mm2 on the bed")
    ok = t.is_watertight and i_new <= i_old + 0.05 and bed > 400
    out.mkdir(parents=True, exist_ok=True); t.export(out / "v45-blade-stiff.stl"); print("wrote", out / "v45-blade-stiff.stl")
    if not ok: sys.exit("check failed")


if __name__ == "__main__":
    main()
