#!/usr/bin/env python3
"""Picture for fitting the servo horn: python3 tools/gate_horn_svg.py out.svg  (drawn from back_gate.py's geometry)"""
import sys, math, numpy as np
out = sys.argv[1]; sys.argv = sys.argv[:1]; sys.path.insert(0, "tools"); import back_gate as g
from shapely.geometry import Point
H, S = g.HINGE, g.SERVO
s = 4.8; X0, Y0 = 128.0, 66.0
RED, BLU, GRN, GRY, BRN = "#c0392b", "#1f6fb5", "#2a8a3a", "#555", "#7a5a30"
def mk(OX, OY):
    def px(p): return OX + (X0 - p[0]) * s, OY + (Y0 - p[1]) * s      # seen from the servo side
    return px
def path(px, poly, fill, stroke, op=1, sw=2, dash=""):
    d = ""
    for q in getattr(poly, "geoms", [poly]):
        for ring in [q.exterior] + list(q.interiors):
            d += "M" + " L".join("%.1f,%.1f" % px(c) for c in ring.coords) + "Z "
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" fill-opacity="{op}" {dash}/>'
def dot(px, c, r, fill, stroke="#222"): x, y = px(c); return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
def txt(x, y, t, col="#333", fs=14, w=400, a="start"): return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" font-weight="{w}" fill="{col}" text-anchor="{a}" paint-order="stroke" stroke="#fff" stroke-width="4" stroke-linejoin="round">{t}</text>'
def note(px, c, dx, dy, lines, col, a="start"):
    x, y = px(c); o = f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x+dx:.1f}" y2="{y+dy:.1f}" stroke="{col}" stroke-width="2"/>'
    for i, t in enumerate(lines): o += txt(x + dx + (6 if a == "start" else -6 if a == "end" else 0), y + dy + 5 + i * 17, t, col if i == 0 else "#333", 14 if i == 0 else 13, 700 if i == 0 else 400, a)
    return o
def scene(px, th, P, C, phi, horn=True, link_at=None, ghost_door=None):
    el = [f'<rect x="{px((X0,0))[0]:.1f}" y="{px((0,g.DECK))[1]:.1f}" width="{(X0-46)*s:.1f}" height="{5*s:.1f}" fill="#2f6b4a"/>',
          path(px, g.cheek_outline(), "#aab395", "#5d6648", 0.55)]
    if ghost_door is not None: el.append(path(px, g.door_profile(ghost_door), "none", "#c9773f", 1, 1.5, 'stroke-dasharray="6 5"'))
    el += [path(px, g.door_profile(th), "#e27c48", "#a3522a", 0.9), path(px, g.servo_case_profile(), "#3a3a3e", "#111"),
           path(px, g.lever_profile(th), "#e8c9a0", "#a8804f")]
    if horn: el.append(path(px, g.horn_profile(phi), "#ffffff", "#666"))
    else: el.append(dot(px, S, 9, "#cfd3d6", "#666"))
    Cl = C if link_at is None else link_at
    el += [path(px, Point(*g.lug_point(P, Cl)).buffer(g.LUG_R, 24), "#b58a55", BRN, 1, 1.5),
           path(px, g.link_profile(P, Cl).union(Point(*P).buffer(3.5)), "#d9b07a", BRN, 0.72),
           dot(px, H, 6, RED), dot(px, P, 6, BLU), dot(px, Cl, 4.5, GRN)]
    if horn: el.append(dot(px, S, 4, GRY))
    return el
th, P, C, phi = g.over_pose(math.radians(4)); mot = g.motion(40); tho, Po, Co, phio = mot[-1]
W, HH, PW = 1260, 600, 400
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {HH}" width="{W}" height="{HH}" font-family="system-ui,Segoe UI,sans-serif">',
       f'<rect width="{W}" height="{HH}" fill="#f7f6f1"/>',
       '<text x="24" y="36" font-size="22" font-weight="700" fill="#1d1d1b">Fitting the servo horn so the door shuts in the right place</text>',
       '<text x="24" y="58" font-size="14" fill="#555">Looking at the servo side of the holder. Red dot: hinge. Blue dot: link pivot on the lever. Green dot: link-to-horn screw.</text>']
