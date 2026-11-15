#!/usr/bin/env python3
"""Calibration cup: sits over the round pad and holds the weights for the force calibration.

    python3 tools/cal_cup.py [out_dir]     # writes cal-cup.stl (print orientation) and checks the fit on pad-TPU.stl

The pad is a dome, so nothing balances on it. This cup has a socket underneath (a short sleeve round the
pad's straight part, then a 45 degree cone that seats on the dome in a ring, so it cannot rock) and a
23 mm tube on top that keeps a stack of US nickels (21.2 mm) upright: 20 nickels = 100 g sit inside it,
40 = 200 g stand half out of it. The flat rim takes a small jar instead. Put it on the pad BEFORE
"Capture zero": then its own weight is part of the zero and only what you add counts.

Printed upside down (rim on the bed): the socket becomes an open funnel, the only bridge is the 23 mm
floor of the tube. No supports.
"""
import sys, math, pathlib
import numpy as np, trimesh, manifold3d as mf
from shapely.geometry import Polygon

ROOT = pathlib.Path(__file__).resolve().parent.parent
STL = ROOT / "hardware" / "stl"
PAD_R, PAD_STRAIGHT, PAD_H = 8.0, 3.4, 11.4      # pad-TPU.stl: 16 mm round, straight for 3.4, then a dome to 11.4
CLEAR = 0.2                                      # per side round the pad (it is TPU)
R_OUT, R_CUP, CUP_DEPTH, FLOOR = 14.0, 11.5, 45.0, 2.0
R_RIM, RIM_T = 25.0, 2.0
SKIRT_Z0 = 0.8                                   # the sleeve stops this far above the pad's base

STEM_R, STEM_LEN = 5.0, 10.9                     # the blade's bare stem (no pad on it): 10 mm round, 10.9 long
STEM_CLEAR, STEM_DEPTH = 0.125, 9.0              # slide fit; the socket is 9 deep, so it stops 1.9 mm short of the blade

def build_stem():
    """the same cup for the bare stem: a plain 10.25 mm socket whose flat end rests on the stem's tip"""
    rs = STEM_R + STEM_CLEAR
    z_floor = STEM_DEPTH + FLOOR; z_end = z_floor + CUP_DEPTH
    prof = [(rs, 0), (R_OUT, 0), (R_OUT, z_end - RIM_T - (R_RIM - R_OUT)), (R_RIM, z_end - RIM_T), (R_RIM, z_end),
            (R_CUP, z_end), (R_CUP, z_floor), (0, z_floor), (0, STEM_DEPTH), (rs, STEM_DEPTH)]
    mm = mf.Manifold.revolve(mf.CrossSection([prof]), 96).to_mesh()
    m = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts)); m.merge_vertices()
    return m, dict(z_end=z_end)

def build():
    rs = PAD_R + CLEAR
    # 45 degree cone touching the dome (sphere R 8 centred at the top of the straight part) in a ring
    c = PAD_R + 0.05
    apex = PAD_STRAIGHT + c * math.sqrt(2.0)                 # where the cone would close
    z_cone0 = apex - rs                                      # the cone starts at the sleeve's radius
    r_top, z_top = 1.5, apex - 1.5
    z_floor = z_top + FLOOR
    z_end = z_floor + CUP_DEPTH
    # half profile (r, z), revolved: outside wall, rim, tube, floor, socket
    prof = [(rs, SKIRT_Z0), (R_OUT, SKIRT_Z0), (R_OUT, z_end - RIM_T - (R_RIM - R_OUT)), (R_RIM, z_end - RIM_T), (R_RIM, z_end),
            (R_CUP, z_end), (R_CUP, z_floor), (0, z_floor), (0, z_top), (r_top, z_top), (rs, z_cone0)]
    man = mf.Manifold.revolve(mf.CrossSection([prof]), 96)      # the profile's (r, z) becomes the solid's radius and z
    mm = man.to_mesh()
    m = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts)); m.merge_vertices()
    return m, dict(z_cone0=z_cone0, z_floor=z_floor, z_end=z_end, apex=apex)

def to_print(m):
    p = m.copy(); p.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0])); p.apply_translation([0, 0, -p.bounds[0][2]])
    return p

def main():
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else STL
    M = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
    # --- the bare-stem version, checked on the V45 blade ---
    ms, ds = build_stem()
    blade = trimesh.load(STL / "v45" / "v45-blade.stl", force="mesh"); v = blade.vertices
    blade.vertices = np.column_stack([v[:, 2] + 2.1, v[:, 1] + 43.5, -v[:, 0]])          # model coordinates: stem along +x at y 62, z 0
    tip = blade.bounds[1][0]
    def on_stem(dz):      # cup axis along x, socket end resting on the stem's tip (dz pushes it further on)
        c = ms.copy(); w = c.vertices.copy(); c.vertices = np.column_stack([w[:, 2] + tip - STEM_DEPTH - dz, w[:, 1] + 62.0, w[:, 0]]); c.invert(); return c
    i0, i1 = (M(on_stem(0)) ^ M(blade)).volume(), (M(on_stem(0.25)) ^ M(blade)).volume()
    print(f"stem version: watertight {ms.is_watertight}, overlap with the blade seated {i0:.3f} mm3, pushed 0.25 mm further {i1:.2f} mm3 (must be > 0)")
    oks = ms.is_watertight and i0 < 0.01 and i1 > 0.05
    out.mkdir(parents=True, exist_ok=True); to_print(ms).export(out / "cal-cup-stem.stl"); print("wrote", out / "cal-cup-stem.stl")
    if not oks: sys.exit("stem check failed")
    m, d = build()
    ok = m.is_watertight and m.volume > 0
    print(f"watertight {m.is_watertight}, {m.volume/1000:.1f} cm3 (about {m.volume/1000*1.24*0.35:.0f} g at 15 % infill), {d['z_end']:.1f} tall")
    pad = trimesh.load(STL / "pad-TPU.stl", force="mesh")
    inter = (M(m) ^ M(pad)).volume()
    lowered = m.copy(); lowered.apply_translation([0, 0, -0.25])
    inter_low = (M(lowered) ^ M(pad)).volume()
    print(f"overlap with the pad: seated {inter:.3f} mm3; pushed 0.25 mm further down {inter_low:.2f} mm3 (must be > 0: it rests on the dome)")
    ok &= inter < 0.01 and inter_low > 0.05
    p = m.copy(); p.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0])); p.apply_translation([0, 0, -p.bounds[0][2]])
    z0 = p.bounds[0][2]; bed = p.area_faces[(p.face_normals[:, 2] < -0.99) & (np.abs(p.triangles_center[:, 2] - z0) < 0.02)].sum()
    print(f"on the bed: {bed:.0f} mm2")
    out.mkdir(parents=True, exist_ok=True); p.export(out / "cal-cup.stl"); print("wrote", out / "cal-cup.stl")
    if not ok: sys.exit("check failed")

if __name__ == "__main__":
    main()
