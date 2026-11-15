#!/usr/bin/env python3
"""Tipping V-holder: the whole V swings up and back on a servo to drop the avocado. No door, no linkage.

    python3 tools/tip_holder.py [out_dir] [--model]

Writes (print orientation):
    tip-frame.stl     two uprights on a sole plate; clicks onto the base's four holder studs
    tip-cradle.stl    the V (floor, back wall, two end plates) that hangs between the uprights
and checks every fit, the whole swing, the balance and the servo's load.

Why
---
With the back gate, the wall the avocado is pressed against was a door held by a lever, a link and a
servo horn: three joints between the wall and the frame, and a relaxed servo behind them. Here the V
is one rigid piece. It hangs on two pivots a little above the pad's height and rests on two stops, one
on each upright under the front tip of its floor:

  * gravity holds it there: with or without an avocado its weight is in front of the pivot, so it
    rests on the stops with the servo switched off;
  * the pad's push goes almost straight through the pivots into the uprights (the pivot is 4 mm above
    the pad's line), and what little turning effect is left presses the V DOWN on its stops;
  * the servo only works when it tips: it turns the V 100 degrees up and back, the back wall becomes a
    22 degree slide, the avocado rolls off its end behind the machine, and the V comes back.

The servo (MG90S) is screwed to the outside of the thick upright on the board side, shaft inward. Its
own single-arm horn lies in a pocket in the V's end plate and drives it; nothing is screwed to the
horn, and the horn cannot come off the shaft because the pocket's floor is behind it. The other
pivot is an M3 x 12 screw through the thin upright into the V.

Both pivot holes are V-seats, not round holes: the weight and the push always press the pin (or the
horn's hub) into the same corner, so there is no play to take up during a press.

Geometry of the V (corner, 12 degree floor, wall square to it) and the sled's tunnel are the same as
the back gate's, so the reach table is unchanged. Built on the +z side and mirrored at the end, so
the servo is on the board side (-z).

Model coordinates: x = press axis toward the holder, y = up, z = across. Pad centre y 62.
"""
import sys
import math
import pathlib
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point, LineString, MultiPoint, box as sbox

_argv, sys.argv = sys.argv, sys.argv[:1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import back_gate as g          # helpers, the V's corner, the keyholes, the base  # noqa: E402
sys.argv = _argv
from back_gate import M, T, prism, cyl_z, box3, vol, mirror_z, V0, U_F, U_W, N_F, N_W, A, DECK, PAD_Y, MAX_TRAVEL, STUDS, SLIDE, STL  # noqa: E402

# ---------------------------------------------------------------- the V
LF, LW = 46.0, 60.0                      # floor and wall lengths from the corner
T_FLOOR, T_WALL = 3.0, 4.0               # the floor is 3 mm so the sled passes 5 mm under its front
F1, W1 = V0 + LF * U_F, V0 + LW * U_W
F1o, W1o = F1 + T_FLOOR * N_F, W1 + T_WALL * N_W
VC = V0 + T_FLOOR * N_F + T_WALL * N_W   # outer corner
HC = 55.0                                # 110 mm between the end plates
T_PLATE = 3.0
ZP = HC + T_PLATE                        # 58: outer face of the end plates

# ---------------------------------------------------------------- pivot, uprights, servo
PIV = np.array([99.0, 66.0])             # pivot axis: 4 mm above the pad's line, behind every avocado's middle
TIP = 100.0                              # degrees the V turns to drop the avocado
GAP = 0.6                                # end plate to upright
ZI = ZP + GAP                            # 58.6: inner face of the uprights
T_UP_PIN, T_UP_SERVO = 5.0, 8.3          # the servo's upright is thick enough to bury the servo's gear boss
ZO_SERVO, ZO_PIN = ZI + T_UP_SERVO, ZI + T_UP_PIN
SOLE_TOP = DECK + 5.5
PAD_R, PAD_T = 19.5, 4.2                 # the thick disc inside the end plate that the horn pocket is cut in
HORN_ZONE = 5.6                          # pocket depth: room for horns up to this tall
HORN_ARM, HORN_HALF, HUB_R, HUB_SEAT = 17.5, 3.2, 4.6, 3.55   # arm slot reaches 17.5 from the axis, 6.4 wide; hub seat for a 7.1 hub
ARM_DIR = -math.pi / 2                   # the horn's arm points down when the V is at rest
STOP_S = (0.8, 5.0)                      # the stops carry the floor's underside from 0.8 to 5 mm behind its front tip


def rot_cw(man, deg):
    """turn a part about the pivot, clockwise seen from +z (the tipping direction)"""
    return man.translate([-PIV[0], -PIV[1], 0]).rotate([0, 0, -deg]).translate([PIV[0], PIV[1], 0])


def rot_pt(p, deg):
    a = -math.radians(deg)
    d = np.asarray(p, float) - PIV
    return PIV + np.array([d[0] * math.cos(a) - d[1] * math.sin(a), d[0] * math.sin(a) + d[1] * math.cos(a)])


def v_seat(c, r, seat, bisector_deg):
    """a pivot hole that is a V-seat: a circle of radius r with two flats at `seat` from the centre, 45 deg
    either side of the direction the pin is pressed in"""
    p = Point(*c).buffer(r, 48)
    for a in (bisector_deg - 45.0, bisector_deg + 45.0):
        n = np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])
        t = np.array([-n[1], n[0]])
        far = [c + seat * n + 20 * t, c + seat * n - 20 * t, c + 30 * n - 20 * t, c + 30 * n + 20 * t]
        p = p.difference(Polygon([tuple(q) for q in far]))
    return p


