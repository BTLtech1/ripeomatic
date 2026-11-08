#!/usr/bin/env python3
"""Print-friendly lead screw thread (experimental): a 90-degree V thread, 2 mm pitch.

The TR10x2 thread's flanks are only 15 degrees off flat, so printed standing up
(screw and sled nut both) every ridge's underside droops. This profile has
45-degree flanks, which print cleanly with the axis vertical, keeps Ø10 and
2 mm per turn (so steps_per_mm is unchanged), and builds the screw-to-nut
clearance into the nut.

    python3 tools/v45_thread.py [out_dir]

writes
    v45-lead-screw.stl        90 mm screw, double-D socket for the 28BYJ-48, standing
    v45-sled.stl              hardware/stl/sled.stl with its nut replaced (motor-end 10 mm)
                              and a zig-zag (no-bridge) blade slot roof, no clamp screw needed
    v45-test-screw-30mm.stl   short screw for a quick fit test
    v45-test-nuts.stl         three 10 mm nuts, radial clearance 0.3 / 0.4 / 0.5 mm
                              (1, 2, 3 notches on the rim)
"""
import sys, pathlib, tempfile
import numpy as np
import trimesh
import manifold3d as mf
from build123d import Cylinder, Box, Pos, Rot, export_stl, Align
from bd_warehouse.thread import Thread

ROOT = pathlib.Path(__file__).resolve().parent.parent
STL = ROOT / "hardware" / "stl"

P = 2.0            # pitch = lead (single start)
R_CREST = 4.95     # screw crest radius (Ø9.9, as the TR screw printed)
DEPTH = 0.8        # radial thread depth
FLAT = 0.2         # axial width of the crest and root flats -> flanks run 0.8 axially = 45 degrees
R_ROOT = R_CREST - DEPTH
CLEAR = 0.4        # radial clearance used for the sled's nut (normal clearance = 0.28)

# 28BYJ-48 shaft socket: Ø5.2 with two flats 3.2 apart, 10 deep (same as the TR screw)
SOCK_D, SOCK_FLATS, SOCK_DEPTH = 5.2, 3.2, 10.0


def to_mesh(shape):
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        export_stl(shape, f.name, tolerance=0.01, angular_tolerance=0.1)
        m = trimesh.load(f.name, force="mesh")
    m.merge_vertices(); m.process()
    return m


def M(m):  # trimesh -> manifold
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))


def T(man):  # manifold -> trimesh
    mm = man.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mm.vert_properties)[:, :3], faces=np.asarray(mm.tri_verts), process=True)


def screw(length, socket=True):
    core = M(to_mesh(Cylinder(R_ROOT + 0.01, length, align=(Align.CENTER, Align.CENTER, Align.MIN))))
    th = M(to_mesh(Thread(apex_radius=R_CREST, apex_width=FLAT, root_radius=R_ROOT, root_width=P - FLAT,
                          pitch=P, length=length, end_finishes=("chamfer", "chamfer"))))
    s = core + th
    if socket:
        sock = Cylinder(SOCK_D / 2, SOCK_DEPTH, align=(Align.CENTER, Align.CENTER, Align.MIN))
        sock = sock & Box(SOCK_D + 1, SOCK_FLATS, SOCK_DEPTH, align=(Align.CENTER, Align.CENTER, Align.MIN))
        s = s - M(to_mesh(Pos(0, 0, -0.01) * sock))
    return T(s)


def nut_cavity_and_ridge(length, clear, z0=0.0):
    """(cavity to subtract, internal ridge to add back) for a nut along +z starting at z0."""
    r_apex, r_root = R_ROOT + clear, R_CREST + clear
    cav = M(to_mesh(Pos(0, 0, z0 - 0.01) * Cylinder(r_root, length + 0.02, align=(Align.CENTER, Align.CENTER, Align.MIN))))
    ridge = M(to_mesh(Pos(0, 0, z0) * Thread(apex_radius=r_apex, apex_width=FLAT, root_radius=r_root,
                                                root_width=P - FLAT, pitch=P, length=length,
                                                end_finishes=("fade", "square"))))
    # 45-degree countersink at the entry (z0): self-supporting when printed from the entry up
    cs_r0 = r_root + 0.1
    cs = trimesh.creation.cone(radius=cs_r0, height=cs_r0, sections=96)
    cs.apply_translation([0, 0, z0 - 0.01])
    return cav, ridge, M(cs)


def nut_block(clear, notches):
    blk = M(to_mesh(Cylinder(9, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))))
    cav, ridge, cs = nut_cavity_and_ridge(10, clear)
    blk = ((blk - cav) + (ridge ^ blk)) - cs
    for k in range(notches):  # notches on the rim, top edge
        a = np.radians(90 + 25 * k)
        n = trimesh.creation.box((2.5, 1.5, 3)); n.apply_translation([9 * np.cos(a), 9 * np.sin(a), 9.5])
        blk = blk - M(n)
    return T(blk)


