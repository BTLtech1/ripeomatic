#!/usr/bin/env python3
"""Fixed V-holder for the avocado (replaces the hanging bowl, U-yoke, M5 bolts and knob).

    python3 tools/v_holder.py [out_dir] [--model]   # writes v-holder.stl (print orientation) and checks the fit

Why: the round bowl only fits one size. A smaller avocado sits at the bottom, and the
pad's push rolls it back and up the curve until it jams, so part of the "squish" is
the fruit moving. The bowl also hung on two bolts between thin arms and flexed.

The V is a floor that tilts 12 degrees down toward the back and a back wall square to
it. Any avocado lying on its side touches both, so the push wedges it into the corner
and it has nowhere to roll. The corner is placed so a large (80 mm) avocado's middle is
at pad height; smaller ones sit lower and the pad meets them a little above their
middle, which presses them down into the floor too.

It is one rigid part: two end walls, ribs under the floor, and a foot that drops into
the base's old yoke recess and takes the same four M3 screws from below (2.8 mm pilot
holes at x 81, z +-30 and +-60). Printed lying on the back of the wall: every face is
vertical or self-supporting, no supports.

Model coordinates (as the Fusion assembly): x = press axis toward the holder, y = up,
z = across. Pad centre at y 62. With the V45 sled and blade the pad tip is at x 28 at
home and x 65 at max travel 37; the sled's low front reaches x 65 below y 19.
"""
import sys
import math
import pathlib
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import Polygon, MultiPoint

ROOT = pathlib.Path(__file__).resolve().parent.parent
STL = ROOT / "hardware" / "stl"

A = math.radians(12.0)          # floor tilt (down toward the back); the wall is square to the floor
PAD_Y = 62.0                    # pad centre height
R_BIG = 40.0                    # an 80 mm avocado sits with its middle at pad height
V0 = np.array([106.0, PAD_Y - R_BIG * (math.sin(A) + math.cos(A)) + 0.5])   # inner corner of the V (+0.5: floor clears the sled's front)
LF, LW = 52.0, 70.0             # inner floor / wall lengths from the corner
T_FLOOR, T_WALL = 3.0, 5.0      # floor 3 mm (ribs carry it) so its underside clears the sled's front by 1.5 mm
HALF_IN, CHEEK = 60.0, 5.0      # 120 mm between the end walls, 5 mm end walls
RIB_T = 4.0
RIB_X_MIN = 70.0                # under-floor ribs near the middle stay clear of the sled (x <= 65 at max travel 37) and the rails (x < 70)
DECK_Y = 5.0
FOOT = (73.5, 88.5, 2.0, 5.0)   # x0, x1, y0, y1: fills the old yoke recess (73.25..88.75, floor at y 2)
HOLES_Z = (-60.0, -30.0, 30.0, 60.0)
HOLE_X, HOLE_D = 81.02, 2.8

U_F = np.array([-math.cos(A), math.sin(A)])    # along the floor, toward the pad
U_W = np.array([math.sin(A), math.cos(A)])     # up the wall
N_F = np.array([-math.sin(A), -math.cos(A)])   # out of the floor (downward)
N_W = np.array([math.cos(A), -math.sin(A)])    # out of the wall (backward)

F1, W1 = V0 + LF * U_F, V0 + LW * U_W
F1o, W1o = F1 + T_FLOOR * N_F, W1 + T_WALL * N_W
VC = V0 + T_FLOOR * N_F + T_WALL * N_W         # outer corner; the back of the wall is the print bed


def back_x(y):
    """x of the wall's back plane at height y"""
    return VC[0] + (y - VC[1]) * math.tan(A)


def floor_under_y(x):
    """height of the floor's underside at x"""
    return VC[1] + (VC[0] - x) * math.tan(A)


def prism(poly_xy, z0, z1):
    """extrude an (x, y) polygon along z"""
    p = Polygon(poly_xy)
    if not p.exterior.is_ccw:
        p = Polygon(list(p.exterior.coords)[::-1])
    m = trimesh.creation.extrude_polygon(p, z1 - z0)
    m.apply_translation([0, 0, z0])
    return m


def M(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))


def T(man):
    mm = man.to_mesh()
    t = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts))
    t.merge_vertices()
    return t


