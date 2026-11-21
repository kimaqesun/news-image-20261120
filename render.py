#!/usr/bin/env python3
"""Deterministic PIL renderer for the WORLD NEWS MANGA poster (see SPEC.md).

Renders entry.png (1024x1024, <900 KB) summarizing 20 November 2026 world
news in manga style: dark halftone background, cream ink-outlined panels
with colored tag tabs, chibi mascots, and a bottom ticker. Pure PIL, no
network, no randomness, no clock. Every text run is measured with PIL and
asserted to stay inside its panel; mascots are confined to a reserved
right-hand zone (~150 px) of each panel.
"""

import math
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "entry.png")
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
W = H = 1024

INK = (26, 22, 34)
BG = (18, 16, 28)
BG_DOT = (30, 27, 44)
SPEED = (58, 52, 82)
CREAM = (246, 240, 230)
BODY_INK = (60, 54, 66)
CORAL = (232, 80, 66)
YELLOW = (247, 196, 60)
SKY = (86, 168, 224)
MINT = (96, 200, 150)
PURPLE = (150, 110, 220)
ORANGE = (240, 140, 50)
TICKER_BG = (32, 29, 48)

_checks = []


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def bold(size):
    return _font("DejaVuSans-Bold.ttf", size)


def body(size):
    return _font("DejaVuSans.ttf", size)


def mono(size):
    return _font("DejaVuSansMono-Bold.ttf", size)


def check(label, bbox, box):
    """Assert measured bbox (x0, y0, x1, y1) lies inside container box."""
    x0, y0, x1, y1 = bbox
    bx0, by0, bx1, by1 = box
    ok = x0 >= bx0 and y0 >= by0 and x1 <= bx1 and y1 <= by1
    _checks.append((label, ok))
    if not ok:
        raise AssertionError("%s: bbox %s escapes container %s" % (label, bbox, box))


def text(d, x, y, s, fnt, fill, box, label):
    d.text((x, y), s, font=fnt, fill=fill)
    bb = d.textbbox((x, y), s, font=fnt)
    check(label, bb, box)
    return bb


def wrap(s, fnt, max_w):
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if fnt.getlength(trial) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    for ln in lines:
        if fnt.getlength(ln) > max_w:
            raise AssertionError("word too wide for %dpx: %r" % (max_w, ln))
    return lines


def text_block(d, x, y, s, fnt, fill, max_w, line_h, max_lines, box, label):
    lines = wrap(s, fnt, max_w)
    if len(lines) > max_lines:
        raise AssertionError("%s: %d lines exceeds allotment of %d"
                             % (label, len(lines), max_lines))
    for i, ln in enumerate(lines):
        text(d, x, y + i * line_h, ln, fnt, fill, box, "%s L%d" % (label, i + 1))
    return y + len(lines) * line_h


# ---------------------------------------------------------------- background

def background(d):
    d.rectangle((0, 0, W, H), fill=BG)
    # Subtle halftone dot texture: staggered grid, deterministic radii.
    for row, y in enumerate(range(6, H, 16)):
        xoff = 8 if row % 2 else 0
        for x in range(6 + xoff, W, 16):
            r = 1.2 + ((x * 7 + y * 13) % 5) * 0.25
            d.ellipse((x - r, y - r, x + r, y + r), fill=BG_DOT)
    # Manga speed lines radiating inward from each canvas corner.
    for cx, cy, base in ((0, 0, 0), (W, 0, 90), (W, H, 180), (0, H, 270)):
        for i in range(7):
            a = math.radians(base + 12 + i * 11)
            r2 = 104 + (i % 3) * 14
            d.line((cx + math.cos(a) * 46, cy + math.sin(a) * 46,
                    cx + math.cos(a) * r2, cy + math.sin(a) * r2),
                   fill=SPEED, width=3)


def masthead(d):
    x, y, w, h = 16, 14, 992, 104
    d.rounded_rectangle((x, y, x + w, y + h), radius=16,
                        fill=CORAL, outline=INK, width=4)
    # Decorative speed ticks on the plate edges, far from centered text.
    for i in range(3):
        yy = y + 26 + i * 22
        d.line((x + 10, yy + 8, x + 26, yy), fill=CREAM, width=3)
        d.line((x + w - 10, yy + 8, x + w - 26, yy), fill=CREAM, width=3)
    box = (x + 40, y + 6, x + w - 40, y + h - 6)
    f = bold(50)
    title = "WORLD NEWS MANGA!"
    tw = f.getlength(title)
    text(d, x + (w - tw) / 2, y + 12, title, f, CREAM, box, "masthead title")
    f2 = bold(19)
    sub = "FRIDAY 20 NOVEMBER 2026 \u00b7 THE WORLD IN ONE PAGE"
    sw = f2.getlength(sub)
    text(d, x + (w - sw) / 2, y + 74, sub, f2, (255, 232, 220), box,
         "masthead subtitle")


