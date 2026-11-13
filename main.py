#!/usr/bin/env python3
"""Steaming Ramen -- make.fun food-picture-01 entry.

Draws a single 1024x1024 PNG with nothing but the Python 3 standard
library (zlib for the PNG encoder). No files are read, no network is
touched, and a fixed seed makes the output byte-identical on every run.

The scene: a steaming bowl of ramen seen from a high angle on a dark
wooden table -- rich golden broth, wavy noodles, a soft-boiled egg with
a jammy yolk, narutomaki swirl, spring onions, chashu, and chopsticks
lifting a curl of noodles. Warm, bright food against a dark background,
no text -- it has to read at a glance and still look delicious at 300 px.
"""

import math
import os
import struct
import zlib
from random import Random

SIZE = 1024
SEED = 20261113

# Bowl geometry (high angle: wide, shallow ellipses)
BOWL_CX, BOWL_CY = 512, 565
BOWL_RX, BOWL_RY = 392, 318
BROTH_RX, BROTH_RY = 338, 272


# ---------------------------------------------------------------- palette
class Pal:
    TABLE = (40, 27, 17)
    TABLE_DK = (24, 15, 9)
    TABLE_LT = (62, 42, 26)
    BOWL_OUT = (26, 28, 46)       # deep indigo-black ceramic
    BOWL_OUT_LT = (52, 56, 84)
    BOWL_OUT_DK = (14, 15, 26)
    BOWL_RIM = (246, 236, 214)    # cream inner rim
    BROTH = (176, 106, 44)        # rich golden-brown broth
    BROTH_DK = (140, 78, 30)
    BROTH_LT = (224, 152, 66)
    BROTH_GLOSS = (255, 196, 110)
    NOODLE = (244, 214, 148)
    NOODLE_DK = (214, 172, 104)
    NOODLE_HI = (255, 236, 190)
    EGG_WHITE = (250, 244, 228)
    YOLK = (232, 126, 26)
    YOLK_DK = (198, 96, 14)
    YOLK_HI = (255, 176, 80)
    NARUTO = (244, 128, 150)      # pink swirl
    NARUTO_W = (252, 246, 238)
    ONION = (86, 168, 74)
    ONION_DK = (46, 112, 44)
    CHASHU = (196, 118, 88)
    CHASHU_DK = (150, 82, 58)
    CHASHU_LT = (228, 158, 120)
    NORI = (22, 34, 22)
    CHOP = (158, 104, 58)         # wooden chopsticks
    CHOP_DK = (110, 68, 34)
    CHOP_HI = (198, 142, 84)
    STEAM = (240, 240, 235)
    CHILI = (206, 52, 36)
    SESAME = (250, 240, 214)


