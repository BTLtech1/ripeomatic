#!/usr/bin/env python3
"""Experimental: the U-yoke slides into a dovetail channel in the base instead of being screwed down.

    python3 tools/dovetail_yoke.py [out_dir]

writes (all in print orientation, like the files in hardware/stl/)
    dovetail-base.stl     hardware/stl/base.stl with the yoke recess turned into a dovetail channel,
                          open at the knob-side edge, and only two optional screw holes (3.4 clearance)
    dovetail-u-yoke.stl   hardware/stl/u-yoke.stl with a matching dovetail crossbar and 2.8 pilot holes
    dovetail-keeper.stl   small plug that fills the open end of the channel behind the yoke (snug fit)

Model coordinates (x = press axis toward the nest, y = up, z = across, knob side +z):
    yoke crossbar x 73..89, y 2..5 (sits in a 3 mm recess, deck under it 2 mm), z -74..74; arms at |z| 68..74.
"""
import sys, pathlib
import numpy as np
import trimesh
import manifold3d as mf
import shapely.geometry as sg

ROOT = pathlib.Path(__file__).resolve().parent.parent
STL = ROOT / "hardware" / "stl"

UNDER_A = 1.5    # dovetail undercut on the motor-side wall over the 3 mm depth (27 degrees off vertical: prints without support)
UNDER_B = 0.75   # nest-side wall: smaller, the corner keyhole pockets are 1 mm away
CLEAR = 0.10     # crossbar-to-channel clearance per side (about 0.2 mm up/down play)
KEEP_CLEAR = 0.05
X0, X1, Y0, Y1 = 73.0, 89.0, 2.0, 5.0        # old recess / crossbar section
Z_CLOSED = -74.2                              # channel stops here (crossbar end + 0.2)
Z_EDGE = 82.5


def M(m): return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def T(man):
    mm = man.to_mesh(); t = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts)); t.merge_vertices(); return t


# print <-> model (cyclic axis swaps, proper rotations, so winding is preserved)
def base_to_model(m):  v = m.vertices.copy(); m.vertices = np.column_stack([v[:, 1] + 20.5, v[:, 2], v[:, 0]]); return m
def base_to_print(m):  v = m.vertices.copy(); m.vertices = np.column_stack([v[:, 2], v[:, 0] - 20.5, v[:, 1]]); return m
def yoke_to_model(m):  v = m.vertices.copy(); m.vertices = np.column_stack([v[:, 1] + 75.6, v[:, 2] + 2.0, v[:, 0] - 4.5]); return m
def yoke_to_print(m):  v = m.vertices.copy(); m.vertices = np.column_stack([v[:, 2] + 4.5, v[:, 0] - 75.6, v[:, 1] - 2.0]); return m


def prism_xy(profile, z0, z1):
    """extrude an (x, y) polygon along model z from z0 to z1"""
    p = trimesh.creation.extrude_polygon(sg.Polygon(profile), z1 - z0)
    p.apply_translation([0, 0, z0])
    return p


def trapezoid(grow):
    """dovetail section: wide at the bottom (y 2), narrow at the top (y 5); grow = outward offset per side"""
    return [(X0 - UNDER_A - grow, Y0), (X1 + UNDER_B + grow, Y0), (X1 + grow, Y1), (X0 - grow, Y1)]


def cyl_y(x, z, r, y0, y1):
    c = trimesh.creation.cylinder(radius=r, height=y1 - y0, sections=48)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2, z])
    return c


def base():
    b = M(base_to_model(trimesh.load(STL / "base.stl", force="mesh")))
    # fill the old recess and the four old screw holes, then cut the channel and two clearance holes
    fill = trimesh.creation.box(extents=[X1 - X0 + 0.02, Y1 - Y0, 152.0]); fill.apply_translation([(X0 + X1) / 2, (Y0 + Y1) / 2, 0])
    b = b + M(fill)
    for z in (-68, -30, 30, 68):
        b = b + M(cyl_y(81.0, z, 1.35, -0.01, Y0 + 0.01))
    ch = prism_xy(trapezoid(0.0), Z_CLOSED, Z_EDGE + 1.0)
    b = b - M(ch)
    for z in (-30, 30):
        b = b - M(cyl_y(81.0, z, 1.7, -0.5, Y0 + 0.5))
    return base_to_print(T(b))


def yoke():
    y = M(yoke_to_model(trimesh.load(STL / "u-yoke.stl", force="mesh")))
    # replace the crossbar's rectangular section (y 2..5) with the dovetail section, keep the arms above y 5
    old = trimesh.creation.box(extents=[X1 - X0 + 0.02, Y1 - Y0, 148.02]); old.apply_translation([(X0 + X1) / 2, (Y0 + Y1) / 2, 0])
    y = y - M(old)
    bar = prism_xy(trapezoid(-CLEAR), -74.0, 74.0)
    y = y + M(bar)
    for z in (-30, 30):
        y = y - M(cyl_y(81.0, z, 1.4, Y0 - 0.5, Y1 + 0.5))
    return yoke_to_print(T(y))


def keeper():
    k = prism_xy(trapezoid(-KEEP_CLEAR), 74.2, Z_EDGE)      # fills the open end of the channel
    k = T(M(k))
    # print it on its wide bottom face, centred
    v = k.vertices.copy(); k.vertices = np.column_stack([v[:, 2], v[:, 0], v[:, 1]])
    lo, hi = k.bounds; k.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    return k


def main():
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else STL / "dovetail"
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in [("dovetail-base.stl", base), ("dovetail-u-yoke.stl", yoke), ("dovetail-keeper.stl", keeper)]:
        m = fn(); m.export(out / name)
        print(f"{name:22s} {m.extents.round(1)} watertight={m.is_watertight} volume={m.volume / 1000:.2f} cm3")


if __name__ == "__main__":
    main()