# -------------------------------------------------------------------- panels

def panel(d, x, y, w, h, accent, tag):
    d.rounded_rectangle((x, y, x + w, y + h), radius=14,
                        fill=CREAM, outline=INK, width=4)
    f = mono(15)
    tw = f.getlength(tag)
    tab_w = int(tw) + 28
    tab = (x + 18, y - 13, x + 18 + tab_w, y + 13)
    d.rounded_rectangle(tab, radius=8, fill=accent, outline=INK, width=3)
    lum = 0.299 * accent[0] + 0.587 * accent[1] + 0.114 * accent[2]
    tfill = INK if lum > 150 else CREAM
    bb = d.textbbox((0, 0), tag, font=f)
    th = bb[3] - bb[1]
    ty = (y - 13) + (26 - th) // 2 - bb[1]
    text(d, x + 32, ty, tag, f, tfill,
         (tab[0] + 4, tab[1] + 2, tab[2] - 4, tab[3] - 2), "tag " + tag)
    return dict(x=x, y=y, w=w, h=h, right=x + w, bottom=y + h)


def panel_text(d, p, headline, body_s, hsize, bsize, hlines, blines):
    tx = p["x"] + 16
    text_right = p["right"] - 150 - 12  # reserve right ~150px for mascot
    max_w = text_right - tx
    box = (tx - 2, p["y"] + 16, text_right + 2, p["bottom"] - 10)
    y = text_block(d, tx, p["y"] + 24, headline, bold(hsize), INK,
                   max_w, hsize + 5, hlines, box, "headline")
    text_block(d, tx, y + 6, body_s, body(bsize), BODY_INK,
               max_w, bsize + 5, blines, box, "body")


def mascot_zone(p):
    return (p["right"] - 150 + 4, p["y"] + 18, p["right"] - 8, p["bottom"] - 14)


# ------------------------------------------------------------------- mascots

def chibi(d, cx, cy, r, fill):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=INK, width=3)
    for ex in (cx - r * 0.35, cx + r * 0.35):
        d.ellipse((ex - 2.6, cy - r * 0.15 - 2.6, ex + 2.6, cy - r * 0.15 + 2.6),
                  fill=INK)
    d.arc((cx - r * 0.45, cy + r * 0.05, cx + r * 0.45, cy + r * 0.55),
          15, 165, fill=INK, width=3)


def mascot_summit(d, z):
    x0, y0, x1, y1 = z
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = 21
    for dx, fill in ((-46, SKY), (0, ORANGE), (46, CORAL)):
        chibi(d, cx + dx, cy, r, fill)
    check("mascot summit", (cx - 46 - r, cy - r, cx + 46 + r, cy + r), z)


def mascot_gavel(d, z):
    x0, y0, x1, y1 = z
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    u = (math.cos(math.radians(-45)), math.sin(math.radians(-45)))
    v = (-u[1], u[0])
    hc = (cx + 16, cy - 16)
    pts = []
    for su, sv in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        pts.append((hc[0] + su * 22 * u[0] + sv * 9 * v[0],
                    hc[1] + su * 22 * u[1] + sv * 9 * v[1]))
    d.line((hc[0], hc[1], cx - 26, cy + 26), fill=(120, 86, 60), width=8)
    d.polygon(pts, fill=YELLOW, outline=INK)
    d.rounded_rectangle((cx - 36, cy + 32, cx + 6, cy + 42), radius=4,
                        fill=ORANGE, outline=INK, width=3)
    for i in range(3):
        a = math.radians(-100 + i * 30)
        d.line((hc[0] + math.cos(a) * 30, hc[1] + math.sin(a) * 30,
                hc[0] + math.cos(a) * 40, hc[1] + math.sin(a) * 40),
               fill=INK, width=2)
    check("mascot gavel", (cx - 38, cy - 48, cx + 40, cy + 44), z)