# ---------------------------------------------------------------- canvas
class Canvas:
    """A flat RGB buffer with a few scanline drawing primitives."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def hline(self, y, x0, x1, rgb):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, int(x0))
        x1 = min(self.w - 1, int(x1))
        if x1 < x0:
            return
        n = x1 - x0 + 1
        i = (y * self.w + x0) * 3
        self.px[i:i + 3 * n] = bytes(rgb) * n

    def hline_alpha(self, y, x0, x1, rgb, alpha):
        if y < 0 or y >= self.h or alpha <= 0.0:
            return
        if alpha >= 1.0:
            self.hline(y, x0, x1, rgb)
            return
        x0 = max(0, int(x0))
        x1 = min(self.w - 1, int(x1))
        if x1 < x0:
            return
        a = int(alpha * 256)
        ia = 256 - a
        r, g, b = rgb
        i = (y * self.w + x0) * 3
        for _ in range(x1 - x0 + 1):
            self.px[i] = (r * a + self.px[i] * ia) >> 8
            self.px[i + 1] = (g * a + self.px[i + 1] * ia) >> 8
            self.px[i + 2] = (b * a + self.px[i + 2] * ia) >> 8
            i += 3

    def dot(self, x, y, rgb, alpha=1.0):
        if 0 <= x < self.w and 0 <= y < self.h and alpha > 0.0:
            a = int(alpha * 256)
            ia = 256 - a
            i = (y * self.w + x) * 3
            self.px[i] = (rgb[0] * a + self.px[i] * ia) >> 8
            self.px[i + 1] = (rgb[1] * a + self.px[i + 1] * ia) >> 8
            self.px[i + 2] = (rgb[2] * a + self.px[i + 2] * ia) >> 8

    def disc(self, cx, cy, r, rgb, alpha=1.0):
        r = int(r)
        for y in range(max(0, cy - r), min(self.h - 1, cy + r) + 1):
            dy = y - cy
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.hline_alpha(y, cx - dx, cx + dx, rgb, alpha)

    def ellipse(self, cx, cy, rx, ry, rgb, alpha=1.0):
        rx, ry = int(rx), int(ry)
        for y in range(max(0, cy - ry), min(self.h - 1, cy + ry) + 1):
            t = (y - cy) / ry
            dx = int(rx * math.sqrt(max(0.0, 1.0 - t * t)))
            self.hline_alpha(y, cx - dx, cx + dx, rgb, alpha)

    def poly(self, pts, rgb, alpha=1.0):
        """Scanline polygon fill."""
        edges = []
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if y0 != y1:
                edges.append((y0, y1, x0, x1))
        ymin = max(0, int(min(p[1] for p in pts)))
        ymax = min(self.h - 1, int(max(p[1] for p in pts)))
        for y in range(ymin, ymax + 1):
            xs = []
            for y0, y1, x0, x1 in edges:
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) / (y1 - y0) * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline_alpha(y, math.ceil(xs[i]), math.floor(xs[i + 1]),
                                 rgb, alpha)

    def thick_polyline(self, pts, radius, rgb, alpha=1.0):
        # Densify so consecutive discs overlap: otherwise long, gently
        # curving strands render as a dotted bead chain.
        prev = None
        for x, y in pts:
            if prev is None:
                self.disc(x, y, radius, rgb, alpha)
            else:
                px, py = prev
                d = math.hypot(x - px, y - py)
                n = max(1, int(d / 3))
                for i in range(1, n + 1):
                    self.disc(int(px + (x - px) * i / n),
                              int(py + (y - py) * i / n),
                              radius, rgb, alpha)
            prev = (x, y)


def quad_bezier(p0, p1, p2, steps):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        pts.append((
            int(u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]),
            int(u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]),
        ))
    return pts


def cubic_bezier(p0, p1, p2, p3, steps):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        pts.append((
            int(u ** 3 * p0[0] + 3 * u * u * t * p1[0]
                + 3 * u * t * t * p2[0] + t ** 3 * p3[0]),
            int(u ** 3 * p0[1] + 3 * u * u * t * p1[1]
                + 3 * u * t * t * p2[1] + t ** 3 * p3[1]),
        ))
    return pts


def in_broth(x, y):
    dx = (x - BOWL_CX) / BROTH_RX
    dy = (y - BOWL_CY) / BROTH_RY
    return dx * dx + dy * dy < 0.92


# ---------------------------------------------------------------- scene
def paint_table(cv, rng):
    for y in range(SIZE):
        cv.hline(y, 0, SIZE - 1, Pal.TABLE)
    # plank seams: horizontal bands, slightly darker, with wobble
    for y0 in (150, 330, 700, 880):
        for k in range(5):
            y = y0 + k
            cv.hline_alpha(y, 0, SIZE - 1, Pal.TABLE_DK,
                           0.55 if k == 2 else 0.22)
    # wood grain: long faint streaks
    for _ in range(46):
        y = rng.randrange(0, SIZE)
        x = rng.randrange(0, 700)
        ln = rng.randrange(120, 420)
        cv.hline_alpha(y, x, x + ln,
                       rng.choice([Pal.TABLE_LT, Pal.TABLE_DK]),
                       rng.uniform(0.08, 0.20))
    # soft warm pool of light under the bowl
    for y in range(180, 1024):
        t = 1.0 - (y - 180) / 844.0
        cv.hline_alpha(y, 60, 964, (120, 78, 40), 0.05 * t)
    # vignette: darken the corners
    for cx, cy, rx, ry in [(0, 0, 560, 420), (1024, 0, 560, 420),
                           (0, 1024, 580, 440), (1024, 1024, 580, 440)]:
        cv.ellipse(cx, cy, rx, ry, (8, 5, 3), 0.22)


def paint_bowl(cv):
    # outer ceramic + soft shadow on the table
    cv.ellipse(BOWL_CX, BOWL_CY + 26, BOWL_RX + 14, BOWL_RY + 12,
               (10, 7, 5), 0.45)
    cv.ellipse(BOWL_CX, BOWL_CY, BOWL_RX, BOWL_RY, Pal.BOWL_OUT)
    # rim light on the upper-left edge, shade lower-right
    cv.ellipse(BOWL_CX - 6, BOWL_CY - 8, BOWL_RX - 8, BOWL_RY - 8,
               Pal.BOWL_OUT_LT, 0.35)
    cv.ellipse(BOWL_CX + 10, BOWL_CY + 12, BOWL_RX - 16, BOWL_RY - 16,
               Pal.BOWL_OUT_DK, 0.30)
    # cream inner rim ring, then the broth
    cv.ellipse(BOWL_CX, BOWL_CY, BOWL_RX - 26, BOWL_RY - 22, Pal.BOWL_RIM)
    cv.ellipse(BOWL_CX, BOWL_CY, BROTH_RX, BROTH_RY, Pal.BROTH)
    # broth depth: darker toward the rim, lighter golden centre
    cv.ellipse(BOWL_CX, BOWL_CY, BROTH_RX - 26, BROTH_RY - 22,
               Pal.BROTH_DK, 0.35)
    cv.ellipse(BOWL_CX - 20, BOWL_CY - 14, 250, 196, Pal.BROTH_LT, 0.55)
    cv.ellipse(BOWL_CX - 30, BOWL_CY - 24, 190, 146, Pal.BROTH_LT, 0.35)
    # glossy highlight where the light hits the broth
    cv.ellipse(BOWL_CX - 170, BOWL_CY - 150, 150, 52, Pal.BROTH_GLOSS, 0.30)
    cv.ellipse(BOWL_CX - 150, BOWL_CY - 138, 90, 30, Pal.BROTH_GLOSS, 0.35)


def paint_noodle_strand(cv, pts, radius, color, hi=False):
    cv.thick_polyline(pts, radius, color, 0.95)
    if hi:
        cv.thick_polyline(pts, max(1, radius - 3), Pal.NOODLE_HI, 0.5)


def paint_noodles(cv, rng):
    # a tangled nest of wavy strands across the broth
    for _ in range(46):
        cx = rng.randrange(BOWL_CX - 260, BOWL_CX + 260)
        cy = rng.randrange(BOWL_CY - 190, BOWL_CY + 190)
        if not in_broth(cx, cy):
            continue
        amp = rng.uniform(14, 42)
        ln = rng.uniform(90, 260)
        ang = rng.uniform(0, math.pi)
        ca, sa = math.cos(ang), math.sin(ang)
        p0 = (cx - int(ln / 2 * ca), cy - int(ln / 2 * sa))
        p3 = (cx + int(ln / 2 * ca), cy + int(ln / 2 * sa))
        ph = rng.uniform(0, 6.28)
        mid = (cx + int(amp * math.cos(ph) * 0.6),
               cy + int(amp * math.sin(ph) * 0.6))
        pts = cubic_bezier(p0, (cx, cy - int(amp)), mid, p3, 22)
        paint_noodle_strand(cv, pts, rng.choice([5, 6, 6, 7]),
                            rng.choice([Pal.NOODLE, Pal.NOODLE,
                                        Pal.NOODLE_DK]),
                            hi=rng.random() < 0.4)
    # a few loose curls: small tight loops
    for _ in range(8):
        cx = rng.randrange(BOWL_CX - 200, BOWL_CX + 200)
        cy = rng.randrange(BOWL_CY - 140, BOWL_CY + 140)
        if not in_broth(cx, cy):
            continue
        r = rng.uniform(16, 30)
        pts = []
        for k in range(24):
            th = 2 * math.pi * k / 24
            pts.append((int(cx + r * 1.15 * math.cos(th)),
                        int(cy + r * 0.8 * math.sin(th))))
        cv.thick_polyline(pts, 5, Pal.NOODLE, 0.95)


def paint_chashu(cv):
    # two overlapping roasted-pork slices, left side of the bowl
    for cx, cy, rx, ry, rot in [(392, 470, 92, 66, 0.5),
                                (452, 540, 88, 62, -0.3)]:
        ca, sa = math.cos(rot), math.sin(rot)
        pts = []
        for k in range(28):
            th = 2 * math.pi * k / 28
            ex, ey = rx * math.cos(th), ry * math.sin(th)
            pts.append((int(cx + ex * ca - ey * sa),
                        int(cy + ex * sa + ey * ca)))
        cv.poly(pts, Pal.CHASHU_DK)
        pts2 = []
        for k in range(28):
            th = 2 * math.pi * k / 28
            ex, ey = (rx - 10) * math.cos(th), (ry - 9) * math.sin(th)
            pts2.append((int(cx + ex * ca - ey * sa),
                         int(cy + ex * sa + ey * ca)))
        cv.poly(pts2, Pal.CHASHU)
        pts3 = []
        for k in range(28):
            th = 2 * math.pi * k / 28
            ex, ey = (rx - 34) * math.cos(th), (ry - 30) * math.sin(th)
            pts3.append((int(cx + ex * ca - ey * sa),
                         int(cy + ex * sa + ey * ca)))
        cv.poly(pts3, Pal.CHASHU_LT, 0.85)
        # fatty edge glint
        cv.disc(cx - 30, cy - 26, 6, Pal.SESAME, 0.8)


def paint_egg(cv):
    # two halves of a soft-boiled egg, upper right; yolk jammy and glossy
    for cx, cy, rot in [(700, 448, 0.45), (788, 522, -0.5)]:
        ca, sa = math.cos(rot), math.sin(rot)
        pts = []
        for k in range(28):
            th = 2 * math.pi * k / 28
            ex, ey = 66 * math.cos(th), 50 * math.sin(th)
            pts.append((int(cx + ex * ca - ey * sa),
                        int(cy + ex * sa + ey * ca)))
        cv.poly(pts, (120, 70, 30), 0.5)          # soft shadow under egg
        pts = []
        for k in range(28):
            th = 2 * math.pi * k / 28
            ex, ey = 62 * math.cos(th), 47 * math.sin(th)
            pts.append((int(cx + ex * ca - ey * sa),
                        int(cy + ex * sa + ey * ca)))
        cv.poly(pts, Pal.EGG_WHITE)
        # yolk: deep orange, darker rim, bright jammy centre
        cv.ellipse(cx, cy, 36, 27, Pal.YOLK_DK)
        cv.ellipse(cx - 2, cy - 2, 31, 23, Pal.YOLK)
        cv.ellipse(cx - 6, cy - 6, 20, 14, Pal.YOLK_HI, 0.85)
        cv.disc(cx - 12, cy - 10, 4, (255, 220, 160), 0.9)


def paint_narutomaki(cv):
    # white fish cake with a pink spiral, lower left of the bowl
    cx, cy = 372, 660
    cv.disc(cx, cy, 46, Pal.NARUTO_W)
    cv.disc(cx, cy, 44, Pal.NARUTO, 0.9)
    # Archimedean spiral in white over the pink disc
    pts = []
    turns = 2.6
    steps = 90
    for i in range(steps + 1):
        th = turns * 2 * math.pi * i / steps
        r = 4 + 36 * i / steps
        pts.append((int(cx + r * math.cos(th)), int(cy + r * math.sin(th))))
    cv.thick_polyline(pts, 6, Pal.NARUTO_W, 0.95)
    cv.disc(cx, cy, 5, Pal.NARUTO_W)


def paint_nori(cv):
    # a sheet of nori standing at the back-left edge of the broth
    cv.poly([(330, 330), (392, 318), (404, 420), (344, 432)], Pal.NORI)
    cv.poly([(336, 334), (388, 324), (396, 408), (350, 418)],
            (38, 58, 38), 0.7)


def paint_onions(cv, rng):
    # scattered spring-onion rings
    for _ in range(30):
        cx = rng.randrange(BOWL_CX - 280, BOWL_CX + 280)
        cy = rng.randrange(BOWL_CY - 200, BOWL_CY + 200)
        if not in_broth(cx, cy):
            continue
        r = rng.choice([7, 8, 9])
        cv.disc(cx, cy, r, Pal.ONION)
        cv.disc(cx, cy, max(2, r - 4), Pal.ONION_DK)
        cv.disc(cx - 2, cy - 2, 2, (150, 210, 120), 0.8)


def paint_garnish(cv, rng):
    # chili threads and sesame seeds
    for _ in range(7):
        cx = rng.randrange(BOWL_CX - 180, BOWL_CX + 180)
        cy = rng.randrange(BOWL_CY - 130, BOWL_CY + 130)
        if not in_broth(cx, cy):
            continue
        ang = rng.uniform(0, math.pi)
        ln = rng.randrange(22, 40)
        ca, sa = math.cos(ang), math.sin(ang)
        cv.thick_polyline(
            [(int(cx - ln / 2 * ca), int(cy - ln / 2 * sa)),
             (int(cx + ln / 2 * ca), int(cy + ln / 2 * sa))],
            2, Pal.CHILI, 0.95)
    for _ in range(26):
        cx = rng.randrange(BOWL_CX - 260, BOWL_CX + 260)
        cy = rng.randrange(BOWL_CY - 180, BOWL_CY + 180)
        if not in_broth(cx, cy):
            continue
        cv.disc(cx, cy, 2, Pal.SESAME, rng.uniform(0.6, 0.95))


def paint_chopsticks_and_lift(cv, rng):
    # chopsticks enter from the top right, tips pinching a lifted curl
    tip = (668, 402)
    base1 = (872, 128)
    base2 = (906, 176)
    # lifted noodle curl: strands rising from the broth to the tips
    for k in range(5):
        off = (k - 2) * 9
        p0 = (640 + off, 470)
        p1 = (620 + off, 420)
        p2 = (648 + off, 372)
        p3 = (tip[0] + off // 2, tip[1] + 6)
        pts = cubic_bezier(p0, p1, p2, p3, 24)
        paint_noodle_strand(cv, pts, 6,
                            Pal.NOODLE if k % 2 == 0 else Pal.NOODLE_DK,
                            hi=(k % 2 == 0))
    # a small loop of noodles draped over the chopstick tips
    loop = []
    for i in range(26):
        th = math.pi * i / 25
        loop.append((int(660 + 26 * math.cos(th)),
                     int(398 + 18 * math.sin(th))))
    cv.thick_polyline(loop, 6, Pal.NOODLE, 0.95)
    # chopsticks: two tapered wooden sticks over the noodles
    for b, t in [(base1, (tip[0] - 8, tip[1] - 14)),
                 (base2, (tip[0] + 10, tip[1] + 2))]:
        dx, dy = t[0] - b[0], t[1] - b[1]
        ln = math.hypot(dx, dy)
        nx, ny = -dy / ln, dx / ln
        w0, w1 = 11, 4
        cv.poly([
            (int(b[0] + nx * w0), int(b[1] + ny * w0)),
            (int(b[0] - nx * w0), int(b[1] - ny * w0)),
            (int(t[0] - nx * w1), int(t[1] - ny * w1)),
            (int(t[0] + nx * w1), int(t[1] + ny * w1)),
        ], Pal.CHOP)
        cv.thick_polyline(
            [(int(b[0] + nx * (w0 - 3)), int(b[1] + ny * (w0 - 3))),
             (int(t[0] + nx * (w1 - 1)), int(t[1] + ny * (w1 - 1)))],
            2, Pal.CHOP_HI, 0.7)


def paint_steam(cv, rng):
    # curling steam rising above the bowl, soft and translucent
    for cx, base_y, height, phase in [
        (400, 300, 210, 0.0),
        (500, 280, 250, 1.4),
        (600, 290, 230, 2.6),
        (690, 320, 180, 3.8),
        (330, 330, 160, 5.0),
    ]:
        pts = []
        for i in range(30):
            t = i / 29
            x = cx + int(26 * math.sin(phase + t * 5.2) * (0.4 + t))
            y = int(base_y - t * height)
            pts.append((x, y))
        cv.thick_polyline(pts, 13, Pal.STEAM, 0.10)
        cv.thick_polyline(pts, 6, Pal.STEAM, 0.12)


# ---------------------------------------------------------------- PNG out
def encode_png(cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    return png


def main():
    rng = Random(SEED)
    cv = Canvas(SIZE, SIZE)
    paint_table(cv, rng)
    paint_bowl(cv)
    paint_noodles(cv, rng)
    paint_chashu(cv)
    paint_nori(cv)
    paint_egg(cv)
    paint_narutomaki(cv)
    paint_onions(cv, rng)
    paint_garnish(cv, rng)
    paint_chopsticks_and_lift(cv, rng)
    paint_steam(cv, rng)

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    data = encode_png(cv)
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
