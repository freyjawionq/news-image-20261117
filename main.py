#!/usr/bin/env python3
"""THE WORLD IN ONE DAY - a deterministic newspaper front page for
Tuesday 17 November 2026, drawn entirely by this program.

Standard library only. No clock, no randomness, no network: every run
writes exactly the same bytes to entry.png in the output directory
(MAKEFUN_OUTPUT_DIR in development, /output in production).

The renderer is self-contained: a minimal PNG writer (zlib + struct +
CRC), an RGB framebuffer, line/rectangle/circle primitives and a small
5x7 bitmap font defined as data below.
"""

import math
import os
import struct
import zlib

W, H = 1024, 768

PAPER = (246, 243, 236)
PANEL_BG = (253, 252, 248)
INK = (24, 24, 28)
GRAY = (96, 94, 88)
ACCENT = (176, 32, 32)

# ---------------------------------------------------------------- font
# 5x7 bitmap glyphs, 7 rows of 5 pixels, '#' = ink.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("###..", "#..#.", "#...#", "#...#", "#...#", "#..#.", "###.."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", ".#.#.", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "'": (".##..", ".##..", ".#...", ".....", ".....", ".....", "....."),
    "$": ("..#..", ".####", "#.#.#", ".###.", "#.#..", "####.", "..#.."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "..##.", "..#..", ".....", "..#.."),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
}


