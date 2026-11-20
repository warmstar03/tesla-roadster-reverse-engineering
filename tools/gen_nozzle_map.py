#!/usr/bin/env python3
"""Generate a Matrix-style isometric exploded view of the Roadster thruster layout.

Concept drawing only: positions are schematic, based on public reporting.
Usage: python3 gen_nozzle_map.py <out.svg>
"""
import math
import random
import sys

W, H = 1600, 1180
S = 158                      # px per metre
OX, OY = 800, 640            # screen origin of car centre at ground level
C30, S30 = math.cos(math.radians(30)), math.sin(math.radians(30))
BODY_DZ = 2.45               # exploded lift of the body shell (m)

G_BRIGHT = "#00ff41"
G_MID = "#00c832"
G_DIM = "#008f11"
G_DARK = "#0a3d14"
G_HOT = "#d7ffd9"

MONO = "'DejaVu Sans Mono','Noto Sans Mono CJK KR','Noto Sans CJK KR',monospace"
SANS = "'DejaVu Sans','Helvetica Neue',Arial,sans-serif"


BBOX = []


def P(x, y, z):
    """Car frame (x fwd, y right, z up, metres) -> screen."""
    pt = (OX - x * S * C30 + y * S * C30, OY + x * S * S30 + y * S * S30 - z * S)
    BBOX.append(pt)
    return pt


def fmt(pt):
    return f"{pt[0]:.1f},{pt[1]:.1f}"


def poly(pts3, close=False, **attr):
    pts = [P(*p) for p in pts3]
    d = "M" + " L".join(fmt(p) for p in pts) + (" Z" if close else "")
    a = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attr.items())
    return f'<path d="{d}" {a}/>'