def mascot_chart(d, z):
    x0, y0, x1, y1 = z
    cy = (y0 + y1) / 2
    d.line((x0 + 2, cy - 40, x0 + 2, cy + 44, x1 - 2, cy + 44),
           fill=(190, 182, 170), width=2)
    pts = [(x0 + 6, cy - 34), (x0 + 34, cy - 8), (x0 + 58, cy - 22),
           (x0 + 92, cy + 16), (x1 - 18, cy + 32)]
    d.line(pts, fill=CORAL, width=5, joint="curve")
    ax, ay = pts[-2]
    bx, by = pts[-1]
    dx, dy = bx - ax, by - ay
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    tip = (bx + ux * 16, by + uy * 16)
    b1 = (bx + px * 9, by + py * 9)
    b2 = (bx - px * 9, by - py * 9)
    d.polygon([tip, b1, b2], fill=CORAL, outline=INK)
    gcx, gcy = (tip[0] + b1[0] + b2[0]) / 3, (tip[1] + b1[1] + b2[1]) / 3
    for ex in (gcx - 3.5, gcx + 3.5):
        d.ellipse((ex - 1.8, gcy - 1.8, ex + 1.8, gcy + 1.8), fill=CREAM)
    check("mascot chart", (x0, cy - 42, tip[0] + 2, cy + 46), z)


def mascot_warning(d, z):
    x0, y0, x1, y1 = z
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    d.polygon([(cx, cy - 42), (cx - 46, cy + 34), (cx + 46, cy + 34)],
              fill=YELLOW, outline=INK)
    d.line((cx, cy - 42, cx - 46, cy + 34, cx + 46, cy + 34, cx, cy - 42),
           fill=INK, width=4)
    d.rounded_rectangle((cx - 4, cy - 14, cx + 4, cy + 10), radius=2, fill=INK)
    d.ellipse((cx - 4, cy + 16, cx + 4, cy + 24), fill=INK)
    check("mascot warning", (cx - 48, cy - 44, cx + 48, cy + 36), z)


def mascot_earth(d, z):
    x0, y0, x1, y1 = z
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = 42
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=SKY, outline=INK, width=3)
    d.ellipse((cx - 28, cy - 24, cx - 6, cy - 6), fill=MINT)
    d.ellipse((cx + 8, cy + 4, cx + 30, cy + 22), fill=MINT)
    for ex in (cx - 13, cx + 13):
        d.ellipse((ex - 3, cy - 11, ex + 3, cy - 5), fill=INK)
    d.line((cx - 19, cy - 18, cx - 7, cy - 14), fill=INK, width=3)
    d.line((cx + 19, cy - 18, cx + 7, cy - 14), fill=INK, width=3)
    d.arc((cx - 12, cy + 8, cx + 12, cy + 22), 200, 340, fill=INK, width=3)
    check("mascot earth", (cx - r, cy - r, cx + r, cy + r), z)


def mascot_megaphone(d, z):
    x0, y0, x1, y1 = z
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    d.rounded_rectangle((cx - 44, cy - 12, cx - 32, cy + 12), radius=3,
                        fill=CREAM, outline=INK, width=3)
    d.polygon([(cx - 34, cy - 12), (cx + 16, cy - 32),
               (cx + 16, cy + 32), (cx - 34, cy + 12)],
              fill=ORANGE, outline=INK)
    d.line((cx - 34, cy - 12, cx + 16, cy - 32, cx + 16, cy + 32,
            cx - 34, cy + 12, cx - 34, cy - 12), fill=INK, width=3)
    d.ellipse((cx + 10, cy - 32, cx + 22, cy + 32),
              fill=(250, 170, 90), outline=INK, width=3)
    d.rectangle((cx - 28, cy + 12, cx - 16, cy + 30), fill=INK)
    for dy1, dy2 in ((-20, -28), (0, 0), (20, 28)):
        d.line((cx + 30, cy + dy1, cx + 44, cy + dy2), fill=INK, width=3)
    check("mascot megaphone", (cx - 46, cy - 34, cx + 46, cy + 32), z)


def mascot_handshake(d, z):
    x0, y0, x1, y1 = z
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    d.line((cx - 26, cy + 12, cx - 8, cy + 26), fill=INK, width=6)
    d.line((cx + 26, cy + 12, cx + 8, cy + 26), fill=INK, width=6)
    d.rounded_rectangle((cx - 12, cy + 20, cx + 12, cy + 34), radius=5,
                        fill=CREAM, outline=INK, width=3)
    chibi(d, cx - 26, cy - 12, 27, SKY)
    chibi(d, cx + 26, cy - 12, 27, YELLOW)
    check("mascot handshake", (cx - 53, cy - 39, cx + 53, cy + 34), z)


