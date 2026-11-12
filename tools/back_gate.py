#!/usr/bin/env python3
"""V-holder with a servo back gate, and the base with keyhole studs for it.

    python3 tools/back_gate.py [out_dir] [--model]

Writes (print orientation):
    base.stl                 the base: old yoke recess and its 4 screw holes filled, 4 BTL mushroom studs added
    gate-frame.stl           floor, end walls, servo housing; clicks onto the studs (4 keyholes)
    gate-door.stl            the back wall, hinged at the bottom corner
    gate-lever.stl           fits through the end wall into the door's D socket
    gate-link.stl            joins the lever to the servo horn
and checks every fit and every motion for collisions.

How it works
------------
The avocado lies in a V: a floor tilted 12 deg down toward the back and a back wall square
to it (see tools/v_holder.py for why). The back wall is a door. Its hinge axis is 5 mm under
the floor and 5 mm behind the wall, so when it swings back 88 deg its inner face lines up with
the floor and the avocado rolls straight out the back, with no hinge bump to climb.

An SG90 / MG90S servo outside the +z end wall drives the door through a lever and a link (a
four-bar). With the door shut the servo crank and the link lie in one straight line, so the
pad's push on the door goes along the link into the servo shaft's bearing and not into its
gears: the door is locked even with the servo unpowered. The firmware's Tip action (rest
angle -> tip angle, hold, back) opens it for the hold time and shuts it again.

The frame clicks onto 4 studs (the v3 stud of the BTL universal mount) through 4 keyholes
(the v6 keyhole) in its bottom: drop it on 9 mm toward the pad from its place and push it
back until it clicks. The pad's push is in the locking direction.

Model coordinates (as the Fusion assembly): x = press axis toward the holder, y = up,
z = across. Pad centre y 62; V45 pad tip at x 28 at home, 65 at max travel 37.
"""
import sys
import math
import pathlib
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import Polygon, Point, MultiPoint, box as sbox
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parent.parent
STL = ROOT / "hardware" / "stl"

# ---------------------------------------------------------------- the V
A = math.radians(12.0)
PAD_Y = 62.0
V0 = np.array([106.0, PAD_Y - 40.0 * (math.sin(A) + math.cos(A)) + 0.5])   # inner corner
U_F = np.array([-math.cos(A), math.sin(A)])      # along the floor toward the pad
U_W = np.array([math.sin(A), math.cos(A)])       # up the wall
N_F = np.array([-math.sin(A), -math.cos(A)])     # out of the floor (down)
N_W = np.array([math.cos(A), -math.sin(A)])      # out of the wall (back)
LF = 52.0                                        # floor length from the corner
F1 = V0 + LF * U_F                               # front edge of the floor (top)
HALF_IN = 56.0                                   # 112 mm between the end walls
CHEEK = 5.0
ZC = HALF_IN + CHEEK                             # 61
DECK = 5.0

# ---------------------------------------------------------------- the door and the four-bar
T_DOOR, L_DOOR = 5.0, 55.0
HINGE = V0 + 5.0 * N_F + 5.0 * N_W               # (109.85, 9.13): 5 under the floor, 5 behind the wall
TH_CLOSED, TH_OPEN = math.radians(78.0), math.radians(-10.0)   # door direction (U_W is 78 deg)
DOOR_HALF = HALF_IN - 0.4
KNUCKLE_R, BOSS_R, BOSS_LEN = 5.0, 6.0, 10.0
RP, ALPHA = 18.0, math.radians(60.0)             # lever pin: 18 mm from the hinge, 60 deg ahead of the door
CRANK = 15.0                                     # servo horn hole 15 mm from the shaft
SERVO = np.array([136.0, 36.0])                  # servo shaft
Z_LEVER = (61.5, 64.5)
Z_LINK = (64.8, 67.8)
Z_HORN = (67.9, 72.3)                            # horn arm + hub
Z_POD = (70.3, 79.1)                             # housing: floor 70.3-72.3, cavity to the tab face at 79.1

# ---------------------------------------------------------------- keyholes / studs
STUDS = [(76.0, -30.0), (92.0, -30.0), (76.0, 30.0), (92.0, 30.0)]   # final stud positions (= slot ends)
SLIDE = 9.0                                      # rounds are 9 mm further back (+x) than the slot ends


