#!/usr/bin/env python3
"""V-holder with a servo back gate (second design), and the base with keyhole studs for it.

    python3 tools/back_gate.py [out_dir] [--model]

Writes (print orientation):
    base.stl          the base: old yoke recess and its 4 screw holes filled, 4 BTL mushroom studs added
    gate-frame.stl    floor, side walls, servo pocket; clicks onto the studs (4 keyholes)
    gate-door.stl     the back wall, hinged at the bottom corner
    gate-lever.stl    its shaft goes through the side wall into the door's D socket
    gate-link.stl     curved link from the lever to the servo horn, with the over-centre stop
and checks every fit and every motion for collisions.

The holder
----------
The avocado lies in a V: a floor tilted 12 deg down toward the back and a back wall square to
it, so any size touches both and the pad's push wedges it into the corner instead of rolling it.
The corner is placed so a 70 mm avocado has its middle exactly at pad height (y 62). An 80 mm
one is met 6 mm below its middle and a 55 mm one 9 mm above (9 and 19 degrees off square), and
the pad reaches everything from 45 to 80 mm across inside the 42 mm travel. (The first gate
design centred an 80 mm fruit, which left a 55 mm one hit 14 mm high, at 31 degrees.)

The floor is 6 mm or more above the sled everywhere the sled can reach: the sled runs into a
tunnel under the floor's front edge.

The gate
--------
The back wall is a door. Its hinge axis is 5 mm under the floor and 5 mm behind the wall, so
swung back 88 deg its inner face lines up with the floor and the fruit rolls out with no bump.

The servo (SG90 / MG90S) sits in a pocket under the floor, pushed in from outside through the
side wall on the board side, so nothing sticks out but its horn. Horn, link and lever lie flat
against the outside of that wall, inside the base's outline. Every screw goes in from outside.

Lever (on the door's shaft), link and horn make a four-bar. With the door shut the horn points
straight away from the lever pin and the link runs back over the servo shaft (it is curved to go
round the horn's hub): horn and link are in line, so the pad's push only pulls along that line
and cannot turn the servo. The horn parks a few degrees past that line, where a lug on the link
meets the lever: the push then holds the lug on the lever harder (an over-centre lock), with no
load on the servo's gears and none of their play in the measurement.

The frame clicks onto 4 studs (the v3 stud of the BTL universal mount) through 4 keyholes (v6)
in its underside: drop it on 9 mm toward the pad from its place, push it back until it clicks.
The pad pushes in the locking direction.

Everything is built on the +z side and mirrored at the end, so the servo ends up on the board
side (-z), next to the ESP32.

Model coordinates (as the Fusion assembly): x = press axis toward the holder, y = up,
z = across. Pad centre y 62; V45 pad tip at x 28 at home, 70 at max travel 42.
"""
import sys
import math
import pathlib
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import Polygon, Point, LineString, MultiPoint, box as sbox
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parent.parent
STL = ROOT / "hardware" / "stl"

# ---------------------------------------------------------------- the V
A = math.radians(12.0)
PAD_Y = 62.0
R_MID = 35.0                                     # a 70 mm avocado sits with its middle at pad height
V0 = np.array([103.0, PAD_Y - R_MID * (math.sin(A) + math.cos(A))])   # inner corner (103, 20.49)
U_F = np.array([-math.cos(A), math.sin(A)])      # along the floor toward the pad
U_W = np.array([math.sin(A), math.cos(A)])       # up the wall
N_F = np.array([-math.sin(A), -math.cos(A)])     # out of the floor (down)
N_W = np.array([math.cos(A), -math.sin(A)])      # out of the wall (back)
LF = 46.0                                        # floor length from the corner
F1 = V0 + LF * U_F                               # front edge of the floor (top)
HALF_IN = 56.0                                   # 112 mm between the side walls
CHEEK = 5.0
ZC = HALF_IN + CHEEK                             # 61: outer face of the side walls
DECK = 5.0
TUNNEL_Y = 24.0                                  # underside of the floor over the sled (sled top is y 19)
TUNNEL_BACK = 76.0                               # the sled's front is at x 70 at max travel 42
MAX_TRAVEL = 42.0
TUNNEL_HALF = 22.5                               # the sled is 39.4 wide

# ---------------------------------------------------------------- the door and the four-bar
T_DOOR, L_DOOR = 5.0, 55.0
HINGE = V0 + 5.0 * N_F + 5.0 * N_W               # 5 under the floor, 5 behind the wall
TH_CLOSED, TH_OPEN = math.radians(78.0), math.radians(-10.0)   # door direction (U_W is at 78 deg)
DOOR_HALF = HALF_IN - 0.4
KNUCKLE_R, BOSS_R = 5.0, 6.0
RP, ALPHA = 12.0, math.radians(60.0)             # lever pin: 12 mm from the hinge, 60 deg ahead of the door
CRANK = 13.0                                     # horn hole 13 mm from the shaft
SERVO = np.array([74.0, 16.0])                   # servo shaft, under the floor
OVER = math.radians(5.0)                         # the horn parks about this far past the straight line
LINK_BEND = -10.0                                # how far the link's middle is offset to clear the horn hub
# layers outward from the side wall's outer face (z 61)
Z_TAB = (61.0, 63.5)                             # servo tabs
Z_CASE = 67.8                                    # top of the servo case; its boss goes on to 71.8
Z_LEVER = (66.5, 69.5)
Z_HORN = (73.2, 74.7)                            # horn arm
Z_LINK = (75.0, 78.0)