# -------------------------------------------------------------------- ticker

def ticker(d):
    x, y, w, h = 16, 960, 992, 48
    d.rounded_rectangle((x, y, x + w, y + h), radius=12,
                        fill=TICKER_BG, outline=INK, width=3)
    f = mono(14)
    box = (x + 14, y + 4, x + w - 14, y + h - 4)
    l1 = "KOREA: COURT OVERTURNS HAN'S JAIL TERM \u00b7 FIJI DECLARES DROUGHT DISASTER"
    l2 = "YEMEN CRISIS DEEPENS \u00b7 IRAQ DEPLOYS TO JURF AL-SAKHAR \u00b7 IRAN WAR COST $48.3B"
    text(d, x + 16, y + 6, l1, f, YELLOW, box, "ticker 1")
    text(d, x + 16, y + 26, l2, f, CREAM, box, "ticker 2")


# ---------------------------------------------------------------------- main

PANELS = [
    # (x, y, w, h, accent, tag, headline, body, mascot, hsize, bsize, hlines, blines)
    (16, 132, 992, 196, CORAL, "PANEL 1 \u00b7 SHENZHEN SUMMIT",
     "Trump, Xi, Putin: first three-way summit ever!",
     "Historic nuclear-risk dialogue opens in Shenzhen. Russia calls the meeting "
     "a watershed; Europe is excluded from the room.",
     mascot_summit, 30, 18, 2, 3),
    (16, 342, 488, 192, PURPLE, "PANEL 2 \u00b7 THE HAGUE",
     "World court: Myanmar guilty of genocide",
     "First-ever state conviction under the 1948 Genocide Convention. Judges vote 9-6.",
     mascot_gavel, 21, 16, 2, 4),
    (16, 548, 488, 192, SKY, "PANEL 3 \u00b7 TAIPEI",
     "AI bubble pops! Taiex -6.2%, week -18%",
     "Anthropic's record IPO lands the same day; chip stocks lead the drop.",
     mascot_chart, 21, 16, 2, 4),
    (16, 754, 488, 192, ORANGE, "PANEL 4 \u00b7 KYIV & RIYADH",
     "Missiles rain on two capitals",
     "Russia fires ~100 missiles and 400 drones at Kyiv; a Houthi missile hits "
     "Riyadh's tallest tower.",
     mascot_warning, 21, 16, 2, 4),
    (520, 342, 488, 192, MINT, "PANEL 5 \u00b7 ANTALYA",
     "COP31 ends \u2014 fossil-fuel words stripped",
     "200 governments end talks short of a deal; the final text drops fossil-fuel language.",
     mascot_earth, 21, 16, 2, 4),
    (520, 548, 488, 192, YELLOW, "PANEL 6 \u00b7 NEW DELHI",
     "Gen Z revolt over deleted voters!",
     "130 million names deleted from the rolls; the education minister resigns amid protests.",
     mascot_megaphone, 21, 16, 2, 4),
    (520, 754, 488, 192, CORAL, "PANEL 7 \u00b7 BRUSSELS",
     "UK and EU meet to mend Brexit fences",
     "PM Burnham meets EU leaders a decade after the vote; Denmark seals a Greenland deal.",
     mascot_handshake, 21, 16, 2, 4),
]


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    background(d)
    masthead(d)
    for (x, y, w, h, accent, tag, headline, body_s, mascot,
         hs, bs, hl, bl) in PANELS:
        p = panel(d, x, y, w, h, accent, tag)
        panel_text(d, p, headline, body_s, hs, bs, hl, bl)
        mascot(d, mascot_zone(p))
    ticker(d)

    failed = [c for c in _checks if not c[1]]
    if failed:
        raise AssertionError("containment failures: %s" % failed)
    print("%d text/mascot containment checks passed" % len(_checks))

    img.save(OUT, "PNG", optimize=True)
    size = os.path.getsize(OUT)
    print("entry.png: %dx%d, %d bytes (%.1f KB)" % (img.size[0], img.size[1],
                                                    size, size / 1024))
    assert img.size == (1024, 1024), "wrong dimensions"
    assert size < 900 * 1024, "PNG exceeds 900 KB"


if __name__ == "__main__":
    main()