def e(a):
    return np.array([math.cos(a), math.sin(a)])


def rot(p, c, a):
    p = np.asarray(p, float) - c
    return c + np.array([p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a)])


def floor_top_y(x):
    return V0[1] + (V0[0] - x) * math.tan(A)


# ---------------------------------------------------------------- mesh helpers
def prism(poly, z0, z1):
    if hasattr(poly, "geoms"):
        out = None
        for g in poly.geoms:
            m = prism(g, z0, z1)
            out = m if out is None else out + m
        return out
    p = poly if isinstance(poly, Polygon) else Polygon(poly)
    p = p.buffer(0)
    m = trimesh.creation.extrude_polygon(p, z1 - z0)
    m.apply_translation([0, 0, z0])
    return M(m)


def M(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))


def T(man):
    mm = man.to_mesh()
    t = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts))
    t.merge_vertices()
    return t


def cyl_z(c, r, z0, z1, n=64):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=n)
    m.apply_translation([c[0], c[1], (z0 + z1) / 2])
    return M(m)


def vol(man):
    return T(man).volume if man.num_vert() else 0.0


# ---------------------------------------------------------------- 2D profiles of the moving parts
def door_profile(th):
    """door outline in (x, y) at door angle th (closed = 78 deg), with its knuckle"""
    d = th - TH_CLOSED
    q0 = V0 - 5.0 * U_W                                      # inner face, bottom
    pts = [q0, V0 + L_DOOR * U_W, V0 + L_DOOR * U_W + T_DOOR * N_W, q0 + T_DOOR * N_W]
    poly = Polygon([rot(p, HINGE, d) for p in pts]).union(Point(*HINGE).buffer(KNUCKLE_R, 48))
    return poly


def pin(th):
    return HINGE + RP * e(th + ALPHA)


def crank_angle(P, prev):
    l = LINK
    d = np.linalg.norm(P - SERVO)
    base = math.atan2(*(P - SERVO)[::-1])
    g = math.acos(max(-1, min(1, (CRANK ** 2 + d * d - l * l) / (2 * CRANK * d))))
    return min([base + g, base - g], key=lambda a: abs((a - prev + math.pi) % (2 * math.pi) - math.pi))


LINK = float(np.linalg.norm(SERVO - pin(TH_CLOSED)) - CRANK)   # straight (toggle) when shut


def motion(n=60):
    """door angle, pin, crank tip at n steps from shut to open"""
    out = []
    prev = math.atan2(*(pin(TH_CLOSED) - SERVO)[::-1])
    for th in np.linspace(TH_CLOSED, TH_OPEN, n):
        P = pin(th)
        phi = crank_angle(P, prev); prev = phi
        out.append((th, P, SERVO + CRANK * e(phi), phi))
    return out


def lever_profile(th):
    P = pin(th)
    arm = Polygon([HINGE + 4.0 * e(th + ALPHA + math.pi / 2), P + 4.0 * e(th + ALPHA + math.pi / 2),
                   P - 4.0 * e(th + ALPHA + math.pi / 2), HINGE - 4.0 * e(th + ALPHA + math.pi / 2)])
    return arm.union(Point(*HINGE).buffer(7.0, 48)).union(Point(*P).buffer(4.5, 32))


def link_profile(P, C):
    u = (C - P) / np.linalg.norm(C - P); n = np.array([-u[1], u[0]])
    return Polygon([P + 3.5 * n, C + 3.5 * n, C - 3.5 * n, P - 3.5 * n]).union(Point(*P).buffer(3.5, 32)).union(Point(*C).buffer(3.5, 32))


def horn_profile(phi):
    C = SERVO + CRANK * e(phi)
    u = e(phi); n = np.array([-u[1], u[0]])
    tip = SERVO + (CRANK + 3.0) * u
    return Polygon([SERVO + 3.5 * n, tip + 2.5 * n, tip - 2.5 * n, SERVO - 3.5 * n]).union(Point(*SERVO).buffer(4.0, 32))


