import sys, math, numpy as np
out = sys.argv[1]; sys.argv = sys.argv[:1]; sys.path.insert(0, "tools"); import back_gate as g
from shapely.geometry import Point
from playwright.sync_api import sync_playwright
th, P, C, phi = g.over_pose(math.radians(4)); H, S = g.HINGE, g.SERVO
s = 7.0; X0, Y0 = 118.0, 60.0; OX, OY = 70, 150
def px(p): return OX + (X0 - p[0]) * s, OY + (Y0 - p[1]) * s      # seen from the servo side: +x is to the left
def path(poly, fill, stroke, op=1, sw=2):
    polys = getattr(poly, "geoms", [poly]); d = ""
    for q in polys:
        for ring in [q.exterior] + list(q.interiors):
            d += "M" + " L".join("%.1f,%.1f" % px(c) for c in ring.coords) + "Z "
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" fill-opacity="{op}" fill-rule="evenodd"/>'
def hole(c, r, col): x, y = px(c); return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r*s:.1f}" fill="#f7f6f1" stroke="{col}" stroke-width="2"/>'
def screw(c, r, col): x, y = px(c); k = r*s; return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{k:.1f}" fill="{col}" stroke="#222" stroke-width="1.5"/><path d="M{x-k*.6:.1f},{y:.1f} H{x+k*.6:.1f} M{x:.1f},{y-k*.6:.1f} V{y+k*.6:.1f}" stroke="#fff" stroke-width="2.5"/>'
def lab(c, dx, dy, lines, col, anchor="start"):
    x, y = px(c); tx, ty = x + dx, y + dy; o = f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" stroke="{col}" stroke-width="2"/>'
    for i, t in enumerate(lines):
        o += f'<text x="{tx + (8 if anchor=="start" else -8 if anchor=="end" else 0):.1f}" y="{ty + 5 + i*19 - (0 if dy >= 0 else (len(lines)-1)*19):.1f}" font-size="{16 if i==0 else 14}" font-weight="{700 if i==0 else 400}" fill="{col if i==0 else "#333"}" text-anchor="{anchor}" paint-order="stroke" stroke="#f7f6f1" stroke-width="5" stroke-linejoin="round">{t}</text>'
    return o
RED, BLU, GRN, GRY = "#c0392b", "#1f6fb5", "#2a8a3a", "#555"
cheek = g.cheek_outline(); lug = Point(*g.lug_point(P, C)).buffer(g.LUG_R, 24)
link = g.link_profile(P, C).union(Point(*P).buffer(3.5))
el = [f'<clipPath id="cp"><rect x="24" y="96" width="640" height="560"/></clipPath><g clip-path="url(#cp)">', f'<rect x="{OX-40}" y="{px((0,g.DECK))[1]:.1f}" width="600" height="{5*s}" fill="#2f6b4a"/>',
      path(cheek, "#8a9470", "#5d6648"), '</g>',
      path(g.servo_case_profile(), "#3a3a3e", "#111"),
      path(g.lever_profile(th), "#e8c9a0", "#a8804f"),
      path(g.horn_profile(phi), "#ffffff", "#888"),
      path(lug, "#b58a55", "#7a5a30", 1, 1.5),
      path(link, "#d9b07a", "#7a5a30", 0.78),
      screw(H, 2.7, RED), screw(P, 2.7, BLU), screw(C, 1.9, GRN), screw(S, 1.6, GRY)]
el += [lab(H, 0, 125, ["A  M3 × 30", "through the lever's big hole", "into the door"], RED, "middle"),
       lab(P, -60, -110, ["B  M3 × 16", "through the link's BIG hole", "into the lever's small hole"], BLU, "middle"),
       lab(C, 30, -190, ["C  M2 × 6 (or a small servo screw)", "through the link's small hole", "into the horn's hole"], GRN, "middle"),
       lab(S, 10, 135, ["D  Horn's own screw", "into the servo shaft"], GRY, "middle"),
       lab(g.lug_point(P, C), 150, 148, ["Bump on the link", "the horn's arm rests on it"], "#7a5a30", "middle"),
       lab((98, 74), 0, 0, ["Holder side wall"], "#2f3524", "middle")]