def plate_outline():
    hull = MultiPoint([tuple(q) for q in (F1, F1o, VC, W1o, W1)]).convex_hull.union(Point(*PIV).buffer(PAD_R, 64)).convex_hull
    # round the outer corner (it swings past the stops) but keep the floor's front tip sharp: it sits on them
    keep = Point(*F1o).buffer(9.0)
    out = hull.buffer(-3.0).buffer(3.0, 24).union(hull.intersection(keep))
    # nothing behind the wall's back face: that face is the print bed
    c = V0 + T_WALL * N_W
    behind = Polygon([tuple(c + 200 * U_W), tuple(c - 200 * U_W), tuple(c - 200 * U_W + 200 * N_W), tuple(c + 200 * U_W + 200 * N_W)])
    return out.difference(behind)


def horn_pocket():
    """hub (V-seat: pressed up and forward by the weight and the push) plus the arm slot"""
    hub = v_seat(PIV, HUB_R, HUB_SEAT, 110.0)
    tip = PIV + HORN_ARM * np.array([math.cos(ARM_DIR), math.sin(ARM_DIR)])
    return hub.union(LineString([tuple(PIV), tuple(tip)]).buffer(HORN_HALF, 16))


def build_cradle():
    v = prism([tuple(q) for q in (F1, V0, W1, W1o, VC, F1o)], -ZP + 0.01, ZP - 0.01)
    out = plate_outline()
    body = v + prism(out, HC, ZP) + prism(out, -ZP, -HC)
    # servo side (+z): the thick disc, then the horn pocket from the outside face
    body = body + prism(Point(*PIV).buffer(PAD_R, 64).intersection(out), HC - PAD_T, HC + 0.01)
    body = body - prism(horn_pocket(), ZP - HORN_ZONE, ZP + 0.1)
    # pin side (-z): a boss for the M3 x 12 (2.8 pilot: the screw cuts its own thread)
    body = body + cyl_z(PIV, 6.0, -HC - 0.01, -HC + 4.5, 48)
    body = body - cyl_z(PIV, 1.4, -ZP - 0.1, -HC + 4.6, 24)
    return body


def upright_outline():
    top = Point(PIV[0], PIV[1] + 10.6 + 2.5 - 12.0).buffer(12.0, 48)          # covers the servo's upper tab
    hull = MultiPoint([(53.0, DECK), (53.0, 24.5), (108.0, DECK), (108.0, 60.0)]).convex_hull.union(top).convex_hull
    out = hull.buffer(-4.0).buffer(4.0, 24).union(hull.intersection(sbox(0, DECK, 200, DECK + 8.0)))
    # the front of the bottom edge is lifted 1 mm: it passes over the raised arrows on the deck while the frame is dropped on
    return out.difference(Polygon([(0, 0), (60.0, 0), (60.0, DECK), (59.0, DECK + 1.0), (0, DECK + 1.0)]))