def interp(x, table):
    for (x0, v0), (x1, v1) in zip(table, table[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return v0 + (v1 - v0) * t
    return table[0][1] if x < table[0][0] else table[-1][1]


def ortho(d):
    dx, dy, dz = d
    n = math.sqrt(dx * dx + dy * dy + dz * dz)
    d = (dx / n, dy / n, dz / n)
    ref = (0, 0, 1) if abs(d[2]) < 0.9 else (1, 0, 0)
    u = (d[1] * ref[2] - d[2] * ref[1], d[2] * ref[0] - d[0] * ref[2], d[0] * ref[1] - d[1] * ref[0])
    un = math.sqrt(sum(c * c for c in u))
    u = tuple(c / un for c in u)
    v = (d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0])
    return d, u, v


def ring(c, d, r, n=36):
    d, u, v = ortho(d)
    return [tuple(c[i] + r * (math.cos(t) * u[i] + math.sin(t) * v[i]) for i in range(3))
            for t in (2 * math.pi * k / n for k in range(n))]



def render(geometry_only=False):
    global ch, cadd, plumes
    out = []
    add = out.append

    # ------------------------------------------------------------------ defs
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
    add('''<defs>
    <radialGradient id="bg" cx="50%" cy="50%" r="75%">
      <stop offset="0%" stop-color="#03140a"/><stop offset="60%" stop-color="#010805"/><stop offset="100%" stop-color="#000000"/>
    </radialGradient>
    <radialGradient id="veil" cx="50%" cy="55%" r="50%">
      <stop offset="0%" stop-color="#000" stop-opacity="0.92"/><stop offset="70%" stop-color="#000" stop-opacity="0.55"/><stop offset="100%" stop-color="#000" stop-opacity="0"/>
    </radialGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2.2" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glow2" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="1" fill="#000" fill-opacity="0.35"/>
    </pattern>
    </defs>''')
    add(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')

    # ------------------------------------------------------------------ digital rain
    random.seed(7)
    glyphs = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜ0123456789Z:.=*+-"
    add(f'<g font-family="{MONO}" font-size="17" opacity="0.55">')
    for col in range(0, W, 23):
        for _ in range(random.randint(1, 2)):
            head = random.randint(-200, H + 100)
            length = random.randint(6, 26)
            for k in range(length):
                y = head - k * 20
                if y < -20 or y > H + 20:
                    continue
                ch = random.choice(glyphs)
                if k == 0:
                    add(f'<text x="{col}" y="{y}" fill="{G_HOT}" fill-opacity="0.85">{ch}</text>')
                else:
                    op = max(0.06, 0.7 * (1 - k / length))
                    add(f'<text x="{col}" y="{y}" fill="{G_BRIGHT}" fill-opacity="{op:.2f}">{ch}</text>')
    add('</g>')
    add(f'<rect width="{W}" height="{H}" fill="url(#veil)"/>')

    # ------------------------------------------------------------------ ground grid
    add(f'<g stroke="{G_DARK}" stroke-width="1" fill="none">')
    for gx in [i * 0.5 for i in range(-7, 8)]:
        add(poly([(gx, -2.4, 0), (gx, 2.4, 0)]))
    for gy in [i * 0.5 for i in range(-5, 6)]:
        add(poly([(-3.5, gy, 0), (3.5, gy, 0)]))
    add('</g>')
    BBOX.clear()

    # ------------------------------------------------------------------ body shell (raised)
    def body_ring(x):
        w = 0.95 - 0.20 * max(0, (x - 1.4) / 0.8) ** 2 - 0.08 * max(0, (-x - 1.6) / 0.6) ** 2
        z0 = 0.16 + 0.16 * max(0, (x - 1.7) / 0.5) + 0.12 * max(0, (-x - 1.8) / 0.4)
        z1 = interp(x, [(-2.2, 0.78), (-1.6, 0.82), (0, 0.74), (1.4, 0.68), (2.2, 0.50)])
        d = interp(x, [(-2.2, 0.82), (-1.8, 0.92), (-1.0, 1.04), (-0.4, 1.17), (0.2, 1.15),
                       (0.6, 0.95), (0.9, 0.80), (1.6, 0.73), (2.2, 0.56)])
        dw = interp(x, [(-2.2, 0.70), (-1.4, 0.68), (-0.8, 0.52), (0.4, 0.52), (0.8, 0.66), (2.2, 0.60)])
        dz = BODY_DZ
        return [(x, -w, z0 + dz), (x, -w, z1 + dz), (x, -dw, d + dz), (x, 0, d + 0.02 + dz),
                (x, dw, d + dz), (x, w, z1 + dz), (x, w, z0 + dz)]


    stations = [-2.2 + 0.2 * i for i in range(23)]
    rings = [body_ring(x) for x in stations]
    add(f'<g fill="none" stroke-linejoin="round" filter="url(#glow)">')
    for i, rg in enumerate(rings):
        add(poly(rg, close=True, stroke=G_DIM, stroke_width="1", stroke_opacity="0.55" if i % 2 else "0.9"))
    for k in range(7):
        add(poly([rg[k] for rg in rings], stroke=G_MID, stroke_width="1.6"))
    # glasshouse outline
    glass = [r for r, x in zip(rings, stations) if -0.5 <= x <= 0.8]
    add(poly([g[2] for g in glass] + [g[4] for g in reversed(glass)], close=True,
             stroke=G_BRIGHT, stroke_width="1.4", fill=G_BRIGHT, fill_opacity="0.05"))
    # nose & tail caps
    add(poly(rings[0], close=True, stroke=G_BRIGHT, stroke_width="1.8"))
    add(poly(rings[-1], close=True, stroke=G_BRIGHT, stroke_width="1.8"))
    add('</g>')

    # exploded-view guide lines body -> chassis
    add(f'<g stroke="{G_DIM}" stroke-width="1" stroke-dasharray="3 6" opacity="0.8">')
    for (x, y) in [(2.1, -0.85), (2.1, 0.85), (-2.15, -0.85), (-2.15, 0.85)]:
        add(poly([(x, y, 0.2), (x, y, BODY_DZ + 0.16)]))
    add('</g>')

    # ------------------------------------------------------------------ chassis layer
    ch = []
    cadd = ch.append

    # frame rails + skirts
    cadd(poly([(-2.0, -0.78, 0.22), (2.0, -0.78, 0.22)], stroke=G_MID, stroke_width="1.6"))
    cadd(poly([(-2.0, 0.78, 0.22), (2.0, 0.78, 0.22)], stroke=G_MID, stroke_width="1.6"))
    for x in (-2.0, -1.35, 0, 1.35, 2.0):
        cadd(poly([(x, -0.78, 0.22), (x, 0.78, 0.22)], stroke=G_DIM, stroke_width="1.2"))
    for y in (-0.95, 0.95):
        cadd(poly([(-1.6, y, 0.03), (1.6, y, 0.03), (1.6, y, 0.17), (-1.6, y, 0.17)], close=True,
                  stroke=G_BRIGHT, stroke_width="1.2", stroke_dasharray="6 4", fill=G_BRIGHT, fill_opacity="0.06"))

    # battery pack (box with cell grid)
    bx0, bx1, by0, by1, bz0, bz1 = -1.15, 1.15, -0.68, 0.68, 0.10, 0.24
    for z in (bz0, bz1):
        cadd(poly([(bx0, by0, z), (bx1, by0, z), (bx1, by1, z), (bx0, by1, z)], close=True,
                  stroke=G_MID, stroke_width="1.4", fill=G_BRIGHT, fill_opacity="0.04"))
    for (x, y) in [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)]:
        cadd(poly([(x, y, bz0), (x, y, bz1)], stroke=G_MID, stroke_width="1.2"))
    for i in range(1, 12):
        x = bx0 + (bx1 - bx0) * i / 12
        cadd(poly([(x, by0, bz1), (x, by1, bz1)], stroke=G_DIM, stroke_width="0.7"))
    for i in range(1, 6):
        y = by0 + (by1 - by0) * i / 6
        cadd(poly([(bx0, y, bz1), (bx1, y, bz1)], stroke=G_DIM, stroke_width="0.7"))

    # underbody fans (horizontal discs)
    FANS = [(1.62, -0.42), (1.62, 0.42), (-1.55, -0.42), (-1.55, 0.42)]
    for (fx, fy) in FANS:
        cadd(poly(ring((fx, fy, 0.08), (0, 0, 1), 0.22, 40), close=True, stroke=G_BRIGHT, stroke_width="1.6",
                  fill=G_BRIGHT, fill_opacity="0.07"))
        cadd(poly(ring((fx, fy, 0.08), (0, 0, 1), 0.07, 20), close=True, stroke=G_BRIGHT, stroke_width="1.2"))
        for k in range(6):
            t = k * math.pi / 3
            cadd(poly([(fx + 0.07 * math.cos(t), fy + 0.07 * math.sin(t), 0.08),
                       (fx + 0.2 * math.cos(t + 0.5), fy + 0.2 * math.sin(t + 0.5), 0.08)],
                      stroke=G_MID, stroke_width="1"))

    # wheels
    def wheel(xc, ys, r=0.36):
        zc = r
        yo, yi = ys, ys * 0.76
        faces = []
        for y in (yo, yi):
            pts = [(xc + r * math.cos(t), y, zc + r * math.sin(t)) for t in (2 * math.pi * k / 48 for k in range(48))]
            faces.append(pts)
            cadd(poly(pts, close=True, stroke=G_MID, stroke_width="1.6" if y == yo else "1"))
        rim = [(xc + 0.6 * r * math.cos(t), yo, zc + 0.6 * r * math.sin(t)) for t in (2 * math.pi * k / 40 for k in range(40))]
        cadd(poly(rim, close=True, stroke=G_BRIGHT, stroke_width="1.2"))
        for k in range(10):
            t = k * math.pi / 5
            cadd(poly([(xc + 0.12 * r * math.cos(t), yo, zc + 0.12 * r * math.sin(t)),
                       (xc + 0.58 * r * math.cos(t + 0.15), yo, zc + 0.58 * r * math.sin(t + 0.15))],
                      stroke=G_DIM, stroke_width="1"))
        for k in range(0, 48, 6):
            cadd(poly([faces[0][k], faces[1][k]], stroke=G_DIM, stroke_width="0.8"))


    for xc in (1.35, -1.35):
        for ys in (-1.0, 1.0):
            wheel(xc, ys)
        cadd(poly([(xc, -0.76, 0.36), (xc, 0.76, 0.36)], stroke=G_DIM, stroke_width="1.4"))

    # driver seat (ghost)
    seat = dict(stroke=G_DIM, stroke_width="1", stroke_opacity="0.8")
    cadd(poly([(-0.25, -0.6, 0.32), (0.35, -0.6, 0.32), (0.35, -0.15, 0.32), (-0.25, -0.15, 0.32)], close=True, **seat))
    cadd(poly([(-0.25, -0.6, 0.32), (-0.45, -0.6, 0.95), (-0.45, -0.15, 0.95), (-0.25, -0.15, 0.32)], close=True, **seat))


    def capsule(a, b, r, n_rings=7):
        d = tuple(b[i] - a[i] for i in range(3))
        rs = []
        for k in range(n_rings):
            t = k / (n_rings - 1)
            c = tuple(a[i] + d[i] * t for i in range(3))
            rg = ring(c, d, r, 40)
            rs.append(rg)
            cadd(poly(rg, close=True, stroke=G_BRIGHT if k in (0, n_rings - 1) else G_MID,
                      stroke_width="1.4" if k in (0, n_rings - 1) else "0.9", fill=G_BRIGHT, fill_opacity="0.03"))
        for j in range(0, 40, 5):
            cadd(poly([rg[j] for rg in rs], stroke=G_MID, stroke_width="0.9"))
        # dome ends
        dd, u, v = ortho(d)
        for end, sgn in ((a, -1), (b, 1)):
            for j in range(0, 40, 10):
                t = 2 * math.pi * j / 40
                arc = []
                for m in range(9):
                    ph = (math.pi / 2) * m / 8
                    arc.append(tuple(end[i] + r * math.cos(ph) * (math.cos(t) * u[i] + math.sin(t) * v[i])
                                     + sgn * r * math.sin(ph) * dd[i] for i in range(3)))
                cadd(poly(arc, stroke=G_MID, stroke_width="0.9"))


    TANK400 = ((-0.45, 0.38, 0.62), (0.40, 0.38, 0.62), 0.27)
    TANK200 = ((-1.05, -0.55, 0.55), (-1.05, 0.55, 0.55), 0.21)
    capsule(*TANK400)
    capsule(*TANK200)

    # valve blocks
    def box(c, s):
        x, y, z = c
        a, b, h = s
        pts = [(x + i * a, y + j * b, z + k * h) for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)]
        edges = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
        for e in edges:
            cadd(poly([pts[e[0]], pts[e[1]]], stroke=G_BRIGHT, stroke_width="1.4"))


    VALVE_R = (-1.55, 0.0, 0.48)
    VALVE_F = (1.62, 0.0, 0.48)
    box(VALVE_R, (0.12, 0.16, 0.08))
    box(VALVE_F, (0.10, 0.14, 0.07))

    # nozzles + plumes
    REAR = [(-2.22, y, 0.44) for y in (-0.45, -0.15, 0.15, 0.45)]
    CORNER = [(1.88, -0.74, 0.34), (1.88, 0.74, 0.34), (-1.92, -0.74, 0.34), (-1.92, 0.74, 0.34)]
    YAW = [((1.98, -0.86, 0.46), (0, -1, 0)), ((1.98, 0.86, 0.46), (0, 1, 0))]

    plumes = []


    def nozzle(p, d, plume_len, spread):
        dd, u, v = ortho(d)
        exit_c = tuple(p[i] + dd[i] * 0.16 for i in range(3))
        th = ring(p, d, 0.035, 18)
        ex = ring(exit_c, d, 0.075, 24)
        cadd(poly(th, close=True, stroke=G_HOT, stroke_width="1.2"))
        cadd(poly(ex, close=True, stroke=G_HOT, stroke_width="1.6", fill=G_BRIGHT, fill_opacity="0.25"))
        for j in range(0, 24, 4):
            cadd(poly([th[(j * 18) // 24], ex[j]], stroke=G_HOT, stroke_width="1"))
        end_c = tuple(exit_c[i] + dd[i] * plume_len for i in range(3))
        for j in range(0, 24, 2):
            t = 2 * math.pi * j / 24
            e = tuple(end_c[i] + spread * (math.cos(t) * u[i] + math.sin(t) * v[i]) for i in range(3))
            plumes.append(poly([ex[j], e], stroke=G_BRIGHT, stroke_width="1.1", stroke_opacity="0.55"))
        for f, rr in ((0.35, 0.45), (0.7, 0.75)):
            c = tuple(exit_c[i] + dd[i] * plume_len * f for i in range(3))
            plumes.append(poly(ring(c, d, 0.075 + (spread - 0.075) * rr, 30), close=True,
                               stroke=G_BRIGHT, stroke_width="0.9", stroke_opacity="0.45"))
        plumes.append(poly(ring(end_c, d, spread, 36), close=True, stroke=G_BRIGHT, stroke_width="1", stroke_opacity="0.3"))
        # core jet
        plumes.append(poly([exit_c, end_c], stroke=G_HOT, stroke_width="3", stroke_opacity="0.75"))
        return exit_c


    for p in REAR:
        nozzle(p, (-1, 0, 0), 0.72, 0.21)
    for p in CORNER:
        nozzle(p, (0, 0, -1), 0.17, 0.13)
        # ground splash rings
        for rr, op in ((0.18, 0.7), (0.3, 0.45), (0.44, 0.25)):
            plumes.append(poly(ring((p[0], p[1], 0.0), (0, 0, 1), rr, 36), close=True,
                               stroke=G_BRIGHT, stroke_width="1", stroke_opacity=str(op)))
    for p, d in YAW:
        nozzle(p, d, 0.48, 0.16)

    # plumbing (tank -> valve -> nozzles), right-angle runs
    pipe = dict(stroke=G_BRIGHT, stroke_width="1.1", stroke_dasharray="5 4", stroke_opacity="0.85", fill="none")
    cadd(poly([(TANK400[0][0], 0.38, 0.40), (-1.2, 0.38, 0.40), (-1.2, 0.0, 0.40), (VALVE_R[0] + 0.12, 0, 0.48)], **pipe))
    cadd(poly([(-1.05, 0.0, 0.34), (-1.05, 0.0, 0.40), (-1.43, 0.0, 0.40)], **pipe))
    for p in REAR:
        cadd(poly([(VALVE_R[0] - 0.12, 0, 0.48), (-2.0, 0, 0.48), (-2.0, p[1], 0.48), (p[0], p[1], p[2])], **pipe))
    for p in CORNER[2:]:
        cadd(poly([(VALVE_R[0], 0, 0.40), (VALVE_R[0], p[1], 0.40), (p[0], p[1], 0.40), (p[0], p[1], p[2])], **pipe))
    cadd(poly([(TANK400[1][0], 0.38, 0.40), (1.2, 0.38, 0.40), (1.2, 0.0, 0.40), (VALVE_F[0] - 0.10, 0, 0.48)], **pipe))
    for p in CORNER[:2]:
        cadd(poly([(VALVE_F[0], 0, 0.41), (VALVE_F[0], p[1], 0.41), (p[0], p[1], 0.41), (p[0], p[1], p[2])], **pipe))
    for p, d in YAW:
        cadd(poly([(VALVE_F[0] + 0.10, 0, 0.48), (1.98, 0, 0.48), (1.98, p[1] - d[1] * 0.02, 0.48), p], **pipe))

    add(f'<g fill="none" stroke-linejoin="round" stroke-linecap="round" filter="url(#glow2)">')
    out.extend(plumes)
    add('</g>')
    add(f'<g fill="none" stroke-linejoin="round" stroke-linecap="round" filter="url(#glow)">')
    out.extend(ch)
    add('</g>')

    # ------------------------------------------------------------------ callouts
    LX_L, LX_R = 64, 1236


    def callout(anchor3, side, ly, title, sub, tag):
        ax, ay = P(*anchor3)
        lx = LX_L + 300 if side == "L" else LX_R - 16
        tx = LX_L if side == "L" else LX_R
        add(f'<g filter="url(#glow)">')
        add(f'<path d="M{ax:.1f},{ay:.1f} L{ax:.1f},{ly:.1f} L{lx:.1f},{ly:.1f}" fill="none" stroke="{G_BRIGHT}" stroke-width="1.2" stroke-opacity="0.9"/>')
        add(f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="5" fill="#000" stroke="{G_HOT}" stroke-width="2"/>')
        add(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3.5" fill="{G_BRIGHT}"/>')
        add('</g>')
        add(f'<text x="{tx}" y="{ly - 8:.1f}" font-family="{MONO}" font-size="19" font-weight="bold" fill="{G_BRIGHT}" filter="url(#glow)">'
            f'<tspan fill="{G_DIM}">{tag} </tspan>{title}</text>')
        add(f'<text x="{tx}" y="{ly + 18:.1f}" font-family="{SANS}" font-size="16" fill="{G_HOT}" fill-opacity="0.85">{sub}</text>')


    # left column: front of car (lower-left of drawing)
    callout(YAW[0][0], "L", 590, "FRONT YAW NOZZLE ×2", "Side-firing pair → yaw rotation", "[01]")
    callout(CORNER[0], "L", 700, "CORNER LIFT NOZZLE ×4", "Downward jets → lift, roll, pitch", "[02]")
    callout((1.62, -0.64, 0.08), "L", 810, "UNDERBODY FAN ×4", "Ducted fans · ~80 kW · suction", "[03]")
    callout((0.6, -0.95, 0.12), "L", 920, "SKIRT SEAL", "Movable skirts · ~6 mm gap (est.)", "[04]")
    callout((0.2, 0.68, 0.24), "L", 1030, "4680 BATTERY PACK", "800–1000 V · powers the fans", "[05]")

    # right column: rear of car (upper-right of drawing)
    callout((-1.2, 0.7, BODY_DZ + 0.82), "R", 250, "BODY SHELL", "Carbon fiber · magnesium · titanium", "[06]")
    callout((0.0, 0.65, 0.62), "R", 520, "AIR TANK 400 L", "Replaces passenger seat · 690 bar", "[07]")
    callout((-1.05, 0.76, 0.55), "R", 630, "AIR TANK 200 L", "Thrust-trim tank · position estimated", "[08]")
    callout((-1.55, 0.16, 0.56), "R", 740, "VALVE BLOCK", "Regulator + fast valves (estimated)", "[09]")
    callout((-2.30, 0.45, 0.44), "R", 850, "REAR THRUST NOZZLE ×4", "80 kN combined · 0→60 mph boost", "[10]")

    # ------------------------------------------------------------------ header / HUD
    add(f'<g font-family="{MONO}" filter="url(#glow)">')
    add(f'<text x="64" y="86" font-size="40" font-weight="bold" fill="{G_BRIGHT}" letter-spacing="2">ROADSTER_SYS // THRUST NOZZLE MAP</text>')
    add(f'<text x="64" y="122" font-size="17" fill="{G_MID}">&gt; exploded_view.render --mode=wireframe --layer=body,chassis --trim=ROCKET</text>')
    add('</g>')
    add(f'<text x="64" y="156" font-family="{SANS}" font-size="18" fill="{G_HOT}" fill-opacity="0.85">'
        'Rocket-trim thruster layout · conceptual 3D exploded view · estimated from public reporting, not an official drawing</text>')

    # legend box
    lx, ly = 1236, 960
    add(f'<g font-family="{MONO}" font-size="15">')
    add(f'<rect x="{lx - 16}" y="{ly - 30}" width="350" height="186" fill="#000" fill-opacity="0.6" stroke="{G_DIM}" stroke-width="1"/>')
    add(f'<text x="{lx}" y="{ly}" fill="{G_BRIGHT}" font-weight="bold">// SPEC_DUMP</text>')
    rows = [("THRUST REAR", "80 kN (reported)"), ("AIR STORE", "690 bar · 200+400 L"),
            ("LIFT REQ", "&gt; m·g ≈ 16.7 kN"), ("HOVER t", "≈ 3.5–11 s (theory)"),
            ("FAN DRAW", "4 × ~20 kW"), ("SUCTION", "ΔP ≈ 7–9 kPa")]
    for i, (k, v) in enumerate(rows):
        y = ly + 26 + i * 22
        add(f'<text x="{lx}" y="{y}" fill="{G_DIM}">{k}</text>')
        add(f'<text x="{lx + 130}" y="{y}" fill="{G_HOT}" font-family="{SANS}">{v}</text>')
    add('</g>')

    # HUD corner brackets + footer
    br = 36
    for (cx, cy, sx, sy) in [(24, 24, 1, 1), (W - 24, 24, -1, 1), (24, H - 24, 1, -1), (W - 24, H - 24, -1, -1)]:
        add(f'<path d="M{cx},{cy + sy * br} L{cx},{cy} L{cx + sx * br},{cy}" fill="none" stroke="{G_BRIGHT}" stroke-width="2.5" filter="url(#glow)"/>')
    add(f'<text x="64" y="{H - 44}" font-family="{MONO}" font-size="14" fill="{G_DIM}">'
        'SCAN 0x7E9 · FRONT ◣ LOWER-LEFT · REAR ◥ UPPER-RIGHT · BODY LIFTED +2.45 m (EXPLODED) · NOT TO SCALE</text>')

    add(f'<rect width="{W}" height="{H}" fill="url(#scan)" pointer-events="none"/>')
    add('</svg>')

    return out


def fit():
    """Scale + place the car so its geometry fills the drawing area between the label columns."""
    global S, OX, OY
    BBOX.clear()
    render()
    # geometry points only: recorded before the callouts (anchors sit inside geometry anyway)
    xs = [p[0] for p in BBOX]
    ys = [p[1] for p in BBOX]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    tx0, tx1, ty0, ty1 = 405, 1195, 196, 1085
    k = min((tx1 - tx0) / (x1 - x0), (ty1 - ty0) / (y1 - y0))
    S *= k
    OX = (OX - x0) * k + tx0 + ((tx1 - tx0) - (x1 - x0) * k) / 2
    OY = (OY - y0) * k + ty0 + ((ty1 - ty0) - (y1 - y0) * k) / 2


fit()
out = render()
with open(sys.argv[1], "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("wrote", sys.argv[1])