def build():
    zc = HALF_IN + CHEEK
    plates = prism([F1, V0, W1, W1o, VC, F1o], -HALF_IN - 0.5, HALF_IN + 0.5)
    # end walls: the whole V outline, down to the deck
    cheek_pts = [F1, V0, W1, W1o, VC, F1o, (F1o[0], DECK_Y), (back_x(DECK_Y), DECK_Y)]
    hull = list(MultiPoint([tuple(p) for p in cheek_pts]).convex_hull.exterior.coords)[:-1]
    body = M(plates)
    for z0 in (-zc, HALF_IN):
        body = body + M(prism(hull, z0, z0 + CHEEK))
    # ribs under the floor. Near the middle they start at x 70 (sled and rails); further out
    # (|z| > 28, beyond the rails) they run to the floor's front edge.
    for zr in (0.0, -20.0, 20.0, -40.0, 40.0):
        x0 = RIB_X_MIN if abs(zr) < 28 else F1o[0] + 0.5
        rib = [(x0, DECK_Y), (back_x(DECK_Y), DECK_Y), tuple(VC), (x0, floor_under_y(x0) + 0.3)]
        body = body + M(prism(rib, zr - RIB_T / 2, zr + RIB_T / 2))
    # a 3 mm plate on the deck ties the ribs together; the foot below it fills the recess
    plate = [(RIB_X_MIN, DECK_Y), (back_x(DECK_Y), DECK_Y), (back_x(DECK_Y + 3), DECK_Y + 3), (RIB_X_MIN, DECK_Y + 3)]
    body = body + M(prism(plate, -zc, zc))
    x0, x1, y0, y1 = FOOT
    # the foot's back face is chamfered (30 degrees off the deck): printed on its back, a square
    # back face would be a 3 mm ledge facing straight down
    body = body + M(prism([(x0, y0), (x1 - 5.5, y0), (x1, y1 + 0.2), (x0, y1 + 0.2)], -zc, zc))
    for zh in HOLES_Z:
        h = trimesh.creation.cylinder(radius=HOLE_D / 2, height=9.0, sections=32)
        h.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
        h.apply_translation([HOLE_X, FOOT[2] + 4.0, zh])
        body = body - M(h)
    return T(body)


def to_print(m):
    """lay it on the back of the wall: rotate so N_W points down (-z), then rest on z = 0"""
    m = m.copy()
    # model (x, y, z) -> print: the wall's outward normal (N_W, 0) becomes -Z, model z becomes print y
    ez = -np.array([N_W[0], N_W[1], 0.0])           # print +Z
    ey = np.array([0.0, 0.0, 1.0])                  # print +Y = model z
    ex = np.cross(ey, ez)                           # print +X (right-handed)
    R = np.vstack([ex, ey, ez])
    m.vertices = m.vertices @ R.T
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    return m


def check(h):
    """fit checks in model coordinates: the base, the sled at max travel, the reach for 55-80 mm fruit"""
    ok = True
    base = trimesh.load(STL / "base-v1-yoke-slot.stl", force="mesh")
    v = base.vertices.copy(); base.vertices = np.column_stack([v[:, 1] + 20.5, v[:, 2], v[:, 0]])
    inter = T(M(h) ^ M(base)).volume
    print(f"overlap with the base: {inter:.2f} mm3"); ok &= inter < 1.0
    sled = trimesh.load(STL / "v45" / "v45-sled.stl", force="mesh")
    v = sled.vertices.copy(); sled.vertices = np.column_stack([v[:, 2] - 2.0 - 20.0 + 37.0, v[:, 1] + 36.5, -v[:, 0]])   # at max travel 37
    inter = T(M(h) ^ M(sled)).volume
    gap = trimesh.proximity.signed_distance(h, sled.sample(4000)).max()
    print(f"sled at max travel 37: overlap {inter:.2f} mm3, closest {-gap:.2f} mm"); ok &= inter < 0.01 and -gap > 1.0
    tip0, tip_max = 28.0, 65.0
    for d in (55, 65, 80):
        r = d / 2
        c = V0 + r * U_F + r * np.array([math.sin(A), math.cos(A)])   # touching the floor and the wall
        dy = PAD_Y - c[1]
        reach = c[0] - math.sqrt(max(r * r - dy * dy, 0))
        print(f"  {d} mm avocado: middle at height {c[1]:.1f}, pad touches at x {reach:.1f} (travel {reach - tip0:.1f} of 37)")
        ok &= tip0 + 3 < reach < tip_max - 2
    return ok


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = pathlib.Path(args[0]) if args else STL
    out.mkdir(parents=True, exist_ok=True)
    h = build()
    print(f"watertight {h.is_watertight}, solid volume {h.volume / 1000:.1f} cm3")
    ok = check(h) and h.is_watertight
    p = to_print(h)
    print("print size", np.round(p.extents, 1))
    p.export(out / "v-holder.stl")
    if "--model" in sys.argv:
        h.export(out / "v-holder-model.stl")   # assembly coordinates, for renders and fit checks
    print("wrote", out / "v-holder.stl")
    if not ok:
        sys.exit("fit check failed")


if __name__ == "__main__":
    main()