def stop_lug(sgn):
    """a 3 mm ledge on the upright's inner face under the floor's front tip, 45 deg underneath (prints unsupported)"""
    q0, q1 = F1o - STOP_S[0] * U_F + 0.05 * N_F, F1o - STOP_S[1] * U_F + 0.05 * N_F
    pts = []
    for q in (q0, q1):
        pts += [(q[0], q[1], sgn * (ZI + 0.5)), (q[0], q[1], sgn * (ZI - 3.0)), (q[0], q[1] - 3.2, sgn * (ZI + 0.5)), (q[0], q[1] - 3.2, sgn * (ZI - 0.02))]
    return M(trimesh.convex.convex_hull(np.array(pts)))


def build_frame():
    out = upright_outline()
    body = prism(out, ZI, ZO_SERVO) + prism(out, -ZO_PIN, -ZI)
    body = body + box3(80.0, 108.0, DECK, SOLE_TOP, -ZO_PIN, ZO_SERVO)                       # sole: back plate, behind the sled's reach
    body = body + box3(68.6, 80.1, DECK, SOLE_TOP, 26.5, ZO_SERVO) + box3(68.6, 80.1, DECK, SOLE_TOP, -ZO_PIN, -26.5)   # and two strips outside the rails
    body = body + stop_lug(1) + stop_lug(-1)
    # servo: case in from outside (22.5 x 12.2, long end down), tabs on the outer face, two pilot holes
    body = body - box3(PIV[0] - 6.5, PIV[0] + 6.5, PIV[1] - 17.1, PIV[1] + 6.4, ZI - 0.1, ZO_SERVO + 0.1)
    for dy in (-13.9, 13.9):
        body = body - cyl_z((PIV[0], PIV[1] - 5.35 + dy), 0.85, ZI + 1.5, ZO_SERVO + 0.1, 24)
    # pin side: clearance V-seat for the M3 (pressed down and back)
    body = body - prism(v_seat(PIV, 1.95, 1.5, -70.0), -ZO_PIN - 0.1, -ZI + 0.1)
    for sx, sz in STUDS:
        body = body - g.keyhole_cut((sx + SLIDE, sz), (sx, sz))
    return body


def servo_solid():
    """MG90S as fitted: tabs on the outside of the thick upright, shaft inward"""
    s = box3(PIV[0] - 6.1, PIV[0] + 6.1, PIV[1] - 16.6, PIV[1] + 5.9, ZO_SERVO - 4.3, ZO_SERVO + 2.5 + 15.9)
    s = s + box3(PIV[0] - 6.1, PIV[0] + 6.1, PIV[1] - 21.3, PIV[1] + 10.6, ZO_SERVO, ZO_SERVO + 2.5)
    s = s + cyl_z(PIV, 5.9, ZO_SERVO - 8.3, ZO_SERVO - 4.2) + cyl_z((PIV[0], PIV[1] - 6.5), 3.0, ZO_SERVO - 8.3, ZO_SERVO - 4.2, 24)
    return s + cyl_z(PIV, 2.4, ZO_SERVO - 11.5, ZO_SERVO - 8.2, 24)


def horn_solid():
    tip = PIV + 15.0 * np.array([math.cos(ARM_DIR), math.sin(ARM_DIR)])
    arm = LineString([tuple(PIV), tuple(tip)]).buffer(2.5, 16)
    return prism(arm, ZP - 4.4, ZP - 2.8) + cyl_z(PIV, 3.5, ZP - 4.4, ZP - 0.2, 32)


def fruit(d):
    """an avocado d mm across lying in the corner: centre (x, y), mass in kg (an ellipsoid 1.4 d long)"""
    c = V0 + d / 2 * (U_F + U_W)
    return c, math.pi / 6 * d * d * 1.4 * d * 1e-6


def fruit_mesh(d):
    m = trimesh.creation.icosphere(subdivisions=3, radius=1.0)
    c, _ = fruit(d)
    m.apply_scale([d / 2, d / 2, min(0.7 * d, HC - 2.0)])
    m.apply_translation([c[0], c[1], 0])
    return m


# ---------------------------------------------------------------- print orientation
def to_print(t, kind):
    m = t.copy()
    v = m.vertices.copy()
    if kind == "frame":                     # as it stands, sole on the bed
        m.vertices = np.column_stack([v[:, 0], -v[:, 2], v[:, 1]])
    else:                                   # cradle: lying on the back of its wall
        ez = -np.array([N_W[0], N_W[1], 0.0])
        ey = np.array([0.0, 0.0, 1.0])
        ex = np.cross(ey, ez)
        m.vertices = v @ np.vstack([ex, ey, ez]).T
    if np.linalg.det(np.eye(3)) < 0 or m.volume < 0:
        m.invert()
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    return m