# ---------------------------------------------------------------- keyhole (v6) and stud (v3)
def keyhole_cut(round_xy, slot_end_xy):
    """cut for one keyhole in a 4 mm floor whose underside is at y = DECK: the 8.8 round, the
    5.4 slot running from the round to slot_end, a 45 deg flare to 8.8 wide between 1.5 and 3.2
    above the underside, and two r 0.35 detent nibs 2.45 before the slot end in the bottom 1.5."""
    rx, rz = round_xy; ex, ez = slot_end_xy
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
    flare = trimesh.convex.convex_hull(np.array(to3d(stadium(5.4), DECK + 1.5) + to3d(stadium(8.76), DECK + 3.2)))
    cut = cut + M(flare)
    cut = cut + M(slab(stadium(8.76), DECK + 3.18, DECK + 4.2))
    d = np.array([ex - rx, ez - rz]); d /= np.linalg.norm(d); nrm = np.array([-d[1], d[0]])
    for sgn in (1, -1):
        c = np.array([ex, ez]) - 2.45 * d + sgn * 2.7 * nrm
        nib = trimesh.creation.cylinder(radius=0.35, height=1.7, sections=24)
        nib.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
        nib.apply_translation([c[0], DECK + 0.75, c[1]])
        cut = cut - M(nib)
    return cut


def stud(x, z):
    prof = [(0, 0), (2.5, 0), (2.5, 1.4), (4.0, 2.9), (4.0, 2.95), (3.65, 3.3), (0, 3.3)]
    m = trimesh.creation.revolve(prof, sections=64)            # around +z
    v = m.vertices.copy(); m.vertices = np.column_stack([v[:, 0] + x, v[:, 2] + DECK - 0.05, -v[:, 1] + z])
    if m.volume < 0: m.invert()
    return M(m)