# ---------------------------------------------------------------- keyholes / studs
STUDS = [(76.0, -33.0), (76.0, 33.0), (89.0, -15.0), (89.0, 15.0)]   # final stud positions (= slot ends)
SLIDE = 9.0                                      # the rounds are 9 mm further back (+x) than the slot ends


def e(a):
    return np.array([math.cos(a), math.sin(a)])


def rot(p, c, a):
    p = np.asarray(p, float) - c
    return c + np.array([p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a)])


def floor_top_y(x):
    return V0[1] + (V0[0] - x) * math.tan(A)


# ---------------------------------------------------------------- mesh helpers
def M(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))


def T(man):
    mm = man.to_mesh()
    t = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts))
    t.merge_vertices()
    return t


def prism(poly, z0, z1):
    if hasattr(poly, "geoms"):
        out = mf.Manifold()
        for g in poly.geoms:
            if g.area > 1e-6:
                out = out + prism(g, z0, z1)
        return out
    p = (poly if isinstance(poly, Polygon) else Polygon(poly)).buffer(0)
    if hasattr(p, "geoms"):
        return prism(p, z0, z1)
    m = trimesh.creation.extrude_polygon(p, z1 - z0)
    m.apply_translation([0, 0, z0])
    return M(m)


def cyl_z(c, r, z0, z1, n=64):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=n)
    m.apply_translation([c[0], c[1], (z0 + z1) / 2])
    return M(m)