# ------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(bytes(bg) * (w * h))

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i] = c[0]
            self.buf[i + 1] = c[1]
            self.buf[i + 2] = c[2]

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + len(row)] = row

    def rect(self, x, y, w, h, c, t=1):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if t == 1:
                self.px(x0, y0, c)
            else:
                self.fill_rect(x0 - t // 2, y0 - t // 2, t, t, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, t=1):
        x, y, err = r, 0, 1 - r
        while x >= y:
            for ox, oy in ((x, y), (y, x), (-y, x), (-x, y),
                           (-x, -y), (-y, -x), (y, -x), (x, -y)):
                self.fill_rect(cx + ox, cy + oy, t, t, c)
            y += 1
            if err < 0:
                err += 2 * y + 1
            else:
                x -= 1
                err += 2 * (y - x) + 1

    def ellipse(self, cx, cy, rx, ry, c):
        prev = None
        steps = 72
        for i in range(steps + 1):
            a = 2.0 * math.pi * i / steps
            p = (int(round(cx + rx * math.cos(a))),
                 int(round(cy + ry * math.sin(a))))
            if prev is not None:
                self.line(prev[0], prev[1], p[0], p[1], c, 1)
            prev = p

    def wave(self, x, y, length, c, phase=0.0):
        for i in range(length):
            self.px(x + i, y + int(round(1.6 * math.sin(i * 0.55 + phase))), c)


# --------------------------------------------------------------- text
def text_width(s, scale):
    if not s:
        return 0
    return len(s) * 6 * scale - scale


def draw_text(cv, x, y, s, scale, c):
    cx = x
    for ch in s:
        glyph = FONT.get(ch, FONT[" "])
        for ri, row in enumerate(glyph):
            for ci, bit in enumerate(row):
                if bit == "#":
                    cv.fill_rect(cx + ci * scale, y + ri * scale,
                                 scale, scale, c)
        cx += 6 * scale
    return cx - x


def draw_centered(cv, y, s, scale, c):
    draw_text(cv, (W - text_width(s, scale)) // 2, y, s, scale, c)


def wrap(s, maxchars):
    lines = []
    cur = ""
    for word in s.split():
        cand = word if not cur else cur + " " + word
        if len(cand) <= maxchars:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------- icons
def icon_bridge(cv, x, y, s):
    c = INK
    deck_y = y + (s * 2) // 3
    top = y + 2
    prev = None
    for i in range(41):
        t = i / 40.0
        px_ = x + 2 + t * (s - 4)
        py_ = deck_y - (deck_y - top) * (1.0 - (2.0 * t - 1.0) ** 2)
        p = (int(round(px_)), int(round(py_)))
        if prev is not None:
            cv.line(prev[0], prev[1], p[0], p[1], c, 1)
        prev = p
    for i in range(1, 8):
        t = i / 8.0
        px_ = int(round(x + 2 + t * (s - 4)))
        py_ = int(round(deck_y - (deck_y - top) * (1.0 - (2.0 * t - 1.0) ** 2)))
        cv.line(px_, py_, px_, deck_y, c, 1)
    cv.line(x + 1, deck_y, x + s - 1, deck_y, c, 2)
    cv.wave(x + 3, deck_y + 8, s - 6, c)
    cv.wave(x + 3, deck_y + 13, s - 6, c, phase=1.7)


def icon_globe(cv, x, y, s):
    c = INK
    cx, cy, r = x + s // 2, y + s // 2, s // 2 - 2
    cv.circle(cx, cy, r, c, 1)
    for dy in (-r // 2, 0, r // 2):
        half = math.isqrt(r * r - dy * dy)
        cv.line(cx - half, cy + dy, cx + half, cy + dy, c, 1)
    cv.ellipse(cx, cy, r // 2, r, c)
    cv.line(cx, cy - r, cx, cy + r, c, 1)


def icon_chip(cv, x, y, s):
    c = INK
    bx, by, bs = x + s // 4, y + s // 4, s // 2
    cv.rect(bx, by, bs, bs, c, 2)
    cv.rect(bx + bs // 4, by + bs // 4, bs // 2, bs // 2, c, 1)
    for i in range(3):
        px_ = bx + (i + 1) * bs // 4
        cv.line(px_, by - 6, px_, by, c, 2)
        cv.line(px_, by + bs, px_, by + bs + 6, c, 2)
        py_ = by + (i + 1) * bs // 4
        cv.line(bx - 6, py_, bx, py_, c, 2)
        cv.line(bx + bs, py_, bx + bs, py_, c, 2)


def icon_rocket(cv, x, y, s):
    c = INK
    cx = x + s // 2
    cv.line(cx, y + 2, cx - 8, y + 18, c, 2)
    cv.line(cx, y + 2, cx + 8, y + 18, c, 2)
    cv.line(cx - 8, y + 18, cx - 8, y + s - 14, c, 2)
    cv.line(cx + 8, y + 18, cx + 8, y + s - 14, c, 2)
    cv.line(cx - 8, y + s - 14, cx + 8, y + s - 14, c, 1)
    cv.circle(cx, y + 26, 4, c, 1)
    cv.line(cx - 8, y + s - 22, cx - 15, y + s - 5, c, 2)
    cv.line(cx + 8, y + s - 22, cx + 15, y + s - 5, c, 2)
    cv.line(cx - 4, y + s - 13, cx, y + s - 2, ACCENT, 2)
    cv.line(cx + 4, y + s - 13, cx, y + s - 2, ACCENT, 2)


def icon_cross(cv, x, y, s):
    cx, cy = x + s // 2, y + s // 2
    cv.fill_rect(cx - 5, y + 8, 10, s - 16, ACCENT)
    cv.fill_rect(x + 8, cy - 5, s - 16, 10, ACCENT)


def icon_ship(cv, x, y, s):
    c = INK
    deck = y + s // 2 + 2
    cv.rect(x + 10, deck - 12, 12, 12, c, 1)
    cv.rect(x + 24, deck - 12, 12, 12, c, 1)
    cv.rect(x + 17, deck - 22, 12, 10, c, 1)
    cv.line(x + 3, deck, x + s - 3, deck, c, 2)
    cv.line(x + 3, deck, x + 10, deck + 10, c, 2)
    cv.line(x + s - 3, deck, x + s - 10, deck + 10, c, 2)
    cv.line(x + 10, deck + 10, x + s - 10, deck + 10, c, 2)
    cv.wave(x + 4, deck + 16, s - 8, c, phase=0.6)


def icon_shield(cv, x, y, s):
    c = INK
    pts = [(x + s // 2, y + 3), (x + s - 6, y + 10), (x + s - 6, y + s // 2),
           (x + s // 2, y + s - 3), (x + 6, y + s // 2), (x + 6, y + 10)]
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        cv.line(x0, y0, x1, y1, c, 2)
    cv.line(x + s // 2 - 8, y + s // 2, x + s // 2 - 2, y + s // 2 + 7, c, 2)
    cv.line(x + s // 2 - 2, y + s // 2 + 7, x + s // 2 + 10, y + s // 2 - 8,
            c, 2)


# -------------------------------------------------------------- panels
STORIES = [
    ("UKRAINE STRIKES KERCH BRIDGE AGAIN",
     "ROAD SPAN FALLS, TRAFFIC HALTED; MISSILES HIT KYIV", icon_bridge),
    ("COP31 DRAFT DEAL SPEEDS FOSSIL PHASE-OUT",
     "DRAFT PROPOSES AT LEAST $120BN ADAPTATION FINANCE TO 2035", icon_globe),
    ("US TIGHTENS AI CHIP EXPORT CURBS ON CHINA",
     "NEW RULES CLOSE OVERSEAS PURCHASE LOOPHOLE", icon_chip),
    ("WEST URGES ISRAEL TO OPEN GAZA CROSSINGS",
     "UK SANCTIONS SETTLEMENT FIRMS AS AID WAITS AT BORDER", icon_cross),
    ("JAPAN JETS SCRAMBLE OVER AIRSPACE BREACH",
     "TWO SUSPECTED RUSSIAN AIRCRAFT ENTERED AIRSPACE OFF FUKUOKA",
     icon_rocket),
    ("GAS TANKER ABLAZE AFTER HORMUZ STRIKES",
     "TARA GAS CREW ABANDON SHIP OFF OMAN; ONE SEAFARER MISSING",
     icon_ship),
    ("RAMSTEIN ALLIES PLEDGE AIR DEFENCE",
     "NEW AID PACKAGES FOR UKRAINE AGREED IN BRUSSELS", icon_shield),
]


def panel(cv, x, y, w, h, headline, sub, icon, icon_size, text_off):
    cv.fill_rect(x, y, w, h, PANEL_BG)
    cv.rect(x, y, w, h, INK, 2)
    icon(cv, x + 12, y + 14, icon_size)
    tx = x + text_off
    maxc = (w - text_off - 12) // 12
    ly = y + 16
    for ln in wrap(headline, maxc)[:3]:
        draw_text(cv, tx, ly, ln, 2, INK)
        ly += 19
    cv.line(x + 14, y + 80, x + w - 14, y + 80, GRAY, 1)
    maxc1 = (w - 28) // 6
    sy = y + 90
    for ln in wrap(sub, maxc1)[:3]:
        draw_text(cv, x + 14, sy, ln, 1, INK)
        sy += 10


def render():
    cv = Canvas(W, H, PAPER)
    cv.rect(8, 8, W - 16, H - 16, INK, 1)
    mx = 28

    # masthead
    cv.fill_rect(mx, 18, W - 2 * mx, 3, INK)
    cv.fill_rect(mx, 25, W - 2 * mx, 1, INK)
    draw_centered(cv, 34, "THE WORLD IN ONE DAY", 6, INK)
    cv.fill_rect(mx, 84, W - 2 * mx, 3, INK)
    draw_centered(cv, 95, "TUESDAY 17 NOVEMBER 2026", 3, INK)
    cv.fill_rect(mx, 124, W - 2 * mx, 1, INK)

    # lead story
    ly = 134
    for ln in wrap("XI TRUMP PUTIN SET FIRST TRILATERAL SUMMIT", 40):
        draw_centered(cv, ly, ln, 4, INK)
        ly += 36
    draw_centered(cv, ly + 4,
                  "LEADERS TO MEET IN SHENZHEN AT APEC ON THURSDAY", 2, INK)
    cv.fill_rect(mx, 232, W - 2 * mx, 2, INK)

    # story grid: rows of 2, 2, 3
    rows = [(STORIES[0:2], 474, 52, 78),
            (STORIES[2:4], 474, 52, 78),
            (STORIES[4:7], 312, 40, 56)]
    py = 246
    for stories, pw, isize, toff in rows:
        total = W - 2 * mx
        gap = (total - pw * len(stories)) // (len(stories) - 1) \
            if len(stories) > 1 else 0
        px = mx
        for headline, sub, icon in stories:
            panel(cv, px, py, pw, 148, headline, sub, icon, isize, toff)
            px += pw + gap
        py += 158

    # footer
    cv.fill_rect(mx, 722, W - 2 * mx, 1, INK)
    draw_centered(cv, 730,
                  "SOURCES IN SOURCES.MD - DRAWN BY PROGRAM, NO PHOTOS",
                  2, GRAY)
    return cv


# ----------------------------------------------------------------- png
def png_bytes(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.buf[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data +
                struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    data = png_bytes(render())
    with open(os.path.join(outdir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