# ---------------------------------------------------------------- parts
def build_frame():
    # end walls: the V outline plus the area round the hinge
    door_top_in = V0 + L_DOOR * U_W
    door_top_out = door_top_in + T_DOOR * N_W
    cheek = MultiPoint([tuple(F1), (F1[0], 14.0), (70.5, DECK), (115.0, DECK), tuple(HINGE + np.array([6.0, 0])),
                        tuple(door_top_out), tuple(door_top_in)]).convex_hull
    body = prism(cheek, -ZC, -HALF_IN) + prism(cheek, HALF_IN, ZC)
    # servo side: the end wall carries on back to the servo housing
    body = body + prism(sbox(104.0, DECK, 159.0, 46.0), HALF_IN, ZC)
    # floor: front strip with a flat underside above the sled (y 20.5), full depth behind
    # floor slab: flat underside at y 20.5 where the sled can reach (x <= 66), 3 mm thick further back
    # (never below 13.6, so it clears the rails while the frame is being dropped on)
    xs = np.linspace(66.0, V0[0], 12)
    bottom = [(x, max(13.6, floor_top_y(x) - 3.0)) for x in xs[::-1]]
    slab = Polygon([tuple(F1), tuple(V0)] + bottom + [(F1[0], 20.5)])
    body = body + prism(slab, -HALF_IN - 0.4, HALF_IN + 0.4)
    def under(x0):   # solid from the deck up to the floor top, from x0 back to the corner
        return Polygon([(x0, DECK), (V0[0] + 2.0, DECK), (V0[0] + 2.0, floor_top_y(V0[0] + 2.0)), (x0, floor_top_y(x0))])
    body = body + prism(under(67.0), -17.4, 17.4)               # between the rails (inner edges at |z| 18; clear of the sled at max travel)
    body = body + prism(under(80.0), -26.0, -17.3) + prism(under(80.0), 17.3, 26.0)   # over the rails: clear of them when dropped on
    body = body + prism(under(70.5), -HALF_IN - 0.5, -26.0) + prism(under(70.5), 26.0, HALF_IN + 0.5)
    for zr in (-28.0, 28.0):                                    # front ribs, beside the rails
        rib = Polygon([(F1[0] + 0.5, 14.0), (70.6, 14.0), (70.6, floor_top_y(70.6) - 0.2), (F1[0] + 0.5, floor_top_y(F1[0] + 0.5) - 0.2)])
        body = body + prism(rib, zr - 2.0, zr + 2.0)
    # servo housing: tower, bottom and back connectors (all outside the lever / link / horn sweeps)
    body = body + prism(sbox(112.0, DECK, 159.0, 46.0), Z_POD[0], Z_POD[1])
    body = body + prism(sbox(119.0, DECK, 159.0, 16.0), ZC - 0.1, Z_POD[0] + 0.1)
    body = body + prism(sbox(155.0, 15.0, 159.0, 46.0), ZC - 0.1, Z_POD[0] + 0.1)
    # servo cavity: body 22.5 x 12.2 (shaft 5.9 from the end, long side toward the base)
    cav = sbox(SERVO[0] - 16.6 - 0.5, SERVO[1] - 6.1 - 0.4, SERVO[0] + 5.9 + 0.5, SERVO[1] + 6.1 + 0.4)
    body = body - prism(cav, Z_POD[0] + 2.0, Z_POD[1] + 0.1)
    boss = Point(*SERVO).buffer(7.0, 48).union(Point(SERVO[0] - 6.0, SERVO[1]).buffer(3.5, 32)).convex_hull
    body = body - prism(boss, Z_POD[0] - 0.1, Z_POD[0] + 2.1)
    for dx in (-13.9, 13.9):                                    # tab screws (M2 self-tap), 27.8 apart round the body centre
        body = body - cyl_z((SERVO[0] - 5.35 + dx, SERVO[1]), 0.9, Z_POD[1] - 8.0, Z_POD[1] + 0.1, 24)
    # clearances for everything that moves
    sweep_door = unary_union([door_profile(th).buffer(0.6) for th in np.linspace(TH_CLOSED, TH_OPEN, 45)])
    # (the door's swing is cut 0.3 mm into the end walls' inner faces: no slivers where floor meets wall)
    body = body - prism(sweep_door, -HALF_IN - 0.3, HALF_IN + 0.3)
    body = body - cyl_z(HINGE, BOSS_R + 0.5, -HALF_IN - 0.3, HALF_IN + 0.3)
    mot = motion(60)
    sweep_lever = unary_union([lever_profile(th).buffer(1.0) for th, *_ in mot])
    sweep_link = unary_union([link_profile(P, C).buffer(1.0) for _, P, C, _ in mot])
    sweep_horn = unary_union([horn_profile(phi).buffer(1.0) for *_, phi in mot])
    body = body - prism(sweep_lever, Z_LEVER[0] - 0.4, Z_LEVER[1] + 0.2)
    body = body - prism(sweep_link, Z_LINK[0] - 0.2, Z_LINK[1] + 0.2)
    body = body - prism(sweep_horn, Z_HORN[0] - 0.2, Z_POD[0])
    # hinge bores: M3 pin on the -z side, the lever's 7.6 shaft on the +z side
    body = body - cyl_z(HINGE, 1.7, -ZC - 0.1, -HALF_IN + 0.1, 32)
    body = body - cyl_z(HINGE, 4.0, HALF_IN - 0.1, ZC + 0.1, 48)
    # keyholes
    for sx, sz in STUDS:
        body = body - keyhole_cut((sx + SLIDE, sz), (sx, sz))
    return body, sweep_door, sweep_lever, sweep_link, sweep_horn


def d_shape(c, r, flat, n_dir):
    circ = Point(*c).buffer(r, 64)
    hp = Polygon([c - 20 * n_dir + 20 * np.array([-n_dir[1], n_dir[0]]), c + flat * n_dir + 20 * np.array([-n_dir[1], n_dir[0]]),
                  c + flat * n_dir - 20 * np.array([-n_dir[1], n_dir[0]]), c - 20 * n_dir - 20 * np.array([-n_dir[1], n_dir[0]])])
    return circ.intersection(hp)


