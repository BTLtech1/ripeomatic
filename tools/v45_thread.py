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
                              and a 45-degree arch blade slot (no bridge, no clamp screw)
    v45-blade.stl             the blade with a matching ridge on its tongue and a 5 mm longer pad stem
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


RIB_H = 0.4        # crush rib height on the slot's back wall (0.1 mm squeeze after the ridge seats)
MAG_D, MAG_DEPTH = 3.4, 2.1   # pocket for a 3 x 2 mm magnet, flush with the blade's back face
STEM_EXTRA = 5.0   # pad stem lengthened by this much (firmware max_travel_mm drops 42 -> 37 to match)
SLOT_W = 6.25      # half width of the blade slot (blade is +-6)
ROOF_X = 24.7      # slot roof springline, model x (blade front face is 24.6)


def to_print_sled(m, y_off=36.5):
    """model (x = press axis, y = up, z = across) -> the sled's print orientation (standing on its motor end).
    (-z, y - y_off, x + 2) is a proper rotation, so the winding stays valid."""
    v = m.vertices.copy()
    m.vertices = np.column_stack([-v[:, 2], v[:, 1] - y_off, v[:, 0] + 2.0])
    return m


def prism_zx(profile, y0, y1):
    """extrude a (z, x) polygon along model y from y0 to y1, in model coordinates"""
    import shapely.geometry as sg
    pr = trimesh.creation.extrude_polygon(sg.Polygon(profile), y1 - y0)
    pr.apply_translation([0, 0, y0])
    v = pr.vertices.copy()                                   # local (z, x, y) -> model (x, y, z): cyclic, proper
    pr.vertices = np.column_stack([v[:, 1], v[:, 2], v[:, 0]])
    return pr


def arch_slot(s):
    """Blade slot with a 45-degree arch roof instead of a flat 12 mm bridge, so the sled prints
    standing on its motor end with no support in the slot. The riser grows toward the pad to hold
    the arch (outer roof 2.5 mm thick). The blade gets a matching ridge (see blade()).
    Holding without a screw: two crush ribs on the slot's back wall push the blade forward so its
    ridge seats in the arch (the 45-degree faces centre it both ways); the ribs squash the rest.
    Optional M3 x 20 screw: a hole down the arch's apex with a flat seat for the head, through the
    blade, threading into the old 2.5 mm hole in the block."""
    hood = prism_zx([(-8.0, 26.0), (8.0, 26.0), (8.0, 26.5), (0.0, 34.5), (-8.0, 26.5)], 19.0, 26.0)
    cut = prism_zx([(-SLOT_W, 21.95), (SLOT_W, 21.95), (SLOT_W, ROOF_X), (0.0, ROOF_X + SLOT_W), (-SLOT_W, ROOF_X)], 19.05, 26.6)
    s = s + M(to_print_sled(hood))
    s = s - M(to_print_sled(cut))
    for zc in (-3.5, 3.5):   # crush ribs, 45-degree flanks, 0.4 tall, along the insertion direction
        rib = prism_zx([(zc - 0.45, 21.9), (zc + 0.45, 21.9), (zc, 21.95 + RIB_H)], 19.05, 26.0)
        s = s + M(to_print_sled(rib))
    # optional screw: clearance hole along the press axis at the blade's hole (model y 23, z 0), head seat at x 33
    hole = trimesh.creation.cylinder(radius=1.7, height=6.0, sections=48)
    hole.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])); hole.apply_translation([32.0, 23.0, 0])
    seat = trimesh.creation.cylinder(radius=3.1, height=3.0, sections=48)
    seat.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])); seat.apply_translation([34.5, 23.0, 0])
    s = s - M(to_print_sled(hole)) - M(to_print_sled(seat))
    return s


def hall_clip(s):
    """Hall-sensor pocket that holds an SS49E without glue. The sensor (4.0 wide, 3.0 tall, 1.5 thick,
    flat marked face toward the magnet, legs up) slides down from the top of the post until it sits on
    the pocket floor, which puts its middle level with the magnet (model y 62). Two 0.6 mm lips on the
    post's front face overlap the sensor's face edges by 0.3 mm, and a 0.3 mm rib on the back wall
    pushes it against them. The lips stand proud of the post face, so the sensor isn't moved back."""
    fill = trimesh.creation.box(extents=[2.2, 8.0, 5.2]); fill.apply_translation([16.4, 64.0, 0.0])   # old pocket
    s = s + M(to_print_sled(fill))
    pocket = trimesh.creation.box(extents=[1.7 + 0.01, 8.0, 4.2]); pocket.apply_translation([17.5 - 0.85 + 0.005, 60.5 + 4.0, 0.0])
    s = s - M(to_print_sled(pocket))
    # dovetail lips standing 0.6 mm proud of the post face, their inner faces at 45 degrees: they overlap the
    # sensor's face edges, centre it, and print without support (the sled prints with the post face up)
    for zs in (-1, 1):
        prof = [(2.9, 17.49), (2.9, 18.1), (1.6, 18.1), (1.6, 18.0), (2.1, 17.5), (2.1, 17.49)]
        if zs < 0:
            prof = [(-z, x) for z, x in reversed(prof)]
        s = s + M(to_print_sled(prism_zx(prof, 60.5, 68.0)))
    rib = prism_zx([(-0.35, 15.79), (0.35, 15.79), (0.0, 16.2)], 61.0, 67.5)   # crush rib on the back wall, along y
    s = s + M(to_print_sled(rib))
    return s


def blade():
    """hardware/stl/blade.stl (printed lying on its back, stem up) with the pad stem STEM_EXTRA longer
    and a 45-degree ridge on the tongue that matches the arch slot. Blade print coords:
    x = -model z, y = model y - 43.5, z = model x - 22.1."""
    m = trimesh.load(STL / "blade.stl", force="mesh")
    v = m.vertices.copy()
    v[np.abs(v[:, 2] - 14.5) < 0.01, 2] += STEM_EXTRA        # move the stem's end face out
    m.vertices = v
    import shapely.geometry as sg
    rid = trimesh.creation.extrude_polygon(sg.Polygon([(-6.0, 2.49), (6.0, 2.49), (6.0, 2.7), (0.0, 8.7), (-6.0, 2.7)]), (-17.7) - (-24.3))
    v = rid.vertices.copy()                                   # local (x, z, y') -> print (x, y, z)
    rid.vertices = np.column_stack([v[:, 0], v[:, 2] - 24.3, v[:, 1]])   # ridge stops 0.2 above the tongue's end
    rid.invert()                                              # (x, z, y) is a mirror swap, fix the winding
    b = M(m) + M(rid)
    h = trimesh.creation.cylinder(radius=1.7, height=12.0, sections=48); h.apply_translation([0, 23.0 - 43.5, 5.0])
    # magnet pocket on the back face (the face on the bed), behind the stem: was 3.2 x 0.5 deep, which left a
    # 3 x 2 mm magnet 1.5 mm proud and printed too tight. Now 3.4 x 2.1 deep: the magnet sits flush.
    mag = trimesh.creation.cylinder(radius=MAG_D / 2, height=MAG_DEPTH + 0.1, sections=48)
    mag.apply_translation([0, 62.0 - 43.5, (MAG_DEPTH + 0.1) / 2 - 0.1])
    return T(b - M(h) - M(mag))   # optional screw hole through the ridge (the blade's own hole was already there)


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
    s = arch_slot(s)
    s = hall_clip(s)
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
    blade().export(out / "v45-blade.stl")
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