def zigzag_slot(s, y_off=36.5):
    """Blade slot roof made of five small 45-degree peaks instead of one flat 12 mm bridge,
    so the sled prints standing on its motor end with no support in the slot. The flat blade
    slides in under the peaks' lower edges (0.1 mm clearance) and is held by the fit, no screw.
    The front wall gets 1 mm thicker to keep 2 mm of wall over the peaks.
    Built in model coordinates (x = press axis, y = up, z = across) and mapped to the
    sled's print orientation: print = (-z, y - y_off, x + 2)."""
    def to_print(m):
        v = m.vertices.copy()
        m.vertices = np.column_stack([-v[:, 2], v[:, 1] - y_off, v[:, 0] + 2.0])
        # (-z, y, x) is a proper rotation (det +1), so the winding stays valid
        return m
    wall = trimesh.creation.box(extents=[1.1, 7.0, 16.0]); wall.apply_translation([27.45, 22.5, 0])
    W, X0, n = 6.25, 24.7, 5   # 6.25: just off the old slot's side faces (coplanar booleans leave slivers)
    h = 2 * W / (2 * n)
    roof = [(W, X0)]
    for k in range(n):
        zc = W - h * (2 * k + 1)
        roof += [(zc, X0 + h), (zc - h, X0)]
    prof = [(-W, 21.95), (W, 21.95)] + roof
    prof = [(z, x) for z, x in prof]
    # extrude the (z, x) profile along y 19.05 .. 26.6
    import shapely.geometry as sg
    poly = sg.Polygon(prof)
    cut = trimesh.creation.extrude_polygon(poly, 26.6 - 19.05)   # profile in its local xy = (z, x), extruded along local z
    cut.apply_translation([0, 0, 19.05])
    v = cut.vertices.copy()                                       # local (z, x, y) -> model (x, y, z)
    cut.vertices = np.column_stack([v[:, 1], v[:, 2], v[:, 0]])   # cyclic swap: proper rotation
    s = s + M(to_print(wall))
    s = s - M(to_print(cut))
    return s


def sled(clear=CLEAR):
    m = trimesh.load(STL / "sled.stl", force="mesh")
    s = M(m)
    # find the bore axis (vertical in print orientation) from the clearance bore at mid-height
    sec = m.section(plane_origin=[0, 0, 30], plane_normal=[0, 0, 1]); p2, Tm = sec.to_2D(normal=[0, 0, 1])
    hole = min((np.array(i.coords) for p in p2.polygons_full for i in p.interiors), key=lambda a: np.ptp(a[:, 0]))
    cx, cy = (hole + Tm[:2, 3]).mean(axis=0)
    # fill the old TR nut and lead-in (motor-end 10 mm), then cut the new nut
    plug = trimesh.creation.cylinder(radius=5.4, height=10.0, sections=128); plug.apply_translation([cx, cy, 5.0])
    s = s + M(plug)
    lip = trimesh.creation.cylinder(radius=5.6, height=0.8, sections=128); lip.apply_translation([cx, cy, 0.4])
    s = s + M(lip)  # also fills the old 0.6 mm stepped lead-in
    cav, ridge, cs = nut_cavity_and_ridge(10.0, clear)
    keep = M(trimesh.creation.cylinder(radius=5.6, height=10.0, sections=128).apply_translation([0, 0, 5.0]))
    # translate the tools to the bore axis
    move = lambda man: man.translate([cx, cy, 0])
    s = (s - move(cav)) + move(ridge ^ keep)
    s = s - move(cs)
    s = zigzag_slot(s)
    return T(s), (cx, cy)


def main():
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else STL / "v45"
    out.mkdir(parents=True, exist_ok=True)
    ls = screw(90.0); ls.export(out / "v45-lead-screw.stl")
    ts = screw(30.0, socket=False); ts.export(out / "v45-test-screw-30mm.stl")
    nuts = []
    for k, c in enumerate((0.3, 0.4, 0.5)):
        n = nut_block(c, k + 1); n.apply_translation([k * 22, 0, 0]); nuts.append(n)
    trimesh.util.concatenate(nuts).export(out / "v45-test-nuts.stl")
    sl, axis = sled(); sl.export(out / "v45-sled.stl")
    for f in sorted(out.glob("v45-*.stl")):
        m = trimesh.load(f, force="mesh")
        if not m.is_watertight:  # float32 STL rounding can leave slivers; weld and close them
            m.merge_vertices(digits_vertex=4); m.update_faces(m.nondegenerate_faces()); m.update_faces(m.unique_faces())
            m.remove_unreferenced_vertices(); trimesh.repair.fill_holes(m); trimesh.repair.fix_normals(m)
            m.export(f)
        print(f"{f.name:26s} {m.extents.round(1)} watertight={m.is_watertight} volume={m.volume/1000:.2f} cm3")
    print("sled nut axis", np.round(axis, 2))


if __name__ == "__main__":
    main()