def build_door():
    # the knuckle is r 6 along the whole hinge edge, cut flush with the inner face (no bump where the
    # fruit rolls out; the flat sits 0.05 inside the face so the union has no coplanar faces)
    knuckle = Point(*HINGE).buffer(BOSS_R, 64).intersection(
        Polygon([V0 + 0.05 * N_W - 30 * U_W, V0 + 0.05 * N_W + 30 * U_W, V0 + 30 * U_W + 30 * N_W, V0 - 30 * U_W + 30 * N_W]))
    d = door_profile(TH_CLOSED).difference(Point(*HINGE).buffer(KNUCKLE_R, 48)).union(knuckle)
    door = prism(d, -DOOR_HALF, DOOR_HALF)
    # +z end: D socket for the lever (7.0, flat 2.9 from the axis, toward the back) and the screw pilot beyond
    door = door - prism(d_shape(HINGE, 3.5, 2.9, N_W), DOOR_HALF - 8.0, DOOR_HALF + 0.1)
    door = door - cyl_z(HINGE, 1.4, DOOR_HALF - 18.0, DOOR_HALF - 7.9, 32)
    # -z end: pilot for the M3 hinge pin
    door = door - cyl_z(HINGE, 1.4, -DOOR_HALF - 0.1, -DOOR_HALF + 10.0, 32)
    return door


def build_lever():
    lev = prism(lever_profile(TH_CLOSED), Z_LEVER[0], Z_LEVER[1])
    lev = lev + cyl_z(HINGE, 3.8, HALF_IN, Z_LEVER[0] + 0.1)                       # round shaft through the end wall
    lev = lev + prism(d_shape(HINGE, 3.4, 2.75, N_W), DOOR_HALF - 7.7, HALF_IN + 0.1)   # D into the door
    lev = lev - cyl_z(HINGE, 1.7, DOOR_HALF - 8.0, Z_LEVER[1] + 0.1, 32)            # M3 x 25 along the axis
    lev = lev - cyl_z(HINGE, 3.1, Z_LEVER[1] - 1.5, Z_LEVER[1] + 0.1, 32)            # head seat
    lev = lev - cyl_z(pin(TH_CLOSED), 1.4, Z_LEVER[0] - 0.1, Z_LEVER[1] + 0.1, 32)   # pilot for the link's M3 pivot
    return lev


def build_link():
    P = pin(TH_CLOSED); C = SERVO + CRANK * e(math.atan2(*(P - SERVO)[::-1]))
    ln = prism(link_profile(P, C), Z_LINK[0], Z_LINK[1])
    ln = ln - cyl_z(P, 1.7, Z_LINK[0] - 0.1, Z_LINK[1] + 0.1, 32)
    ln = ln - cyl_z(C, 1.1, Z_LINK[0] - 0.1, Z_LINK[1] + 0.1, 32)
    return ln


def build_base():
    base = trimesh.load(STL / "base-v1-yoke-slot.stl", force="mesh")   # the base before this change (idempotent)
    v = base.vertices.copy(); base.vertices = np.column_stack([v[:, 1] + 20.5, v[:, 2], v[:, 0]])
    if base.volume < 0: base.invert()
    b = M(base)
    fill = trimesh.creation.box(extents=[15.9, 3.1, 148.9]); fill.apply_translation([81.0, 3.445, 0.0])   # old yoke recess, flush with the deck
    b = b + M(fill)
    for zh in (-60.0, -30.0, 30.0, 60.0):
        h = trimesh.creation.cylinder(radius=1.85, height=2.3, sections=32)
        h.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
        h.apply_translation([81.02, 1.0, zh])
        b = b + M(h)
    for sx, sz in STUDS:
        b = b + stud(sx, sz)
    return b


# ---------------------------------------------------------------- print orientation
def to_print(m, kind):
    m = m.copy()
    v = m.vertices.copy()
    if kind == "base":                      # inverse of the model mapping used for base.stl
        m.vertices = np.column_stack([v[:, 2], v[:, 0] - 20.5, v[:, 1]])
        return m                            # keep the original placement
    if kind == "frame":                     # upright, as installed
        m.vertices = np.column_stack([v[:, 0], -v[:, 2], v[:, 1]])
    elif kind == "door":                    # inner face down (the hinge knuckle is behind the outer face)
        ez = np.array([N_W[0], N_W[1], 0.0]); ey = np.array([0.0, 0.0, 1.0]); ex = np.cross(ey, ez)
        m.vertices = v @ np.vstack([ex, ey, ez]).T
    elif kind in ("lever", "link"):         # outer face down, shaft up
        m.vertices = np.column_stack([v[:, 0], -v[:, 1], -v[:, 2]])
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    return m