def bed_area(p):
    z0 = p.bounds[0][2]
    return p.area_faces[(p.face_normals[:, 2] < -0.99) & (np.abs(p.triangles_center[:, 2] - z0) < 0.02)].sum()


# ---------------------------------------------------------------- checks
def checks(frame, cradle):
    ok = True

    def rep(name, v, lim=0.05):
        nonlocal ok
        good = v <= lim
        ok &= good
        print(f"  {'ok ' if good else 'BAD'} {name}: {v:.3f} mm3")

    def flag(good, text):
        nonlocal ok
        ok &= bool(good)
        print(f"  {'ok ' if good else 'BAD'} {text}")

    print("fit checks (+z build; base, sled and blade mirrored to match)")
    base_m = mirror_z(g.build_base())
    rep("frame vs base", vol(frame ^ base_m), 0.5)
    rep("frame vs base while being dropped on (9 mm toward the pad)", vol(frame.translate([-SLIDE, 0, 0]) ^ base_m), 0.5)
    srv, horn = servo_solid(), horn_solid()
    rep("servo vs frame", vol(srv ^ frame), 0.5)
    rep("servo vs base", vol(srv ^ base_m))
    rep("horn vs cradle (in its pocket)", vol(horn ^ cradle))
    rep("cradle vs frame at rest (it touches the two stops)", vol(cradle ^ frame), 0.3)

    def flipped(mesh):
        return M(trimesh.Trimesh(mesh.vertices, mesh.faces[:, ::-1], process=False))
    sled = trimesh.load(STL / "v45" / "v45-sled.stl", force="mesh")
    s = sled.vertices.copy()
    blade = trimesh.load(STL / "v45" / "v45-blade.stl", force="mesh")
    bl = blade.vertices.copy()
    home = None
    for travel in (0.0, MAX_TRAVEL):
        sled.vertices = np.column_stack([s[:, 2] - 22.0 + travel, s[:, 1] + 36.5, s[:, 0]])
        blade.vertices = np.column_stack([bl[:, 2] + 2.1 + travel, bl[:, 1] + 43.5, bl[:, 0]])
        pad = trimesh.creation.cylinder(radius=8.0, height=11.4, sections=48)
        pad.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
        pad.apply_translation([28.0 + travel - 5.7, PAD_Y, 0.0])
        moving = flipped(sled) + flipped(blade) + M(pad)
        rep(f"frame and cradle vs sled, blade and pad at travel {travel:.0f}", vol(frame ^ moving) + vol(cradle ^ moving))
        if travel == 0:
            home = moving
        else:
            pts = sled.sample(3000)
            gc = -trimesh.proximity.signed_distance(T(cradle), pts).max()
            gf = -trimesh.proximity.signed_distance(T(frame), pts).max()
            flag(gc >= 1.9 and gf >= 1.9, f"closest the sled gets at max travel {MAX_TRAVEL:.0f}: {gc:.1f} mm to the cradle, {gf:.1f} mm to the frame")
    worst = dict.fromkeys(["cradle vs frame", "cradle vs base", "cradle vs servo", "cradle vs sled, blade and pad (at home)"], 0.0)
    low, back = 1e9, -1e9
    for deg in np.arange(1.0, TIP + 5.01, 2.0):         # 5 degrees past the tip angle as margin
        c = rot_cw(cradle, deg)
        worst["cradle vs frame"] = max(worst["cradle vs frame"], vol(c ^ frame))
        worst["cradle vs base"] = max(worst["cradle vs base"], vol(c ^ base_m))
        worst["cradle vs servo"] = max(worst["cradle vs servo"], vol(c ^ srv))
        worst["cradle vs sled, blade and pad (at home)"] = max(worst["cradle vs sled, blade and pad (at home)"], vol(c ^ home))
        tm = T(c)
        low, back = min(low, tm.bounds[0][1]), max(back, tm.bounds[1][0])
    for k, v in worst.items():
        rep(f"{k}, whole swing (worst)", v, 0.3)
    flag(low >= SOLE_TOP + 1.5, f"lowest the cradle swings: {low - SOLE_TOP:.1f} mm above the sole plate")
    print(f"       it swings {back - 109.5:.0f} mm out past the back of the base: keep that space (and the ramp) clear")
    for name, part in (("frame", frame), ("cradle", cradle)):
        n = len(T(part).split(only_watertight=False))
        flag(n == 1 and T(part).is_watertight, f"{name} is one watertight piece ({n})")

    print("balance and servo load (pivot at x %.0f, y %.0f; the stops resist turning toward the pad)" % tuple(PIV))
    tc = T(cradle)
    cm = tc.volume * 1e-3 * 1.24 * 0.45 * 1e-3          # kg: PLA at about 45 % of solid (walls + 15 % infill)
    cc = tc.center_mass[:2]
    flag(cc[0] < PIV[0] - 1.0, f"empty cradle ({cm * 1000:.0f} g): its weight is {PIV[0] - cc[0]:.1f} mm in front of the pivot, so it rests on the stops")
    STALL = 176.0                                       # MG90S at 4.8 V, N mm (1.8 kg cm)
    for d in (45, 55, 70, 80):
        fc, fm = fruit(d)
        rest = 9.81 * (cm * (PIV[0] - cc[0]) + fm * (PIV[0] - fc[0]))             # N mm holding it on the stops
        peak = 0.0
        for deg in np.arange(0.0, 91.0, 2.0):           # the avocado stays in the corner until the wall is level
            tq = 9.81 * (cm * (PIV[0] - rot_pt(cc, deg)[0]) + fm * (PIV[0] - rot_pt(fc, deg)[0]))
            peak = max(peak, tq)
        press = 2.5 * (PIV[1] - PAD_Y)                   # N mm, same direction
        flag(rest > 0 and peak < 0.6 * STALL, f"{d} mm avocado ({fm * 1000:.0f} g): {rest:.0f} N mm holds it on the stops (+{press:.0f} from a full press); "
             f"the servo needs {peak:.0f} N mm to tip it ({100 * peak / STALL:.0f} % of an MG90S)")
    w_end = rot_pt(W1, TIP)
    slope = math.degrees(math.atan2(*(rot_pt(V0, TIP) - w_end)[::-1]))
    slope = 180 - slope if slope > 90 else slope
    print(f"  tipped {TIP:.0f} deg: the wall slopes {abs(slope):.0f} deg down toward the back and ends at x {w_end[0]:.0f}, y {w_end[1]:.0f} "
          f"({w_end[0] - 109.5:+.0f} mm from the base's back edge, {w_end[1]:.0f} mm above the table)")
    flag(15 <= abs(slope) <= 30, "that is steep enough to roll and gentle enough not to throw")

    print(f"where the pad meets each size (pad tip is at x 28 at home, {28 + MAX_TRAVEL:.0f} at max travel {MAX_TRAVEL:.0f})")
    for d in (45, 50, 55, 60, 65, 70, 75, 80):
        r = d / 2
        c, _ = fruit(d)
        dy = PAD_Y - c[1]
        x = c[0] - math.sqrt(r * r - dy * dy)
        flag(28.0 + 2.0 <= x <= 28.0 + MAX_TRAVEL - 1.0, f"{d} mm: travel {x - 28.0:4.1f} of {MAX_TRAVEL:.0f}, pad {abs(dy):4.1f} mm {'above' if dy > 0 else 'below'} the middle")
    return ok


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = pathlib.Path(args[0]) if args else STL
    out.mkdir(parents=True, exist_ok=True)
    frame, cradle = build_frame(), build_cradle()
    ok = checks(frame, cradle)
    for name, part in (("frame", frame), ("cradle", cradle)):
        t = T(mirror_z(part))                       # servo to the board side
        if "--model" in sys.argv:
            t.export(out / f"tip-{name}-model.stl")
        p = to_print(t, name)
        area = bed_area(p)
        print(f"tip-{name}.stl: {np.round(p.extents, 1)} mm, {t.volume / 1000:.0f} cm3 solid, {area:.0f} mm2 on the bed")
        ok &= area > 300
        p.export(out / f"tip-{name}.stl")
    if "--model" in sys.argv:
        T(mirror_z(servo_solid())).export(out / "tip-servo-model.stl")
        T(mirror_z(horn_solid())).export(out / "tip-horn-model.stl")
    if not ok:
        sys.exit("a check failed")


if __name__ == "__main__":
    main()