heads = [("1  Park the servo, horn off", "Power on, tap Open the back gate once, let it finish.|The shaft now rests at the shut angle: don't turn it."),
         ("2  Hold the door shut, push the horn on", "Horn points straight away from the blue pivot,|its arm touching the bump under the link."),
         ("3  Test: Open the back gate", "The horn swings round and the door folds down,|then comes back to the pose in panel 2.")]
for i, (h1, h2) in enumerate(heads):
    x0 = 20 + i * (PW + 10)
    svg.append(f'<rect x="{x0}" y="76" width="{PW}" height="508" rx="12" fill="#fff" stroke="#d8d6cc"/>')
    svg.append(f'<text x="{x0+16}" y="104" font-size="17" font-weight="700" fill="#1d1d1b">{h1}</text>')
    for j, l in enumerate(h2.split("|")): svg.append(f'<text x="{x0+16}" y="{124+j*17}" font-size="13" fill="#555">{l}</text>')
    px = mk(x0 + 10, 190)
    svg.append(f'<clipPath id="c{i}"><rect x="{x0+2}" y="150" width="{PW-4}" height="430"/></clipPath><g clip-path="url(#c{i})">')
    if i == 0:
        hang = P + g.LINK * np.array([-0.83, 0.56])       # the link swung up out of the way
        svg += scene(px, th, P, C, phi, horn=False, link_at=hang)
        svg.append(note(px, S, -20, 86, ["bare shaft,", "parked at the shut angle"], GRY, "middle"))
        svg.append(note(px, P + (hang - P) * 0.6, -30, -70, ["link swung up,", "out of the way"], BRN, "middle"))
    elif i == 1:
        a, b = px(P + (P - S) / np.linalg.norm(P - S) * 6), px(S + (C - S) / np.linalg.norm(C - S) * 24)
        svg += scene(px, th, P, C, phi)
        svg.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{BLU}" stroke-width="2.5" stroke-dasharray="8 6"/>')
        svg.append(note(px, P + (S - P) * 0.3, 10, -150, ["one straight line:", "pivot, shaft, horn tip"], BLU, "middle"))
        svg.append(note(px, g.lug_point(P, C), 50, -84, ["arm rests", "on the bump"], BRN, "middle"))
        svg.append(note(px, C, -70, 76, ["horn hole under the", "link's small hole"], GRN, "middle"))
    else:
        svg += scene(px, tho, Po, Co, phio, ghost_door=th)
        svg.append(path(px, g.horn_profile(phi), "none", "#888", 1, 1.5, 'stroke-dasharray="5 4"'))
        r = g.CRANK + 6; pts = []
        for m_ in mot:
            pts.append(px(S + r * g.e(m_[3])))
        d = "M" + " L".join("%.1f,%.1f" % q for q in pts)
        (x1, y1), (x2, y2) = pts[-2], pts[-1]; ang = math.atan2(y2 - y1, x2 - x1)
        ah = " ".join("%.1f,%.1f" % (x2 + 12 * math.cos(ang + da), y2 + 12 * math.sin(ang + da)) for da in (0, 2.5, -2.5))
        svg.append(f'<path d="{d}" fill="none" stroke="{RED}" stroke-width="3"/><polygon points="{ah}" fill="{RED}"/>')
        v1 = np.array(pts[3]) - np.array(px(S)); v2 = np.array(pts[9]) - np.array(px(S))
        sense = "counter-clockwise" if (v1[0] * v2[1] - v1[1] * v2[0]) < 0 else "clockwise"      # screen y points down
        svg.append(note(px, S + r * g.e(mot[len(mot)//2][3]), -60, -150, ["opening turns the horn", sense + " from this side"], RED, "middle"))
        svg.append(note(px, H + np.array([-2, 14]), 40, 170, ["dashed: horn and door", "when shut"], "#a3522a", "middle"))
        print("opening sense as drawn:", sense, " sweep", round(g.SWEEP))
    svg.append('</g>')
svg.append('</svg>')
open(out, "w").write("\n".join(svg))