# right panel: the stack, seen from above
RX, RY, k = 740, 150, 15.0
def zx(z): return RX + (z - 56) * k
def bar(z0, z1, y0, y1, fill, stroke, txt=None, tcol="#222"):
    o = f'<rect x="{zx(z0):.1f}" y="{RY+y0}" width="{(z1-z0)*k:.1f}" height="{y1-y0}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    return o
yH, yP, yC, yS = 60, 150, 290, 380          # rows: hinge, lever pin, horn hole, servo shaft
st = [f'<text x="{RX}" y="{RY-44}" font-size="17" font-weight="700" fill="#1d1d1b">Seen from above: what sits on what</text>',
      f'<text x="{RX}" y="{RY-24}" font-size="13" fill="#555">wall, then lever, then horn, then link on the outside</text>',
      bar(56, 61, 20, 430, "#8a9470", "#5d6648"),
      bar(61, 67.8, yS-40, yS+40, "#3a3a3e", "#111"), bar(67.8, 73.2, yS-16, yS+16, "#77777c", "#111"),
      bar(61, 66.5, yH-14, yH+14, "#e8c9a0", "#a8804f"), bar(62.5, 66.5, yP-17, yP+17, "#e8c9a0", "#a8804f"),
      bar(66.5, 69.5, yH-26, yP+17, "#e8c9a0", "#a8804f"),
      bar(73.2, 74.7, yC-16, yS+18, "#ffffff", "#888"),
      bar(69.7, 75, yP-13, yP+13, "#d9b07a", "#7a5a30"), bar(75, 78, yP-14, yC+14, "#d9b07a", "#7a5a30"),
      bar(73.4, 75, yC-52, yC-40, "#b58a55", "#7a5a30")]
def scr(y, z_tip, z_head, col, letter):
    return (f'<rect x="{zx(z_tip):.1f}" y="{RY+y-4}" width="{(z_head-z_tip)*k:.1f}" height="8" fill="{col}"/>'
            f'<rect x="{zx(z_head):.1f}" y="{RY+y-10}" width="12" height="20" rx="3" fill="{col}"/>'
            f'<text x="{zx(z_head)+20:.1f}" y="{RY+y+6}" font-size="17" font-weight="700" fill="{col}">{letter}</text>')
st += [scr(yH, 57, 69.5, RED, "A"), scr(yP, 63, 78, BLU, "B"), scr(yC, 73.2, 78, GRN, "C"), scr(yS, 70, 74.7, GRY, "D")]
def t(z, y, txt, col="#222", a="middle", fs=13): return f'<text x="{zx(z):.1f}" y="{RY+y}" font-size="{fs}" fill="{col}" text-anchor="{a}">{txt}</text>'
st += [t(58.5, 448, "wall", "#3d4530"), t(64.4, yS+58, "servo", "#111"), t(68, yH-34, "lever", "#8a6535"), t(74, yS+36, "horn", "#555"),
       t(76.5, yC+32, "link", "#7a5a30"), t(72.3, yP-20, "spacer", "#7a5a30"), t(72.6, yC-58, "bump", "#7a5a30")]
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 680" width="1200" height="680" font-family="system-ui,Segoe UI,sans-serif">
<rect width="1200" height="680" fill="#f7f6f1"/>
<text x="24" y="36" font-size="22" font-weight="700" fill="#1d1d1b">Back gate linkage: four screws, door shut</text>
<text x="24" y="60" font-size="14" fill="#555">Looking at the servo side of the holder. Fit A, then B, then the horn with C and D. The link is drawn see-through: the horn lies under it.</text>
<line x1="690" y1="84" x2="690" y2="660" stroke="#d8d6cc" stroke-width="2"/>
{''.join(el)}{''.join(st)}</svg>'''
open(out, "w").write(svg)
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width":1200,"height":680}, device_scale_factor=2); pg.set_content(svg); pg.screenshot(path=out.replace(".svg", ".png")); b.close()