def box3(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return M(m)


def vol(man):
    return abs(T(man).volume) if man.num_vert() else 0.0


def mirror_z(man):
    return man.mirror([0, 0, 1])


# ---------------------------------------------------------------- kinematics
def pin(th):
    return HINGE + RP * e(th + ALPHA)


P_SHUT = pin(TH_CLOSED)
LINK = float(np.linalg.norm(SERVO - P_SHUT) + CRANK)          # horn and link in line, folded, when shut
PHI_SHUT = math.atan2(*(SERVO - P_SHUT)[::-1])                # the horn points straight away from the lever pin


def crank_angle(P):
    """From the in-line position the horn could fold either way; this is the way that keeps it above the deck."""
    d = np.linalg.norm(P - SERVO)
    base = math.atan2(*(P - SERVO)[::-1])
    g = math.acos(max(-1, min(1, (CRANK ** 2 + d * d - LINK ** 2) / (2 * CRANK * d))))
    return base + g


def motion(n=60):
    """(door angle, lever pin, horn hole, horn angle) at n steps from shut (in line) to open"""
    out = []
    for th in np.linspace(TH_CLOSED, TH_OPEN, n):
        P = pin(th)
        phi = crank_angle(P)
        out.append((th, P, SERVO + CRANK * e(phi), phi))
    return out


_m = motion(60)
_ph = np.unwrap([m[3] for m in _m])
OPEN_SIGN = 1.0 if _ph[5] > _ph[0] else -1.0     # which way the horn turns to open (+ = counter-clockwise seen from +z)
SWEEP = math.degrees(abs(_ph[-1] - _ph[0]))


def over_pose(eps):
    """horn eps past the in-line position (the door stays shut to within a few hundredths of a mm)"""
    phi = PHI_SHUT - OPEN_SIGN * eps
    return TH_CLOSED, P_SHUT, SERVO + CRANK * e(phi), phi


# ---------------------------------------------------------------- 2D outlines of the moving parts
def door_profile(th):
    d = th - TH_CLOSED
    q0 = V0 - 5.0 * U_W
    pts = [q0, V0 + L_DOOR * U_W, V0 + L_DOOR * U_W + T_DOOR * N_W, q0 + T_DOOR * N_W]
    return Polygon([rot(p, HINGE, d) for p in pts]).union(Point(*HINGE).buffer(BOSS_R, 48))


def lever_profile(th):
    P = pin(th)
    return LineString([HINGE, P]).buffer(4.0, 16).union(Point(*HINGE).buffer(7.0, 48)).union(Point(*P).buffer(4.5, 32))


def link_frame(P, C):
    u = (C - P) / np.linalg.norm(C - P)
    return u, np.array([-u[1], u[0]])


def link_line(P, C):
    """the link's centre line: out to one side and back, so it goes round the horn's hub"""
    u, n = link_frame(P, C)
    L = np.linalg.norm(C - P)
    return LineString([P, P + 0.3 * L * u + LINK_BEND * n, P + 0.7 * L * u + LINK_BEND * n, C])


def link_profile(P, C):
    return link_line(P, C).buffer(3.5, 16, join_style=1)


LUG_K, LUG_R = 7.0, 1.5                          # the stop: a bump under the link, 7 mm from the horn hole


def lug_point(P, C):
    """Beside the horn's arm, on the side the arm swings to when it goes past the in-line position.
    The gap is what a 2.5 mm half-width arm closes OVER (about 5 deg of horn, 7 of horn against link)."""
    u, n = link_frame(P, C)
    side = -1.0 if LINK_BEND < 0 else 1.0
    return C - LUG_K * u + side * (2.5 + LUG_R + 0.45) * n


def horn_profile(phi):
    u = e(phi)
    return LineString([SERVO, SERVO + (CRANK + 2.0) * u]).buffer(2.5, 16).union(Point(*SERVO).buffer(4.0, 32))


def servo_case_profile():
    """the servo's case and gear boss as seen along its shaft (shaft toward the hinge end)"""
    body = sbox(SERVO[0] - 16.6, SERVO[1] - 6.1, SERVO[0] + 5.9, SERVO[1] + 6.1)
    return body.union(Point(*SERVO).buffer(6.0, 32)).union(Point(SERVO[0] - 6.5, SERVO[1]).buffer(3.0, 24))


def lug_touch():
    """how far past in-line the horn gets before its arm meets the lug (deg), or None"""
    for ed in np.arange(0.0, 15.1, 0.25):
        th, P, C, phi = over_pose(math.radians(ed))
        if Point(*lug_point(P, C)).distance(horn_profile(phi)) - LUG_R <= 0:
            return ed
    return None


LUG_TOUCH = lug_touch()


# ---------------------------------------------------------------- keyhole (v6) and stud (v3)
def keyhole_cut(round_xy, slot_end_xy):
    """one keyhole in a floor whose underside is at y = DECK: the 8.8 round, the 5.4 slot from the
    round to slot_end, a 45 deg flare to 8.8 wide between 1.5 and 3.2 above the underside, and two
    r 0.35 detent nibs 2.45 before the slot end in the bottom 1.5."""
    rx, rz = round_xy
    ex, ez = slot_end_xy

    def stadium(w):
        return MultiPoint([(rx, rz), (ex, ez)]).convex_hull.buffer(w / 2, 32)

    def to3d(poly, y):
        return [(x, y, z) for x, z in poly.exterior.coords[:-1]]

    def slab(poly, y0, y1):
        return trimesh.convex.convex_hull(np.array(to3d(poly, y0) + to3d(poly, y1)))

    rnd = trimesh.creation.cylinder(radius=4.4, height=4.4, sections=64)
    rnd.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    rnd.apply_translation([rx, DECK + 2.0, rz])
    cut = M(rnd)
    cut = cut + M(slab(stadium(5.4), DECK - 0.2, DECK + 1.52))
    cut = cut + M(trimesh.convex.convex_hull(np.array(to3d(stadium(5.4), DECK + 1.5) + to3d(stadium(8.76), DECK + 3.2))))
    cut = cut + M(slab(stadium(8.76), DECK + 3.18, DECK + 4.2))
    d = np.array([ex - rx, ez - rz])
    d /= np.linalg.norm(d)
    nrm = np.array([-d[1], d[0]])
    for sgn in (1, -1):
        c = np.array([ex, ez]) - 2.45 * d + sgn * 2.7 * nrm
        nib = trimesh.creation.cylinder(radius=0.35, height=1.7, sections=24)
        nib.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
        nib.apply_translation([c[0], DECK + 0.75, c[1]])
        cut = cut - M(nib)
    return cut


def stud(x, z):
    prof = [(0, 0), (2.5, 0), (2.5, 1.4), (4.0, 2.9), (4.0, 2.95), (3.65, 3.3), (0, 3.3)]
    m = trimesh.creation.revolve(prof, sections=64)
    v = m.vertices.copy()
    m.vertices = np.column_stack([v[:, 0] + x, v[:, 2] + DECK - 0.05, -v[:, 1] + z])
    if m.volume < 0:
        m.invert()
    return M(m)


# ---------------------------------------------------------------- parts (built on the +z side)
def cheek_outline():
    """side wall: a 10 mm lip above the floor at the front, rising in a straight line to the top of the
    door; top corners rounded, bottom corners square (they stand on the print bed)"""
    top_in = V0 + L_DOOR * U_W
    top_out = top_in + T_DOOR * N_W
    raw = Polygon([(SERVO[0] - 22.9, DECK), (SERVO[0] - 22.9, F1[1] + 9.0), tuple(top_in + 1.5 * U_W), tuple(top_out + 1.5 * U_W + 2.5 * N_W),
                   (HINGE[0] + 8.5, HINGE[1] + 6.0), (HINGE[0] + 8.5, DECK)])
    rounded = raw.buffer(-6.0).buffer(6.0, 24)
    out = rounded.union(raw.intersection(sbox(0, DECK, 200, DECK + 10.0)))
    # the front 7 mm of the bottom edge is lifted 1 mm: it passes over the raised arrows on the deck
    # while the frame is being dropped on
    return out.difference(Polygon([(0, 0), (59.0, 0), (59.0, DECK), (58.0, DECK + 1.0), (0, DECK + 1.0)]))


def under_floor(kind):
    """solid from the deck up to the floor, in (x, y). The front is a 3 mm nose, then a 45 deg
    underside (prints without support) down to a vertical face at x 70.5."""
    xb = V0[0] + 2.0
    nose = F1[1] - 3.0
    p = Polygon([(70.5, DECK), (xb, DECK), (xb, floor_top_y(xb)), tuple(F1), (F1[0], nose), (70.5, nose - (70.5 - F1[0]))])
    if kind in ("rail", "both"):       # over the rails: clear of them while the frame is dropped on 9 mm forward
        p = p.difference(sbox(0, 0, 80.0, 14.0))
    if kind in ("centre", "both", "core"):   # the sled's tunnel
        p = p.difference(sbox(0, 0, TUNNEL_BACK, TUNNEL_Y))
    if kind == "core":                 # the middle stays open further back for the lead screw's tip
        p = p.difference(sbox(0, 0, 79.0, TUNNEL_Y))
    return p


def build_frame():
    body = prism(cheek_outline(), HALF_IN, ZC) + prism(cheek_outline(), -ZC, -HALF_IN)
    bands = [(0.0, 8.0, "core"), (8.0, 17.3, "centre"), (17.3, TUNNEL_HALF, "both"), (TUNNEL_HALF, 26.5, "rail"), (26.5, HALF_IN + 0.4, "outer")]
    for z0, z1, kind in bands:
        p = under_floor(kind)
        body = body + prism(p, z0 - 0.02, z1 + 0.02) + prism(p, -z1 - 0.02, -z0 + 0.02)
    # the door's swing and its knuckle
    sweep_door = unary_union([door_profile(th).buffer(0.6) for th in np.linspace(TH_CLOSED, TH_OPEN, 45)])
    body = body - prism(sweep_door, -HALF_IN - 0.3, HALF_IN + 0.3)
    # hinge: the lever's shaft through the servo-side wall, an M3 pin through the other
    body = body - cyl_z(HINGE, 4.0, HALF_IN - 0.5, ZC + 0.1, 48)
    body = body - cyl_z(HINGE, 1.7, -ZC - 0.1, -HALF_IN + 0.5, 32)
    # servo pocket: in from outside through the side wall, under the floor (case 22.5 x 12.2, 15.9 deep
    # below its tabs). The MG90S's cable leaves the case at its shaft end, near the bottom, which is the
    # pocket's closed end: a 4.5 mm relief there lets the cable turn into the 5 mm space behind the
    # case's bottom and run to the open front. (Without it the cable is pinched and the servo won't seat.)
    body = body - box3(SERVO[0] - 17.1, SERVO[0] + 6.4, SERVO[1] - 6.5, SERVO[1] + 6.5, 40.0, ZC + 0.1)
    body = body - box3(SERVO[0] + 6.3, SERVO[0] + 10.9, SERVO[1] - 4.5, SERVO[1] + 4.5, 40.0, 54.0)
    for dx in (-13.9, 13.9):           # tab screws, 27.8 apart round the case centre
        body = body - cyl_z((SERVO[0] - 5.35 + dx, SERVO[1]), 0.85, HALF_IN - 0.1, ZC + 0.1, 24)
    for sx, sz in STUDS:
        body = body - keyhole_cut((sx + SLIDE, sz), (sx, sz))
    return body


def d_shape(c, r, flat, n_dir):
    t = np.array([-n_dir[1], n_dir[0]])
    hp = Polygon([c - 20 * n_dir + 20 * t, c + flat * n_dir + 20 * t, c + flat * n_dir - 20 * t, c - 20 * n_dir - 20 * t])
    return Point(*c).buffer(r, 64).intersection(hp)


def build_door():
    # the knuckle is r 6 along the whole hinge edge, cut flush with the inner face (no bump where the
    # fruit rolls out; the flat sits 0.05 inside the face so the union has no coplanar faces)
    knuckle = Point(*HINGE).buffer(BOSS_R, 64).intersection(
        Polygon([V0 + 0.05 * N_W - 30 * U_W, V0 + 0.05 * N_W + 30 * U_W, V0 + 30 * U_W + 30 * N_W, V0 - 30 * U_W + 30 * N_W]))
    q0 = V0 - 5.0 * U_W
    slab = Polygon([q0, V0 + L_DOOR * U_W, V0 + L_DOOR * U_W + T_DOOR * N_W, q0 + T_DOOR * N_W])
    door = prism(slab.union(knuckle), -DOOR_HALF, DOOR_HALF)
    # +z end: D socket for the lever (7.0, flat 2.9 from the axis, toward the back), screw pilot beyond
    door = door - prism(d_shape(HINGE, 3.5, 2.9, N_W), DOOR_HALF - 8.0, DOOR_HALF + 0.1)
    door = door - cyl_z(HINGE, 1.4, DOOR_HALF - 20.0, DOOR_HALF - 7.9, 32)
    # -z end: pilot for the M3 hinge pin
    door = door - cyl_z(HINGE, 1.4, -DOOR_HALF - 0.1, -DOOR_HALF + 10.0, 32)
    return door


def build_lever():
    P = P_SHUT
    lev = prism(lever_profile(TH_CLOSED), Z_LEVER[0], Z_LEVER[1])
    lev = lev + cyl_z(HINGE, 3.8, HALF_IN, Z_LEVER[0] + 0.1)                          # shaft: through the wall and the gap
    lev = lev + prism(d_shape(HINGE, 3.4, 2.75, N_W), DOOR_HALF - 7.7, HALF_IN + 0.1)   # D into the door
    lev = lev + cyl_z(P, 4.5, 62.5, Z_LEVER[0] + 0.1, 32)                              # more thread for the link's pivot screw
    lev = lev - cyl_z(HINGE, 1.7, DOOR_HALF - 8.0, Z_LEVER[1] + 0.1, 32)                # M3 along the axis
    lev = lev - cyl_z(HINGE, 3.1, Z_LEVER[1] - 1.5, Z_LEVER[1] + 0.1, 32)                # head seat
    lev = lev - cyl_z(P, 1.4, 62.4, Z_LEVER[1] + 0.1, 32)                               # pilot for the pivot screw
    return lev


def build_link():
    C = SERVO + CRANK * e(PHI_SHUT)
    ln = prism(link_profile(P_SHUT, C), Z_LINK[0], Z_LINK[1])
    ln = ln + cyl_z(P_SHUT, 3.5, Z_LEVER[1] + 0.2, Z_LINK[0] + 0.05, 32)               # spacer down to the lever
    ln = ln + cyl_z(lug_point(P_SHUT, C), LUG_R, Z_HORN[0] + 0.2, Z_LINK[0] + 0.05, 24)   # the over-centre stop, beside the horn's arm
    ln = ln - cyl_z(P_SHUT, 1.7, Z_LEVER[1], Z_LINK[1] + 0.1, 32)                       # turns on the M3's shank
    ln = ln - cyl_z(C, 1.1, Z_LINK[0] - 0.1, Z_LINK[1] + 0.1, 32)                        # M2 into the horn
    return ln


def build_base():
    base = trimesh.load(STL / "base-v1-yoke-slot.stl", force="mesh")   # the base before this change (idempotent)
    v = base.vertices.copy()
    base.vertices = np.column_stack([v[:, 1] + 20.5, v[:, 2], v[:, 0]])
    if base.volume < 0:
        base.invert()
    b = M(base)
    # Fill the old yoke recess (x 73-89) and the two weight-saving windows where the holder now stands
    # (board side x 50-70, z -68..-30; knob side the last 15 mm of the long window, x 50-65, z 32..68).
    # Each fill is built 0.5 proud and then planed off at exactly the deck's own height, so the deck is
    # one flat face: a fill that stops a hair under it leaves hairline steps that slicers draw as lines.
    deck = float(np.median(base.vertices[np.abs(base.vertices[:, 1] - DECK) < 0.01, 1]))
    fills = [(72.5, 89.5, 1.9, -75.5, 75.5), (49.5, 70.5, 0.0, -68.5, -29.5), (49.5, 65.5, 0.0, 31.5, 68.5)]
    for x0, x1, y0, z0, z1 in fills:
        b = b + box3(x0, x1, y0, deck + 0.5, z0, z1)
    for zh in (-60.0, -30.0, 30.0, 60.0):                     # the yoke's four screw holes
        h = trimesh.creation.cylinder(radius=1.85, height=2.3, sections=32)
        h.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
        h.apply_translation([81.02, 1.0, zh])
        b = b + M(h)
    for x0, x1, y0, z0, z1 in fills:
        b = b - box3(x0, x1, deck, deck + 1.0, z0, z1)
    # ...and nothing may reach below the base's own underside: a fill that pokes out even 0.15 mm
    # becomes the only thing touching the print bed
    bottom = float(base.vertices[:, 1].min())
    b = b - box3(-200.0, 200.0, bottom - 5.0, bottom, -200.0, 200.0)
    for sx, sz in STUDS:
        b = b + stud(sx, sz)
    # raised arrow beside the holder (knob side): the way to slide the holder to unlock it (toward the pad)
    arrow = Polygon([(62.0, 71.5), (68.0, 67.5), (68.0, 70.5), (80.0, 70.5), (80.0, 72.5), (68.0, 72.5), (68.0, 75.5)])
    am = trimesh.creation.extrude_polygon(arrow, 0.65)
    v = am.vertices.copy()
    am.vertices = np.column_stack([v[:, 0], v[:, 2] + deck - 0.05, v[:, 1]])
    am.invert()
    b = b + M(am)
    return b


LINER_T = 8.0                                    # the small-avocado liner makes the floor this much thicker


def build_liner():
    """Drop-in floor liner for small avocados (about 45 to 65 mm across). It lifts the fruit 8 mm, so a
    57 mm one has its middle at pad height instead of a 70 mm one. It lies on the floor between the side
    walls, stops 0.8 mm short of the door, and two hooks at its front corners reach down over the floor's
    front edge and tuck 1.6 mm under it, so it cannot slide back when the pad pushes. The hooks are
    outside the sled's width. To fit it: tilt it, hook the front, lower the back."""
    top_b = V0 + LINER_T * U_W + 0.8 * U_F
    top_f = F1 + LINER_T * U_W
    plate = Polygon([tuple(F1 + 0.15 * U_W), tuple(V0 + 0.15 * U_W + 0.8 * U_F), tuple(top_b), tuple(top_f)])
    liner = prism(plate, -HALF_IN + 0.4, HALF_IN - 0.4)
    xf, nose = F1[0], F1[1] - 3.0                 # the floor's front face, and where its 45 deg underside starts
    x0 = xf - 2.3
    y_top = top_f[1] + (top_f[0] - x0) * math.tan(A)
    hook = Polygon([(x0, y_top), tuple(top_f), tuple(F1 + 0.15 * U_W), (xf - 0.3, F1[1] + 0.2), (xf - 0.3, nose - 0.12),
                    (xf + 1.3, nose - 1.72), (xf + 1.3, nose - 2.5), (x0, nose - 2.5)])
    for z0, z1 in ((26.0, HALF_IN - 0.4), (-HALF_IN + 0.4, -26.0)):
        liner = liner + prism(hook, z0, z1)
    return liner


def liner_to_print(t):
    """top face down, hooks up"""
    t = t.copy()
    ez = np.array([U_W[0], U_W[1], 0.0]) * -1.0
    ey = np.array([0.0, 0.0, 1.0])
    ex = np.cross(ey, ez)
    t.vertices = t.vertices @ np.vstack([ex, ey, ez]).T
    lo, hi = t.bounds
    t.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    return t


def servo_solid():
    """the servo as fitted (+z side), for the fit checks and the renders"""
    s = box3(SERVO[0] - 16.6, SERVO[0] + 5.9, SERVO[1] - 6.1, SERVO[1] + 6.1, ZC - 15.9, Z_CASE)
    s = s + box3(SERVO[0] - 21.3, SERVO[0] + 10.6, SERVO[1] - 6.1, SERVO[1] + 6.1, Z_TAB[0], Z_TAB[1])
    s = s + cyl_z(SERVO, 5.9, Z_CASE - 0.1, 71.8) + cyl_z(SERVO, 2.4, 71.7, 75.0, 24)
    return s


# ---------------------------------------------------------------- print orientation
def to_print(m, kind):
    m = m.copy()
    v = m.vertices.copy()
    if kind == "base":                      # inverse of the mapping used to load base.stl: same place as before
        m.vertices = np.column_stack([v[:, 2], v[:, 0] - 20.5, v[:, 1]])
        return m
    if kind == "frame":                     # upright, keyholes on the bed
        m.vertices = np.column_stack([v[:, 0], -v[:, 2], v[:, 1]])
    elif kind == "door":                    # inner face down
        ez = np.array([N_W[0], N_W[1], 0.0])
        ey = np.array([0.0, 0.0, 1.0])
        ex = np.cross(ey, ez)
        m.vertices = v @ np.vstack([ex, ey, ez]).T
    elif kind in ("lever", "link"):         # outer face down (parts are on the -z side after mirroring)
        m.vertices = np.column_stack([v[:, 0], v[:, 1], v[:, 2]])
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    return m


# ---------------------------------------------------------------- checks
def checks(frame, door, lever, link, base_new):
    """everything here is in the +z build, so the base, sled and blade are mirrored to match"""
    ok = True

    def rep(name, v, lim=0.05):
        nonlocal ok
        good = v <= lim
        ok &= good
        print(f"  {'ok ' if good else 'BAD'} {name}: {v:.3f} mm3")

    print("fit checks")
    base_m = mirror_z(base_new)
    liner = build_liner()
    rep("liner vs frame", vol(liner ^ frame), 0.3)
    worst_l = 0.0
    for th in np.linspace(TH_CLOSED, TH_OPEN, 30):
        dd = math.degrees(th - TH_CLOSED)
        worst_l = max(worst_l, vol(door.translate([-HINGE[0], -HINGE[1], 0]).rotate([0, 0, dd]).translate([HINGE[0], HINGE[1], 0]) ^ liner))
    rep("liner vs door, whole swing (worst)", worst_l, 0.3)
    rep("frame vs base", vol(frame ^ base_m), 0.5)
    rep("frame vs base while being dropped on (9 mm toward the pad)", vol(frame.translate([-SLIDE, 0, 0]) ^ base_m), 0.5)
    srv = servo_solid()
    rep("servo vs frame", vol(srv ^ frame), 0.5)
    rep("servo vs base", vol(srv ^ base_m))
    sled = trimesh.load(STL / "v45" / "v45-sled.stl", force="mesh")
    s = sled.vertices.copy()
    blade = trimesh.load(STL / "v45" / "v45-blade.stl", force="mesh")
    bl = blade.vertices.copy()
    for travel in (0.0, MAX_TRAVEL):
        sled.vertices = np.column_stack([s[:, 2] - 22.0 + travel, s[:, 1] + 36.5, s[:, 0]])
        blade.vertices = np.column_stack([bl[:, 2] + 2.1 + travel, bl[:, 1] + 43.5, bl[:, 0]])
        def flipped(mesh):                 # the z mirror turns the mesh inside out: put the faces back
            return M(trimesh.Trimesh(mesh.vertices, mesh.faces[:, ::-1], process=False))
        sm, bm = flipped(sled), flipped(blade)
        pad = trimesh.creation.cylinder(radius=8.0, height=11.4, sections=48)
        pad.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
        pad.apply_translation([28.0 + travel - 5.7, PAD_Y, 0.0])
        rep(f"frame vs sled at travel {travel:.0f}", vol(frame ^ sm))
        rep(f"liner vs sled, blade and pad at travel {travel:.0f}", vol(liner ^ sm) + vol(liner ^ bm) + vol(liner ^ M(pad)))
        if travel > 0:
            lg = -trimesh.proximity.signed_distance(T(liner), sled.sample(3000)).max()
            print(f"  {'ok ' if lg >= 1.0 else 'BAD'} closest the sled gets to the liner at max travel: {lg:.1f} mm")
            ok &= lg >= 1.0
        rep(f"frame and door vs blade and pad at travel {travel:.0f}", vol(frame ^ bm) + vol(door ^ bm) + vol(frame ^ M(pad)))
        if travel > 0:
            gap = -trimesh.proximity.signed_distance(T(frame), sled.sample(3000)).max()
            print(f"  {'ok ' if gap >= 1.9 else 'BAD'} closest the sled gets to the frame at max travel {MAX_TRAVEL:.0f}: {gap:.1f} mm")
            ok &= gap >= 1.9
    mot = motion(40) + [over_pose(math.radians((LUG_TOUCH or 5.0) - 0.3))]
    case = prism(servo_case_profile(), Z_TAB[0], 71.8)
    worst = dict.fromkeys(["door vs frame", "door vs base", "lever vs frame, base, servo", "link vs frame, base, servo", "link vs lever", "horn vs frame, base, link"], 0.0)
    for i, (th, P, C, phi) in enumerate(mot):
        dd = math.degrees(th - TH_CLOSED)

        def swing(part):
            return part.translate([-HINGE[0], -HINGE[1], 0]).rotate([0, 0, dd]).translate([HINGE[0], HINGE[1], 0])
        dr, lv = swing(door), swing(lever)
        worst["door vs frame"] = max(worst["door vs frame"], vol(dr ^ frame))
        worst["door vs base"] = max(worst["door vs base"], vol(dr ^ base_m))
        worst["lever vs frame, base, servo"] = max(worst["lever vs frame, base, servo"], vol(lv ^ frame) + vol(lv ^ base_m) + vol(lv ^ srv))
        lk = prism(link_profile(P, C), Z_LINK[0], Z_LINK[1]) + cyl_z(P, 3.5, Z_LEVER[1] + 0.2, Z_LINK[0] + 0.05, 32)
        lk = lk + cyl_z(lug_point(P, C), LUG_R, Z_HORN[0] + 0.2, Z_LINK[0] + 0.05, 24)
        worst["link vs frame, base, servo"] = max(worst["link vs frame, base, servo"], vol(lk ^ frame) + vol(lk ^ base_m) + vol(lk ^ srv))
        if True:
            worst["link vs lever"] = max(worst["link vs lever"], vol(lk ^ lv))
        hn = prism(horn_profile(phi), Z_HORN[0], Z_HORN[1])
        worst["horn vs frame, base, link"] = max(worst["horn vs frame, base, link"], vol(hn ^ frame) + vol(hn ^ base_m) + vol(hn ^ lk))
    for k, v in worst.items():
        rep(f"{k}, whole swing (worst)", v, 0.3)
    hub = min(link_profile(P, C).distance(Point(*SERVO)) for _, P, C, _ in mot)
    print(f"  {'ok ' if hub >= 3.3 else 'BAD'} link stays {hub:.1f} mm clear of the horn's hub screw (needs 3.3)")
    ok &= hub >= 3.3
    low = min(min(y for _, y in horn_profile(phi).exterior.coords) for *_, phi in mot)
    print(f"  {'ok ' if low >= DECK + 0.8 else 'BAD'} horn's lowest point is {low - DECK:.1f} mm above the deck")
    ok &= low >= DECK + 0.8
    tr = []
    for th, P, C, phi in mot[:-1]:
        u = (P - C) / np.linalg.norm(P - C)
        t = np.array([-(P - HINGE)[1], (P - HINGE)[0]]) / RP
        tr.append(90 - math.degrees(math.acos(abs(float(u @ t)))))
    print(f"  link {LINK:.1f} mm between holes; servo turns {SWEEP:.0f} deg to open (+{LUG_TOUCH or 0:.1f} past in-line to the stop); "
          f"worst transmission angle {min(tr):.0f} deg; seen from the horn side it turns {'clockwise' if OPEN_SIGN > 0 else 'counter-clockwise'} to open")
    ok &= min(tr) > 35 and LUG_TOUCH is not None and 3.0 <= LUG_TOUCH <= 7.0
    parts = len(T(frame).split(only_watertight=False))
    print(f"  {'ok ' if parts == 1 else 'BAD'} frame is one piece ({parts})")
    ok &= parts == 1
    print(f"where the pad meets each size (pad tip is at x 28 at home, {28 + MAX_TRAVEL:.0f} at max travel {MAX_TRAVEL:.0f})")
    for d in (45, 50, 55, 60, 65, 70, 75, 80):
        r = d / 2
        c = V0 + r * U_F + r * U_W
        dy = PAD_Y - c[1]
        x = c[0] - math.sqrt(r * r - dy * dy)
        good = 28.0 + 2.0 <= x <= 28.0 + MAX_TRAVEL - 1.0
        ok &= good
        print(f"  {'ok ' if good else 'BAD'} {d} mm: travel {x - 28.0:4.1f} of {MAX_TRAVEL:.0f}, pad {abs(dy):4.1f} mm {'above' if dy > 0 else 'below'} the middle ({math.degrees(math.asin(abs(dy) / r)):.0f} deg off square)")
    print(f"with the liner in ({LINER_T:.0f} mm)")
    for d in (45, 50, 55, 57, 60, 65):
        r = d / 2
        c = V0 + r * U_F + (r + LINER_T) * U_W
        dy = PAD_Y - c[1]
        x = c[0] - math.sqrt(r * r - dy * dy)
        good = 28.0 + 2.0 <= x <= 28.0 + MAX_TRAVEL - 1.0
        ok &= good
        print(f"  {'ok ' if good else 'BAD'} {d} mm: travel {x - 28.0:4.1f} of {MAX_TRAVEL:.0f}, pad {abs(dy):4.1f} mm {'above' if dy > 0 else 'below'} the middle ({math.degrees(math.asin(abs(dy) / r)):.0f} deg off square)")
    return ok


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = pathlib.Path(args[0]) if args else STL
    out.mkdir(parents=True, exist_ok=True)
    frame, door, lever, link, base_new = build_frame(), build_door(), build_lever(), build_link(), build_base()
    print(f"over-centre stop: the horn's arm meets the link's lug {LUG_TOUCH} deg past in-line")
    ok = checks(frame, door, lever, link, base_new)
    parts = {"gate-frame": (mirror_z(frame), "frame"), "gate-door": (mirror_z(door), "door"), "gate-lever": (mirror_z(lever), "lever"),
             "gate-link": (mirror_z(link), "link"), "base": (base_new, "base")}
    for name, (man, kind) in parts.items():
        t = T(man)
        ok &= t.is_watertight
        p = to_print(t, kind)
        p.export(out / f"{name}.stl")
        if "--model" in sys.argv:
            t.export(out / f"{name}-model.stl")
        print(f"{name}: watertight {t.is_watertight}, {t.volume / 1000:.1f} cm3, print size {np.round(p.extents, 1).tolist()}")
    lt = T(build_liner())
    ok &= lt.is_watertight
    lp = liner_to_print(lt)
    lp.export(out / "gate-liner-small.stl")
    if "--model" in sys.argv:
        lt.export(out / "gate-liner-small-model.stl")
    print(f"gate-liner-small: watertight {lt.is_watertight}, {lt.volume / 1000:.1f} cm3, print size {np.round(lp.extents, 1).tolist()}")
    if not ok:
        sys.exit("a check failed")


if __name__ == "__main__":
    main()