# ---------------------------------------------------------------- checks
def checks(frame, door, lever, link, base_new, sweeps):
    ok = True
    def rep(name, v, lim=0.05):
        nonlocal ok
        flag = v <= lim
        ok &= flag
        print(f"  {'ok ' if flag else 'BAD'} {name}: {v:.3f} mm3")
    print("fit checks")
    rep("frame vs base", vol(frame ^ base_new), 0.5)
    dropped = frame.translate([-SLIDE, 0, 0])
    rep("frame vs base while being dropped on (9 mm toward the pad)", vol(dropped ^ base_new), 0.5)
    sled = trimesh.load(STL / "v45" / "v45-sled.stl", force="mesh"); s = sled.vertices.copy()
    blade = trimesh.load(STL / "v45" / "v45-blade.stl", force="mesh"); bl = blade.vertices.copy()
    for travel in (0.0, 37.0):
        sled.vertices = np.column_stack([s[:, 2] - 22.0 + travel, s[:, 1] + 36.5, -s[:, 0]])
        blade.vertices = np.column_stack([bl[:, 2] + 2.1 + travel, bl[:, 1] + 43.5, -bl[:, 0]])
        rep(f"frame vs sled at travel {travel:.0f}", vol(frame ^ M(sled)))
        rep(f"frame vs blade at travel {travel:.0f}", vol(frame ^ M(blade)))
        rep(f"door vs blade at travel {travel:.0f}", vol(door ^ M(blade)))
    mot = motion(40)
    worst = {"door": 0.0, "door-base": 0.0, "lever": 0.0, "link": 0.0}
    for th, P, C, phi in mot:
        dd = th - TH_CLOSED
        dr = door.translate([-HINGE[0], -HINGE[1], 0]).rotate([0, 0, math.degrees(dd)]).translate([HINGE[0], HINGE[1], 0])
        worst["door"] = max(worst["door"], vol(dr ^ frame))
        worst["door-base"] = max(worst["door-base"], vol(dr ^ base_new))
        lv = lever.translate([-HINGE[0], -HINGE[1], 0]).rotate([0, 0, math.degrees(dd)]).translate([HINGE[0], HINGE[1], 0])
        worst["lever"] = max(worst["lever"], vol(lv ^ frame))
        lk = prism(link_profile(P, C), Z_LINK[0], Z_LINK[1])
        worst["link"] = max(worst["link"], vol(lk ^ frame) + vol(lk ^ lv) * 0)
    for k, v in worst.items():
        rep(f"{k} through its whole swing (worst)", v, 0.5)
    # transmission and toggle
    tr = []
    for th, P, C, phi in mot:
        u = (P - C) / np.linalg.norm(P - C); t = np.array([-(P - HINGE)[1], (P - HINGE)[0]]) / RP
        tr.append(90 - math.degrees(math.acos(abs(float(u @ t)))))
    sweep = math.degrees(abs(np.unwrap([m[3] for m in mot])[-1] - np.unwrap([m[3] for m in mot])[0]))
    print(f"  link {LINK:.1f} mm, servo turns {sweep:.0f} deg, worst transmission angle {min(tr):.0f} deg (90 is ideal, >40 fine)")
    ok &= min(tr) > 38
    return ok


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = pathlib.Path(args[0]) if args else STL
    out.mkdir(parents=True, exist_ok=True)
    frame, *sweeps = build_frame()
    door, lever, link = build_door(), build_lever(), build_link()
    base_new = build_base()
    parts = {"gate-frame": (frame, "frame"), "gate-door": (door, "door"), "gate-lever": (lever, "lever"),
             "gate-link": (link, "link"), "base": (base_new, "base")}
    for name, (man, kind) in parts.items():
        t = T(man)
        print(f"{name}: watertight {t.is_watertight}, {t.volume / 1000:.1f} cm3, model bounds {np.round(t.bounds, 1).tolist()}")
    ok = checks(frame, door, lever, link, base_new, sweeps)
    for name, (man, kind) in parts.items():
        t = T(man)
        p = to_print(t, kind)
        p.export(out / f"{name}.stl")
        if "--model" in sys.argv:
            t.export(out / f"{name}-model.stl")
        print(f"wrote {out / (name + '.stl')}  print size {np.round(p.extents, 1).tolist()}")
    if not ok:
        sys.exit("a check failed")


if __name__ == "__main__":
    main()
