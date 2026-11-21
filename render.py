#!/usr/bin/env python3
"""Render the v5 "ONE DAY OF WORLD NEWS" newspaper front page.

Implements SPEC.md (design spec v5) from scratch: a dense, warm-cream
newspaper/infographic front page covering 32 stories, all dated Friday
20 November 2026. Pure PIL, fully deterministic -- no network, no
randomness, no clock reads. Output: entry.png, 1024x1024, under 900 KB.

v5: every illustration (the three featured scenes and all ten grid
scenes) is restyled as a DOODLE STICKER -- very thick near-black
outlines, flat bright fills, a pure-white die-cut silhouette border
(the drawing's alpha dilated 10px) behind each scene, small expressive
faces on personified objects, and sparkles / motion dashes / zigzag
energy marks. The grid rhythm still varies: light cream/mint/sky/butter
cell tints, illustrations offset left vs right between neighbors, and a
different accent underline style per row (solid / dashed, double rule
between rows).

Every text placement and every drawn box is guarded by an internal
containment check; the run aborts on the first violation and prints a
summary count when all checks pass.
"""

import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ----------------------------------------------------------------------
# Canvas, palette, fonts
# ----------------------------------------------------------------------

W = H = 1024
MARGIN = 16
CONTENT_W = W - 2 * MARGIN  # 992

PAPER = (247, 243, 233)
INK = (25, 25, 30)
RULE = (60, 60, 70)
FAINT = (228, 222, 208)

RED = (200, 40, 40)
BLUE = (25, 80, 160)
TEAL = (0, 120, 120)
AMBER = (200, 130, 20)
GREEN = (40, 120, 60)
PURPLE = (110, 50, 140)

# v5 doodle-sticker palette: flat, bright, marker-like fills + near-black
# outline. No gradients, no shading.
OUTLINE = (22, 22, 26)
S_RED = (228, 52, 52)
S_YELLOW = (255, 205, 40)
S_SKY = (86, 170, 235)
S_BLUE = (40, 90, 180)
S_GREEN = (70, 180, 90)
S_PURPLE = (150, 90, 200)
S_ORANGE = (245, 140, 40)
S_CORAL = (240, 110, 100)
S_WHITE = (252, 252, 250)
S_BLACK = (32, 32, 38)
S_GREY = (158, 160, 166)
S_NIGHT = (42, 50, 96)
S_SAND = (232, 206, 150)
S_SEA = (120, 190, 215)
S_SKIN = (232, 190, 150)
S_SKIN2 = (212, 168, 128)
S_FOREST = (28, 92, 48)
S_BROWN = (168, 106, 60)

# v5 grid rhythm: very light pastel cell tints (cream / mint / sky / butter)
TINTS = [(250, 247, 239), (235, 246, 238), (235, 243, 250), (250, 246, 228)]
ART_W, ART_H = 118, 48        # grid sticker drawing area (border adds ~15px)
FEAT_ART_W, FEAT_ART_H = 280, 72  # featured sticker drawing area
STICKER_BORDER = 10           # white silhouette extends 10px past the art

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
_font_cache = {}


def font(kind, size):
    key = (kind, size)
    if key not in _font_cache:
        name = {
            "serif": "DejaVuSerif-Bold.ttf",
            "sans": "DejaVuSans.ttf",
            "sansbold": "DejaVuSans-Bold.ttf",
            "mono": "DejaVuSansMono-Bold.ttf",
        }[kind]
        _font_cache[key] = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    return _font_cache[key]


# ----------------------------------------------------------------------
# Check machinery -- every guard increments the counter
# ----------------------------------------------------------------------

CHECKS = 0


def check(cond, label):
    global CHECKS
    if not cond:
        raise AssertionError("containment check failed: " + label)
    CHECKS += 1


def text_w(d, text, f):
    return d.textlength(text, font=f)


def wrap(d, text, f, max_w):
    """Word-wrap text to max_w; every produced line is width-checked."""
    lines = []
    cur = ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if text_w(d, trial, f) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            check(text_w(d, word, f) <= max_w, "single word fits: %r" % word)
            cur = word
    if cur:
        lines.append(cur)
    for ln in lines:
        check(text_w(d, ln, f) <= max_w, "wrapped line fits: %r" % ln)
    return lines


def put(d, x, y, text, f, fill, max_w, box_bottom, anchor="lt", label=""):
    """Place text with width + vertical containment checks."""
    w = text_w(d, text, f)
    check(w <= max_w, "text width %r (%.1f <= %d)" % (text, w, max_w))
    ascent, descent = f.getmetrics()
    if anchor == "mt":
        check(x - w / 2 >= MARGIN - 1 and x + w / 2 <= W - MARGIN + 1,
              "centered text inside page: %r" % text)
    else:
        check(x >= 0 and x + w <= W, "text inside page: %r" % text)
    check(y >= 0 and y + ascent + descent <= box_bottom,
          "text height %r (y=%d bottom=%d)" % (text, y, box_bottom))
    d.text((x, y), text, font=f, fill=fill, anchor=anchor)
    return w


def put_lines(d, x, y, lines, f, fill, lh, max_w, box_bottom, label=""):
    for i, ln in enumerate(lines):
        put(d, x, y + i * lh, ln, f, fill, max_w, box_bottom,
            label="%s line %d" % (label, i))
    return y + len(lines) * lh


def hrule(d, x0, x1, y, color=RULE, width=1):
    check(0 <= x0 < x1 <= W and 0 <= y < H, "hrule in page at y=%d" % y)
    d.line([(x0, y), (x1, y)], fill=color, width=width)


def vrule(d, x, y0, y1, color=RULE, width=1):
    check(0 <= x < W and 0 <= y0 < y1 <= H, "vrule in page at x=%d" % x)
    d.line([(x, y0), (x, y1)], fill=color, width=width)


def chip(d, x, y, text, color, max_w, ch=18):
    """Rounded accent chip with white uppercase mono text; returns width."""
    f = font("mono", 11)
    tw = text_w(d, text, f)
    cw = int(tw) + 14
    check(cw <= max_w, "chip fits column: %r" % text)
    check(x + cw <= W - MARGIN + 1, "chip inside page: %r" % text)
    d.rounded_rectangle([x, y, x + cw, y + ch], radius=ch // 2, fill=color)
    ascent, _ = f.getmetrics()
    ty = y + (ch - ascent) // 2
    check(ty >= y + 2 and ty + ascent <= y + ch - 2, "chip text padded: %r" % text)
    d.text((x + 7, ty), text, font=f, fill=(255, 255, 255))
    return cw


def accent_underline(d, x, y, w, color, style):
    """v5 accent underline under a grid headline; style varies per row."""
    check(style in ("solid", "dashed", "double"), "underline style: " + style)
    check(x >= 0 and x + w <= W and 0 <= y and y + 4 < H,
          "underline in page at y=%d" % y)
    if style == "solid":
        d.line([(x, y), (x + w, y)], fill=color, width=2)
    elif style == "dashed":
        for sx in range(x, x + w - 5, 10):
            d.line([(sx, y), (min(sx + 6, x + w), y)], fill=color, width=2)
    else:  # double
        d.line([(x, y - 1), (x + w, y - 1)], fill=color, width=1)
        d.line([(x, y + 2), (x + w, y + 2)], fill=color, width=1)


# ----------------------------------------------------------------------
# Doodle-sticker toolkit
# ----------------------------------------------------------------------

class Pen:
    """Thick-outlined marker drawing on a transparent sticker layer.

    All coordinates are local to the drawing area; (ox, oy) offsets them
    onto the padded layer so the white die-cut border has room to grow.
    """

    def __init__(self, ld, ox, oy, ow=5):
        self.d = ld
        self.ox = ox
        self.oy = oy
        self.ow = ow

    def P(self, pts):
        return [(self.ox + px, self.oy + py) for px, py in pts]

    def B(self, box):
        x0, y0, x1, y1 = box
        return [self.ox + x0, self.oy + y0, self.ox + x1, self.oy + y1]

    def line(self, pts, fill=OUTLINE, w=None, joint="curve"):
        self.d.line(self.P(pts), fill=fill, width=w or self.ow, joint=joint)

    def rect(self, box, fill, r=3, ow=None, outline=OUTLINE):
        self.d.rounded_rectangle(self.B(box), radius=r, fill=fill,
                                 outline=outline, width=ow or self.ow)

    def fillrect(self, box, fill):
        self.d.rectangle(self.B(box), fill=fill)

    def ellipse(self, box, fill, ow=None, outline=OUTLINE):
        self.d.ellipse(self.B(box), fill=fill, outline=outline,
                       width=ow or self.ow)

    def poly(self, pts, fill, ow=None, outline=OUTLINE):
        p = self.P(pts)
        self.d.polygon(p, fill=fill)
        self.d.line(p + [p[0]], fill=outline, width=ow or self.ow, joint="curve")

    def arc(self, box, a0, a1, fill=OUTLINE, w=None):
        self.d.arc(self.B(box), a0, a1, fill=fill, width=w or self.ow)

    def dot(self, cx, cy, r, fill=OUTLINE):
        self.d.ellipse([self.ox + cx - r, self.oy + cy - r,
                        self.ox + cx + r, self.oy + cy + r], fill=fill)

    def face(self, cx, cy, s, mood="happy", color=OUTLINE):
        """Small expressive face: dot eyes + a simple mouth."""
        ex = s * 0.44
        ey = cy - s * 0.18
        er = max(1.6, s * 0.16)
        lw = max(2, int(round(s * 0.17)))
        if mood == "sleepy":
            self.line([(cx - ex - er, ey), (cx - ex + er, ey)], color, lw)
            self.line([(cx + ex - er, ey), (cx + ex + er, ey)], color, lw)
        elif mood == "dizzy":
            for sx in (cx - ex, cx + ex):
                self.line([(sx - er, ey - er), (sx + er, ey + er)], color, lw)
                self.line([(sx - er, ey + er), (sx + er, ey - er)], color, lw)
        elif mood == "proud":
            self.arc([cx - ex - er, ey - er, cx - ex + er, ey + er], 200, 340, color, lw)
            self.arc([cx + ex - er, ey - er, cx + ex + er, ey + er], 200, 340, color, lw)
        else:
            self.dot(cx - ex, ey, er, color)
            self.dot(cx + ex, ey, er, color)
        my = cy + s * 0.30
        if mood in ("happy", "proud"):
            self.arc([cx - s * 0.34, my - s * 0.12, cx + s * 0.34, my + s * 0.34],
                     15, 165, color, lw)
        elif mood == "sad":
            self.arc([cx - s * 0.30, my, cx + s * 0.30, my + s * 0.42],
                     200, 340, color, lw)
        elif mood == "shock":
            self.ellipse([cx - s * 0.20, my, cx + s * 0.20, my + s * 0.36],
                         fill=None, ow=lw, outline=color)
        elif mood == "worry":
            self.line([(cx - s * 0.28, my + s * 0.10), (cx, my),
                       (cx + s * 0.28, my + s * 0.12)], color, lw)
        elif mood == "dizzy":
            self.line([(cx - s * 0.30, my), (cx - s * 0.10, my + s * 0.16),
                       (cx + s * 0.10, my), (cx + s * 0.30, my + s * 0.16)], color, lw)
        elif mood == "sleepy":
            self.ellipse([cx - s * 0.12, my, cx + s * 0.12, my + s * 0.22],
                         fill=None, ow=lw, outline=color)
        else:  # neutral
            self.line([(cx - s * 0.24, my + s * 0.08), (cx + s * 0.24, my + s * 0.08)],
                      color, lw)

    def sparkle(self, cx, cy, r, fill=S_YELLOW, w=2):
        self.line([(cx, cy - r), (cx, cy + r)], fill, w)
        self.line([(cx - r, cy), (cx + r, cy)], fill, w)
        rr = r * 0.55
        self.line([(cx - rr, cy - rr), (cx + rr, cy + rr)], fill, w)
        self.line([(cx - rr, cy + rr), (cx + rr, cy - rr)], fill, w)

    def dashes(self, x, y, dx, dy, n, fill=OUTLINE, w=3, ln=7, gap=5):
        mag = math.hypot(dx, dy) or 1.0
        ux, uy = dx / mag, dy / mag
        for i in range(n):
            sx = x + i * (ln + gap) * ux
            sy = y + i * (ln + gap) * uy
            self.line([(sx, sy), (sx + ln * ux, sy + ln * uy)], fill, w)

    def chk(self, cond, label):
        check(cond, label)


def doodle(d, x, y, w, h, scene, name, ow=5, border=STICKER_BORDER):
    """Render a doodle sticker: thick-outlined scene on a transparent
    layer, a pure-white die-cut silhouette (alpha dilated `border` px)
    behind it, composited onto the page so the drawing area lands at
    (x, y). Guards that the whole sticker stays inside the page."""
    pad = border + ow  # room for the outline stroke + the white border
    lw, lh = w + 2 * pad, h + 2 * pad
    layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    pen = Pen(ld, pad, pad, ow)
    scene(pen, w, h)
    alpha = layer.getchannel("A")
    dil = alpha.filter(ImageFilter.MaxFilter(2 * border + 1))
    sil = Image.new("RGBA", (lw, lh), (255, 255, 255, 255))
    sil.putalpha(dil)
    out = Image.alpha_composite(sil, layer)
    px, py = x - pad, y - pad
    check(0 <= px and 0 <= py and px + lw <= W and py + lh <= H,
          "sticker inside page: " + name)
    d._image.paste(out, (px, py), out)


# ----------------------------------------------------------------------
# Story data (all facts dated Friday 20 November 2026, per SPEC.md)
# ----------------------------------------------------------------------

TOP_LEFT = "ONE DAY OF WORLD NEWS"
TOP_RIGHT = ("32 STORIES \u00b7 7 REGIONS \u00b7 EVERY ONE DATED "
             "FRIDAY 20 NOVEMBER 2026")
MASTHEAD = "Friday 20 November 2026"

STATS = [
    ("111", "missiles + 404 drones", "fired at Ukraine"),
    ("3", "Kyiv bridges", "hit in mass strike"),
    ("\u22123.7%", "S&P 500 week;", "worst since 2020"),
    ("\u22126.2%", "Taiex,", "one day"),
    ("\u221214%", "Nvidia on SEC", "probe report"),
    ("372,000", "evacuated before", "Cyclone Akvan"),
]

FEATURED = [
    dict(tag="UKRAINE \u00b7 KYIV", color=RED, art="kyiv",
         head="Russia hits 3 Kyiv bridges in mass strike, killing at least 9",
         body="111 missiles and 404 drones fired; 7 dead in Kyiv, 2 in Lviv; "
              "power and water cut."),
    dict(tag="WORLD MARKETS", color=BLUE, art="chart",
         head="AI rout: S&P 500 sinks 3.7%, enters a correction",
         body="Nasdaq \u22125.3%, Taiex \u22126.2%, Nikkei \u22125.1%; world "
              "stocks' worst week since 2020."),
    dict(tag="INDIA \u00b7 ODISHA", color=TEAL, art="cyclone",
         head="Cyclone Akvan hits Odisha; no deaths reported",
         body="Landfall 02:00\u201303:00 UTC near Gopalpur; 70\u201380 km/h "
              "winds, 209 mm rain; 372,000 evacuated."),
]

MID = [
    dict(tag="US \u00b7 TECH", color=RED, art="nvidia",
         head="Nvidia sinks 14% on SEC probe report",
         body="Reuters: SEC staff examining its accounting."),
    dict(tag="T\u00dcRKIYE", color=AMBER, art="cop",
         head="COP31 runs into overtime, no deal",
         body="Draft omits fossil fuels; new text Saturday."),
    dict(tag="POLAND", color=BLUE, art="poland",
         head="Poland says 2 Russian missiles landed",
         body="A Kh-101 found by a forest; no one hurt."),
    dict(tag="BRUSSELS", color=BLUE, art="ukeu",
         head="UK and EU seal food, carbon, visa deals",
         body="100,000 youth visas; food checks eased."),
    dict(tag="HORMUZ", color=TEAL, art="hormuz",
         head="Tanker set ablaze off Oman near Hormuz",
         body="No casualties; Iran's Guards blame a mine."),
    dict(tag="INDIA", color=GREEN, art="indpak",
         head="Pakistani minister visits New Delhi",
         body="First visit since the May 2025 clash."),
    dict(tag="KENYA", color=AMBER, art="kenya",
         head="Kenya starts drilling for Turkana oil",
         body="First crude targeted for 1 December."),
    dict(tag="NEW ZEALAND", color=GREEN, art="rugby",
         head="New Zealand make 368 against India",
         body="Nicholls 175 not out, Phillips 118; India 159\u20131."),
    dict(tag="ARGENTINA", color=TEAL, art="arg",
         head="Argentina's country risk jumps to 1,070",
         body="Up 13%; first close over 1,000 in 13 months."),
    dict(tag="HEALTH", color=PURPLE, art="pill",
         head="Pancreatic cancer pill: 60.7% respond",
         body="Tumours shrink with chemo in 61 patients."),
]

ALSO = [
    "Lviv: rail station strike kills 2",
    "Estonia shuts Russian border",
    "CYGIL: general strike over budget",
    "Europe: shares' worst week in a year",
    "Gaza: strikes kill 6 despite truce",
    "Iraq: forces enter Jurf al-Sakhar",
    "Yemen: coalition strikes Hodeidah",
    "AfDB: 22 states near debt distress",
    "Sudan: army gains in West Kordofan",
    "Japan: core inflation 2.2%",
    "S. Korea: move to impeach top judge",
    "Bangladesh: arson; 124 held in Dhaka",
    "Myanmar: court ruling 'unfair'",
    "Australia: Xi hails 'full turnaround'",
    "Wall St: Anthropic \u22128.6%, still >$83",
    "US: floods spread north; 17+ in rain",
    "Fed's Cook calls for rate hikes now",
    "Mexico: Sheinbaum leads Victory parade",
    "Hunger Games prequel: $21.25m previews",
]
assert len(ALSO) == 19  # stories 14..32

DATE_CHECK_LABEL = ("DATE CHECK \u2014 left out on purpose, first reported "
                    "before Friday:")
DATE_CHECK_ITEMS = ("Trump\u2013Xi\u2013Putin Shenzhen talks (Thu 19) \u00b7 "
                    "ICJ Rohingya genocide ruling (Wed 18) \u00b7 "
                    "Denmark's Greenland vote (Thu 19)")
BOTTOM_LINE = ("Every story here happened on, or was first reported on, "
               "Friday 20 November 2026 \u00b7 Sources: AP, Reuters, AFP, "
               "BBC, IMF, UKMTO · original drawings")

# Map dots: (story number, x, y) in local map coordinates (470 x 136).
MAP_REGIONS = [
    ("EUROPE", BLUE, [(15, 262, 16), (6, 238, 32), (1, 290, 30),
                      (14, 262, 44), (7, 220, 48), (17, 238, 62),
                      (16, 280, 62), (5, 308, 52)]),
    ("MIDDLE EAST", AMBER, [(18, 314, 74), (19, 342, 60),
                            (20, 326, 102), (8, 366, 80)]),
    ("ASIA", TEAL, [(9, 330, 40), (3, 344, 88), (25, 374, 96),
                    (26, 398, 110), (23, 434, 36), (24, 408, 52)]),
    ("AMERICAS", RED, [(31, 72, 84), (29, 94, 56), (30, 122, 48),
                       (2, 136, 32), (28, 152, 58), (4, 44, 48),
                       (32, 36, 68), (12, 112, 124)]),
    ("AFRICA", GREEN, [(21, 230, 92), (22, 284, 84), (10, 298, 112)]),
    ("OCEANIA", PURPLE, [(27, 402, 124), (11, 440, 128)]),
]
MAP_COUNTS = {"EUROPE": 8, "MIDDLE EAST": 4, "ASIA": 6,
              "AMERICAS": 8, "AFRICA": 3, "OCEANIA": 2}


# ----------------------------------------------------------------------
# Featured doodle-sticker scenes (larger, ~72px drawing area)
# ----------------------------------------------------------------------

def art_kyiv(p, w, h):
    """Night-sky patch, worried moon, city, three cracked bridge arcs,
    missiles with motion streaks."""
    p.chk(w == FEAT_ART_W and h == FEAT_ART_H, "kyiv feat size")
    p.rect([3, 3, w - 3, h - 3], S_NIGHT, r=9)            # night sticker body
    # worried-face moon
    p.ellipse([16, 9, 46, 39], S_YELLOW)
    p.dot(26, 20, 2, (230, 180, 40))
    p.dot(38, 30, 2, (230, 180, 40))
    p.face(31, 24, 9, "worry")
    # stars / sparkles
    for sx, sy in [(66, 12), (120, 9), (176, 14), (232, 10)]:
        p.sparkle(sx, sy, 3, S_WHITE, 2)
    # city silhouette with lit windows
    base = 56
    for bx, bw, bh in [(58, 22, 22), (84, 16, 30), (104, 24, 18),
                       (132, 18, 28), (154, 22, 34), (180, 16, 20),
                       (200, 24, 26), (228, 18, 16), (250, 22, 24)]:
        p.rect([bx, base - bh, bx + bw, base], (16, 18, 32), r=2, ow=3)
        for wy in range(base - bh + 5, base - 4, 8):
            for wx in range(bx + 4, bx + bw - 3, 7):
                p.dot(wx, wy, 1, S_YELLOW)
    # river
    p.rect([3, 56, w - 3, h - 3], (52, 84, 146), r=4, ow=3)
    # three broken bridge arcs with crack marks
    for bx0, bx1 in [(20, 96), (108, 184), (196, 268)]:
        mid = (bx0 + bx1) // 2
        p.arc([bx0, 44, bx1, 72], 180, 360, S_WHITE, 4)
        p.line([(bx0, 58), (mid - 8, 58)], S_WHITE, 4)
        p.line([(mid + 8, 58), (bx1, 58)], S_WHITE, 4)
        p.line([(mid - 8, 58), (mid - 2, 66), (mid + 2, 58), (mid + 8, 66)],
               S_YELLOW, 3)  # crack zigzag
    # missiles with motion streaks (top right)
    for mx, my in [(206, 18), (238, 26)]:
        p.dashes(mx + 16, my - 12, -1, 1, 3, S_ORANGE, 3, 6, 4)
        p.poly([(mx, my), (mx + 12, my - 4), (mx + 10, my + 4)], S_RED, ow=3)
        p.line([(mx + 10, my), (mx + 20, my - 8)], S_ORANGE, 3)


def art_chart(p, w, h):
    """Panicked red chart sticker falling down a dotted slide, terrified
    coin stickers bouncing off."""
    p.chk(w == FEAT_ART_W and h == FEAT_ART_H, "chart feat size")
    # dotted slide
    for i in range(11):
        t = i / 10.0
        p.dot(36 + t * 200, 16 + t * 44, 2, S_GREY)
    # big tilted chart card (white) with a falling red line + panicked face
    card = [(104, 12), (206, 22), (198, 62), (96, 52)]
    p.poly(card, S_WHITE, ow=6)
    pts = [(112, 24), (130, 30), (146, 27), (162, 40), (178, 38), (192, 52)]
    p.line(pts, S_RED, 5)
    p.poly([(192, 52), (184, 48), (188, 58)], S_RED, ow=3)
    p.face(128, 44, 9, "shock")
    p.sparkle(210, 14, 4, S_YELLOW, 2)
    # terrified coins bouncing off
    for cx, cy, r in [(52, 50, 9), (78, 60, 8), (232, 52, 9)]:
        p.ellipse([cx - r, cy - r, cx + r, cy + r], S_YELLOW)
        p.face(cx, cy, r * 0.8, "shock")
        p.dashes(cx - r - 12, cy - 6, -1, 0, 2, S_GREY, 2, 5, 3)
    p.sparkle(40, 20, 4, S_SKY, 2)


def art_cyclone(p, w, h):
    """Grumpy spiral cloud spinning over a coastal village, evacuation
    bus fleeing."""
    p.chk(w == FEAT_ART_W and h == FEAT_ART_H, "cyclone feat size")
    # coastal village patch (bottom right)
    p.poly([(176, 50), (w - 3, 44), (w - 3, h - 3), (176, h - 3)], S_SAND, ow=5)
    for hx in (196, 222, 248):
        p.rect([hx, 54, hx + 16, 66], S_WHITE, r=2, ow=3)
        p.poly([(hx - 2, 54), (hx + 8, 46), (hx + 18, 54)], S_RED, ow=3)
    # grumpy spiral cloud sticker (top left / center)
    cx, cy = 86, 30
    p.ellipse([cx - 30, cy - 24, cx + 30, cy + 24], S_WHITE)
    for r, a0, a1 in [(22, 200, 540), (15, 160, 500), (8, 120, 460)]:
        p.arc([cx - r, cy - r, cx + r, cy + r], a0, a1, S_GREY, 4)
    p.face(cx, cy, 11, "sad")
    p.sparkle(cx - 34, cy - 20, 4, S_SKY, 2)
    # rain dashes under the cloud
    for rx, ry in [(40, 52), (60, 58), (120, 54), (140, 60)]:
        p.line([(rx, ry), (rx + 5, ry + 7)], S_SKY, 3)
    # evacuation bus fleeing right with motion dashes
    p.dashes(176, 58, -1, 0, 3, S_GREY, 3, 6, 4)
    p.rect([206, 50, 252, 64], S_YELLOW, r=4, ow=4)
    for wx in (212, 224, 236):
        p.rect([wx, 53, wx + 8, 59], S_SKY, r=1, ow=2)
    p.dot(216, 66, 3, S_BLACK)
    p.dot(242, 66, 3, S_BLACK)
    p.face(248, 57, 5, "worry")


FEATURED_ART = {"kyiv": art_kyiv, "chart": art_chart, "cyclone": art_cyclone}


# ----------------------------------------------------------------------
# Grid doodle-sticker scenes (ten, each ART_W x ART_H drawing area)
# ----------------------------------------------------------------------

def art_nvidia(p, w, h):
    """Panicked green candlestick chart with a shocked face, red
    magnifier looming."""
    p.line([(8, 43), (110, 43)], (120, 122, 128), 3)
    # two smaller candles, then a big panicked one hosting the face
    for cx, top, bot in [(12, 12, 28), (32, 18, 34)]:
        p.line([(cx + 6, top - 4), (cx + 6, bot + 3)], OUTLINE, 3)
        p.rect([cx, top, cx + 12, bot], S_GREEN, r=2, ow=4)
    p.line([(63, 16), (63, 44)], OUTLINE, 3)
    p.rect([52, 20, 74, 42], S_GREEN, r=3, ow=4)
    p.face(63, 31, 10, "shock")
    # red SEC magnifier looming over the last candle
    p.ellipse([80, 8, 106, 34], (255, 240, 240), ow=5, outline=S_RED)
    p.line([(102, 30), (113, 42)], S_RED, 5)
    p.chk(113 <= w and 42 <= h, "nvidia magnifier in scene")
    p.sparkle(78, 5, 3, S_YELLOW, 2)


def art_cop(p, w, h):
    """Sweating sad Earth with a band-aid and grey smoke puffs."""
    p.ellipse([20, 4, 64, 44], S_SKY)
    # land patches kept clear of the face (top-left and right edge)
    p.poly([(26, 12), (36, 9), (40, 16), (32, 21)], S_GREEN, ow=3)
    p.poly([(52, 30), (59, 28), (58, 38), (51, 37)], S_GREEN, ow=3)
    p.face(42, 28, 12, "sad")
    # band-aid across the top of the globe (above the eyes)
    p.poly([(28, 14), (50, 7), (55, 16), (33, 22)], S_SAND, ow=3)
    p.dot(40, 14, 1, (180, 150, 100))
    p.dot(46, 12, 1, (180, 150, 100))
    # sweat drop
    p.poly([(64, 10), (61, 17), (67, 17)], S_SKY, ow=2)
    p.dot(64, 18, 3, S_SKY)
    # grey smoke puffs drifting up-right
    for px, py, r in [(84, 14, 6), (96, 9, 5), (106, 15, 4)]:
        p.chk(px + r <= w and py - r >= 0, "cop puff in scene")
        p.ellipse([px - r, py - r, px + r, py + r], S_GREY, ow=3)


def art_poland(p, w, h):
    """Two sleepy missiles lying in a dark green forest patch."""
    p.rect([4, 34, 114, 44], S_FOREST, r=4, ow=4)
    for cx in (14, 30, 92, 108):
        p.poly([(cx, 12), (cx - 7, 34), (cx + 7, 34)], (36, 110, 58), ow=3)
    # two missiles lying horizontal, sleepy
    p.rect([18, 22, 58, 34], S_GREY, r=5, ow=4)
    p.poly([(58, 22), (70, 28), (58, 34)], S_RED, ow=3)
    p.poly([(18, 22), (12, 18), (18, 28)], S_GREY, ow=3)
    p.face(38, 28, 8, "sleepy")
    p.rect([62, 26, 98, 38], (184, 186, 192), r=5, ow=4)
    p.poly([(98, 26), (108, 32), (98, 38)], S_RED, ow=3)
    p.face(80, 32, 8, "sleepy")
    # zzz energy marks
    p.line([(48, 16), (54, 16), (48, 20), (54, 20)], OUTLINE, 2)
    p.line([(58, 10), (62, 10), (58, 13), (62, 13)], OUTLINE, 2)


def art_ukeu(p, w, h):
    """Handshake with tiny UK and EU flag badges."""
    # handshake: sleeves + clasped hands
    p.rect([8, 12, 38, 24], S_BLUE, r=3, ow=4)
    p.rect([80, 12, 110, 24], S_PURPLE, r=3, ow=4)
    p.rect([34, 10, 68, 26], S_SKIN, r=7, ow=4)
    p.rect([52, 12, 86, 24], S_SKIN2, r=7, ow=4)
    p.line([(52, 14), (60, 20)], (170, 130, 96), 2)
    p.sparkle(60, 5, 3, S_YELLOW, 2)
    # UK badge (simplified Union Jack)
    p.rect([14, 32, 46, 44], S_BLUE, r=2, ow=3)
    p.line([(30, 32), (30, 44)], S_WHITE, 3)
    p.line([(14, 38), (46, 38)], S_WHITE, 3)
    p.line([(30, 32), (30, 44)], S_RED, 1)
    p.line([(14, 38), (46, 38)], S_RED, 1)
    # EU badge (circle of stars)
    p.rect([72, 32, 104, 44], S_BLUE, r=2, ow=3)
    for k in range(8):
        a = k * math.pi / 4
        p.dot(88 + 7 * math.cos(a), 38 + 4 * math.sin(a), 1, S_YELLOW)
    p.chk(104 <= w and 44 <= h, "ukeu badges in scene")


def art_hormuz(p, w, h):
    """Alarmed black tanker with orange flames."""
    p.rect([4, 36, 114, 44], S_SEA, r=3, ow=3)
    hull = [(12, 28), (96, 28), (106, 36), (96, 42), (20, 42), (8, 36)]
    p.poly(hull, S_BLACK, ow=4)
    p.rect([80, 18, 94, 28], S_WHITE, r=2, ow=3)
    p.face(66, 35, 9, "shock", color=S_WHITE)
    # flames on deck (left of the face)
    p.poly([(28, 28), (34, 12), (40, 22), (46, 8), (52, 28)], S_ORANGE, ow=3)
    p.poly([(34, 28), (39, 18), (44, 24), (47, 16), (50, 28)], S_YELLOW, ow=2)
    for px, py, r in [(58, 8, 5), (70, 6, 4)]:
        p.chk(py - r >= 0 and px + r <= w, "hormuz smoke in scene")
        p.ellipse([px - r, py - r, px + r, py + r], S_GREY, ow=3)


def art_indpak(p, w, h):
    """Two cute flag badges facing off."""
    # Pakistan badge: green, crescent + star, cute face
    p.rect([10, 10, 52, 40], (1, 96, 44), r=5, ow=4)
    p.dot(26, 20, 7, S_WHITE)
    p.dot(29, 18, 6, (1, 96, 44))
    p.dot(38, 16, 2, S_WHITE)
    p.face(31, 31, 8, "happy", color=S_WHITE)
    # India badge: saffron / white / green, chakra, cute face
    p.rect([66, 10, 108, 40], S_WHITE, r=5, ow=4)
    p.rect([66, 10, 108, 20], S_ORANGE, r=3, ow=3)
    p.rect([66, 30, 108, 40], S_GREEN, r=3, ow=3)
    p.ellipse([83, 21, 91, 29], fill=None, ow=2, outline=S_BLUE)
    p.face(87, 34, 8, "happy")
    # versus energy marks between
    p.line([(57, 18), (61, 22), (57, 26)], S_YELLOW, 2)
    p.sparkle(59, 33, 3, S_YELLOW, 2)
    p.chk(108 <= w and 40 <= h, "indpak badges in scene")


def art_kenya(p, w, h):
    """Proud oil derrick with a smiling black droplet."""
    p.rect([4, 38, 114, 44], S_SAND, r=3, ow=3)
    # derrick triangle with cross braces, personified proud
    p.poly([(30, 6), (12, 38), (48, 38)], (120, 90, 60), ow=4)
    p.line([(21, 22), (39, 22)], OUTLINE, 2)
    p.line([(17, 30), (43, 30)], OUTLINE, 2)
    p.face(30, 27, 7, "proud", color=S_WHITE)
    # smiling black oil droplet
    p.poly([(84, 12), (76, 28), (92, 28)], S_BLACK, ow=4)
    p.ellipse([74, 24, 94, 42], S_BLACK, ow=4)
    p.face(84, 33, 9, "happy", color=S_WHITE)
    p.sparkle(102, 12, 4, S_YELLOW, 2)
    p.chk(94 <= w and 42 <= h, "kenya droplet in scene")


def art_rugby(p, w, h):
    """Flying rugby ball with motion dashes and a happy face."""
    cx, cy, rx, ry, ang = 64, 24, 21, 12, -20 * math.pi / 180
    pts = []
    for k in range(28):
        t = k * math.pi / 14
        ex, ey = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + ex * math.cos(ang) - ey * math.sin(ang),
                    cy + ex * math.sin(ang) + ey * math.cos(ang)))
    p.chk(all(0 <= px <= w and 0 <= py <= h for px, py in pts),
          "rugby ball in scene")
    p.poly(pts, S_BROWN, ow=5)
    p.line([(cx - 12 * math.cos(ang), cy - 12 * math.sin(ang)),
            (cx + 12 * math.cos(ang), cy + 12 * math.sin(ang))], S_WHITE, 2)
    for t in (-5, 0, 5):
        lx = cx + t * math.cos(ang)
        ly = cy + t * math.sin(ang)
        p.line([(lx - 2 * math.sin(ang), ly + 2 * math.cos(ang)),
                (lx + 2 * math.sin(ang), ly - 2 * math.cos(ang))], S_WHITE, 2)
    p.face(cx, cy, 9, "happy", color=S_WHITE)
    # motion dashes behind the ball
    p.dashes(10, 16, 1, 0, 2, S_GREY, 3, 7, 4)
    p.dashes(8, 26, 1, 0, 2, S_GREY, 3, 7, 4)
    p.sparkle(98, 10, 4, S_YELLOW, 2)
    p.sparkle(102, 36, 3, S_SKY, 2)


def art_arg(p, w, h):
    """Dizzy rising red line with a blue sun badge."""
    # flag-blue sun badge (Sol de Mayo) with a dizzy face
    sx, sy, r = 24, 16, 10
    for k in range(8):
        a = k * math.pi / 4
        p.line([(sx + (r + 1) * math.cos(a), sy + (r + 1) * math.sin(a)),
                (sx + (r + 4) * math.cos(a), sy + (r + 4) * math.sin(a))],
               S_SKY, 3)
    p.ellipse([sx - r, sy - r, sx + r, sy + r], S_SKY, ow=4)
    p.face(sx, sy, 8, "dizzy")
    # steep rising risk line with arrowhead
    pts = [(14, 42), (34, 38), (52, 30), (72, 22), (92, 12), (104, 8)]
    p.line(pts, S_RED, 5)
    p.poly([(110, 5), (100, 7), (106, 15)], S_RED, ow=3)
    p.chk(110 <= w and 5 >= 0, "arg arrow in scene")
    p.sparkle(96, 20, 3, S_YELLOW, 2)


def art_pill(p, w, h):
    """Smiling capsule pill (half coral half white) with sparkles."""
    p.rect([30, 16, 88, 38], S_WHITE, r=11, ow=5)
    p.rect([30, 16, 59, 38], S_CORAL, r=11, ow=5)
    p.fillrect([48, 16, 59, 38], S_CORAL)
    p.line([(59, 16), (59, 38)], OUTLINE, 3)
    p.face(73, 27, 9, "happy")
    p.chk(88 <= w and 38 <= h, "pill capsule in scene")
    for cx, cy, col in [(18, 12, S_YELLOW), (100, 12, S_GREEN),
                        (16, 38, S_GREEN), (102, 38, S_YELLOW), (59, 6, S_YELLOW)]:
        p.chk(0 <= cx - 4 and cx + 4 <= w and 0 <= cy - 4 and cy + 4 <= h,
              "pill sparkle in scene at %d,%d" % (cx, cy))
        p.sparkle(cx, cy, 4, col, 2)


MID_ART = {"nvidia": art_nvidia, "cop": art_cop, "poland": art_poland,
           "ukeu": art_ukeu, "hormuz": art_hormuz, "indpak": art_indpak,
           "kenya": art_kenya, "rugby": art_rugby, "arg": art_arg,
           "pill": art_pill}


# ----------------------------------------------------------------------
# Section builders
# ----------------------------------------------------------------------

def top_bar(d):
    y = 14
    fl = font("mono", 12)
    fr = font("sans", 11)
    wl = put(d, MARGIN, y + 2, TOP_LEFT, fl, INK, 300, 40, label="top-left")
    wr = text_w(d, TOP_RIGHT, fr)
    check(wl + wr + 24 <= CONTENT_W, "top bar texts do not collide")
    put(d, W - MARGIN - wr, y + 4, TOP_RIGHT, fr, RULE, wr + 1, 40,
        label="top-right")
    hrule(d, MARGIN, W - MARGIN, 40)
    return 40


def masthead(d, y0):
    size = 66
    while size > 40:
        f = font("serif", size)
        ascent, descent = f.getmetrics()
        if (text_w(d, MASTHEAD, f) <= CONTENT_W - 32
                and ascent + descent <= 58):
            break
        size -= 2
    f = font("serif", size)
    ascent, descent = f.getmetrics()
    check(ascent + descent <= 58, "masthead height budget")
    put(d, W // 2, y0 + 4, MASTHEAD, f, INK, CONTENT_W - 32, y0 + 76,
        anchor="mt", label="masthead")
    ry = y0 + 4 + ascent + descent + 4
    check(ry + 4 <= y0 + 84, "masthead rules within budget")
    hrule(d, MARGIN, W - MARGIN, ry, INK, 2)
    hrule(d, MARGIN, W - MARGIN, ry + 4, INK, 1)
    return ry + 4


def numbers_strip(d, y0):
    f_head = font("mono", 12)
    head = "THE DAY IN NUMBERS"
    hw = text_w(d, head, f_head)
    hx = W // 2 - hw / 2
    put(d, W // 2, y0, head, f_head, INK, CONTENT_W, y0 + 16,
        anchor="mt", label="numbers header")
    hrule(d, MARGIN, hx - 12, y0 + 7, RULE)
    hrule(d, hx + hw + 12, W - MARGIN, y0 + 7, RULE)
    cell_top, cell_bot = y0 + 18, y0 + 80
    f_num = font("mono", 22)
    f_lab = font("sans", 11)
    na, nd = f_num.getmetrics()
    for i, (num, l1, l2) in enumerate(STATS):
        x0 = MARGIN + round(i * CONTENT_W / 6)
        x1 = MARGIN + round((i + 1) * CONTENT_W / 6)
        cw = x1 - x0
        cx = (x0 + x1) / 2
        if i > 0:
            vrule(d, x0, cell_top + 4, cell_bot - 4, RULE)
        nw = text_w(d, num, f_num)
        check(nw <= cw - 16, "stat number fits cell: %s" % num)
        put(d, cx, cell_top + 4, num, f_num, INK, cw - 16, cell_top + 4 + na + nd,
            anchor="mt", label="stat " + num)
        ly = cell_top + 4 + na + nd + 4
        for j, lab in enumerate((l1, l2)):
            lw = text_w(d, lab, f_lab)
            check(lw <= cw - 12, "stat label fits cell: %r" % lab)
            put(d, cx, ly + j * 13, lab, f_lab, RULE, cw - 12, cell_bot,
                anchor="mt", label="stat label")
        check(ly + 26 <= cell_bot, "stat cell vertical budget: %s" % num)
    hrule(d, MARGIN, W - MARGIN, cell_bot + 6)
    return cell_bot + 6


def featured_row(d, y0):
    gap = 16
    colw = (CONTENT_W - 2 * gap) // 3  # 320
    bottom_limit = y0 + 200
    inset = (colw - FEAT_ART_W) // 2
    for i, st in enumerate(FEATURED):
        x = MARGIN + i * (colw + gap)
        inner = colw - 16
        doodle(d, x + inset, y0 + 14, FEAT_ART_W, FEAT_ART_H,
               FEATURED_ART[st["art"]], "feat-" + st["art"], ow=6)
        check(y0 + 14 + FEAT_ART_H + STICKER_BORDER + 6 <= bottom_limit,
              "featured art budget")
        cy = y0 + 104
        chip(d, x, cy, st["tag"], st["color"], inner)
        hs = 17
        while hs > 14:
            lines = wrap(d, st["head"], font("serif", hs), inner)
            if len(lines) <= 2:
                break
            hs -= 1
        hf = font("serif", hs)
        lines = wrap(d, st["head"], hf, inner)
        check(len(lines) <= 2, "featured headline <= 2 lines: %r" % st["head"])
        hy = cy + 22
        hend = put_lines(d, x, hy, lines, hf, INK, hs + 3, inner,
                         bottom_limit, label="featured head")
        bf = font("sans", 12)
        blines = wrap(d, st["body"], bf, inner)
        check(len(blines) <= 2, "featured body <= 2 lines: %r" % st["body"])
        bend = put_lines(d, x, hend + 4, blines, bf, RULE, 14, inner,
                         bottom_limit, label="featured body")
        check(bend <= bottom_limit, "featured column fits: %s" % st["tag"])
    hrule(d, MARGIN, W - MARGIN, bottom_limit + 6)
    return bottom_limit + 6


def mid_grid(d, y0):
    """v5: ten doodle-sticker cells with varied tint / offset / underline."""
    hgap, vgap = 10, 8
    colw = (CONTENT_W - 4 * hgap) // 5  # 190
    rowh = 170
    inner = colw - 8
    hf = font("serif", 14)
    bf = font("sans", 11)
    row_styles = ["solid", "dashed"]  # different accent underline per row
    prev_side = None
    for i, st in enumerate(MID):
        r, c = divmod(i, 5)
        x = MARGIN + c * (colw + hgap)
        y = y0 + r * (rowh + vgap)
        cell_bot = y + rowh
        # rhythm 1: light pastel tint, cycling cream / mint / sky / butter
        tint = TINTS[i % 4]
        check(tint in TINTS, "grid tint from palette: %s" % st["tag"])
        d.rectangle([x, y, x + colw, y + rowh], fill=tint)
        # rhythm 2: sticker offset left vs right between neighbors
        side = (r + c) % 2
        if prev_side is not None:
            check(side != prev_side, "grid art offset alternates: %s" % st["tag"])
        prev_side = side
        pad = STICKER_BORDER + 5
        ax = x + 8 + pad if side == 0 else x + colw - 8 - pad - ART_W
        check(ax - pad >= x + 4 and ax + ART_W + pad <= x + colw - 4,
              "grid sticker padded in cell: %s" % st["tag"])
        art_top = y + 15
        check(art_top - pad >= y, "grid sticker top inside cell: %s" % st["tag"])
        doodle(d, ax, art_top, ART_W, ART_H, MID_ART[st["art"]],
               "grid-" + st["art"], ow=5)
        check(art_top + ART_H + pad <= y + 82, "grid art height budget: %s" % st["tag"])
        # chip, headline, accent underline, body
        chip(d, x + 4, y + 82, st["tag"], st["color"], inner, ch=16)
        lines = wrap(d, st["head"], hf, inner)
        check(len(lines) <= 2, "mid headline <= 2 lines: %r" % st["head"])
        hend = put_lines(d, x + 4, y + 102, lines, hf, INK, 16, inner,
                         cell_bot, label="mid head")
        check(hend <= y + 137, "mid headline above underline: %s" % st["tag"])
        accent_underline(d, x + 4, y + 138, inner, st["color"], row_styles[r])
        blines = wrap(d, st["body"], bf, inner)
        check(len(blines) <= 2, "mid body <= 2 lines: %r" % st["body"])
        bend = put_lines(d, x + 4, y + 142, blines, bf, RULE, 13, inner,
                         cell_bot, label="mid body")
        check(bend <= cell_bot - 2, "mid cell fits: %s" % st["tag"])
    # rhythm 3: double rule separating the two rows (solid/dashed under heads)
    sep_y = y0 + rowh + vgap // 2
    hrule(d, MARGIN, W - MARGIN, sep_y - 2, FAINT, 1)
    hrule(d, MARGIN, W - MARGIN, sep_y + 1, FAINT, 1)
    check(sep_y + 1 < y0 + rowh + vgap, "row separator clear of row 2")
    end = y0 + 2 * rowh + vgap
    hrule(d, MARGIN, W - MARGIN, end + 6)
    return end + 6


def world_map(d, x, y, w, h):
    """Dot-cluster world map with numbered, color-coded story dots."""
    d.rectangle([x, y, x + w, y + h], outline=FAINT, width=1)
    for gx in range(1, 6):
        vrule(d, x + round(gx * w / 6), y + 1, y + h - 1, FAINT)
    for gy in range(1, 4):
        hrule(d, x + 1, x + w - 1, y + round(gy * h / 4), FAINT)
    f_num = font("mono", 11)
    na, _ = f_num.getmetrics()
    r = 4
    dots = []   # (cx, cy, num, color, numbox)
    for name, color, pts in MAP_REGIONS:
        check(len(pts) == MAP_COUNTS[name], "map count " + name)
        for num, dx, dy in pts:
            cx, cy = x + dx, y + dy
            check(x + r <= cx <= x + w - r and y + r <= cy <= y + h - r,
                  "dot inside map: %d" % num)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
            label = str(num)
            tw = text_w(d, label, f_num)
            nx, ny = cx + r + 3, cy - na // 2 - 1
            nbox = (nx, ny, nx + tw, ny + na)
            check(nbox[2] <= x + w - 2 and nbox[1] >= y + 1 and nbox[3] <= y + h - 1,
                  "dot number inside map: %d" % num)
            d.text((nx, ny), label, font=f_num, fill=INK)
            dots.append((cx, cy, num, color, nbox))
    # pairwise containment: dots and number boxes must never overlap
    def rect_circle_hit(box, cx, cy, rr):
        rx = max(box[0], min(cx, box[2]))
        ry = max(box[1], min(cy, box[3]))
        return (rx - cx) ** 2 + (ry - cy) ** 2 < rr * rr

    def rect_hit(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    for i in range(len(dots)):
        for j in range(i + 1, len(dots)):
            ax, ay, an, _, abox = dots[i]
            bx, by, bn, _, bbox = dots[j]
            dist2 = (ax - bx) ** 2 + (ay - by) ** 2
            check(dist2 >= (2 * r + 4) ** 2,
                  "dots %d/%d spaced (%.1fpx)" % (an, bn, math.sqrt(dist2)))
            check(not rect_circle_hit(abox, bx, by, r + 1),
                  "number %d clear of dot %d" % (an, bn))
            check(not rect_circle_hit(bbox, ax, ay, r + 1),
                  "number %d clear of dot %d" % (bn, an))
            check(not rect_hit(abox, bbox),
                  "numbers %d/%d do not overlap" % (an, bn))
    return dots


def bottom_section(d, y0):
    left_w = 470
    div_x = MARGIN + left_w + 10
    right_x = div_x + 10
    right_w = W - MARGIN - right_x
    sec_bot = y0 + 180
    fh = font("mono", 13)
    # left: map
    put(d, MARGIN, y0, "WHERE IT HAPPENED", fh, INK, left_w, y0 + 18,
        label="map header")
    map_y, map_h = y0 + 22, 136
    world_map(d, MARGIN, map_y, left_w, map_h)
    # legend: one row of six color-coded region entries
    fl = font("sans", 11)
    ly = map_y + map_h + 6
    lx = MARGIN
    for name, color, pts in MAP_REGIONS:
        d.rectangle([lx, ly + 2, lx + 8, ly + 10], fill=color)
        label = "%s %d" % (name, len(pts))
        lw = text_w(d, label, fl)
        check(lx + 12 + lw <= div_x - 6, "legend item fits: %s" % name)
        put(d, lx + 12, ly, label, fl, RULE, lw + 1, sec_bot, label="legend")
        lx += 12 + lw + 6
    check(lx - 6 <= div_x - 6, "legend row fits left column")
    check(ly + 14 <= sec_bot, "legend vertical budget")
    vrule(d, div_x, y0, sec_bot - 4, RULE)
    # right: numbered also-list, two columns (14..23, 24..32)
    put(d, right_x, y0, "ALSO ON FRIDAY 20 NOVEMBER", fh, INK, right_w,
        y0 + 18, label="also header")
    sub_gap = 14
    sub_w = (right_w - sub_gap) // 2
    fn = font("mono", 11)
    ft = font("sans", 11)
    list_y = y0 + 22
    for col, (start, items) in enumerate([(14, ALSO[:10]), (24, ALSO[10:])]):
        sx = right_x + col * (sub_w + sub_gap)
        yy = list_y
        for k, item in enumerate(items):
            num = str(start + k)
            nw = text_w(d, num, fn)
            tx = sx + nw + 5
            avail = sub_w - nw - 5
            lines = wrap(d, item, ft, avail)
            check(len(lines) <= 2, "also item <= 2 lines: %r" % item)
            put(d, sx, yy, num, fn, INK, nw + 1, sec_bot, label="also num")
            yy = put_lines(d, tx, yy, lines, ft, RULE, 13, avail, sec_bot,
                           label="also item")
            yy += 2
        check(yy - 2 <= sec_bot, "also column fits: col %d" % col)
    return sec_bot


def footer(d, y0):
    box_bot = y0 + 40
    d.rectangle([MARGIN, y0, W - MARGIN, box_bot], outline=RULE, width=1)
    fl = font("mono", 11)
    fb = font("sans", 11)
    put(d, MARGIN + 8, y0 + 6, DATE_CHECK_LABEL, fl, RED, CONTENT_W - 16,
        y0 + 20, label="date check label")
    put(d, MARGIN + 8, y0 + 22, DATE_CHECK_ITEMS, fb, RULE, CONTENT_W - 16,
        box_bot - 4, label="date check items")
    fbot = font("sans", 11)
    bw = text_w(d, BOTTOM_LINE, fbot)
    check(bw <= CONTENT_W, "bottom line fits page")
    put(d, W // 2, box_bot + 6, BOTTOM_LINE, fbot, RULE, CONTENT_W,
        H - 4, anchor="mt", label="bottom line")
    return box_bot + 6


# ----------------------------------------------------------------------
# Main render
# ----------------------------------------------------------------------

def render(path):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    y = top_bar(d)                      # -> 40
    y = masthead(d, y + 4)
    check(y <= 118, "masthead section budget")
    y = numbers_strip(d, y + 4)
    check(y <= 208, "numbers section budget")
    y = featured_row(d, y + 4)
    check(y <= 418, "featured section budget")
    y = mid_grid(d, y + 4)
    check(y <= 778, "mid grid section budget")
    y = bottom_section(d, y + 3)
    check(y <= 960, "bottom section budget")
    y = footer(d, y + 3)
    check(y <= H - 4, "footer within page")

    img.save(path, optimize=True)

    # verify the written artifact with PIL
    with Image.open(path) as im:
        check(im.size == (1024, 1024), "output is 1024x1024")
        check(im.mode == "RGB", "output mode RGB")
    nbytes = os.path.getsize(path)
    check(nbytes < 900 * 1024, "PNG under 900 KB")
    check(CHECKS >= 50, "at least 50 containment checks ran")
    print("%d text/illustration containment checks passed" % CHECKS)
    print("entry.png: 1024x1024, %d bytes (%.1f KB)" % (nbytes, nbytes / 1024))
    return CHECKS


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    render(os.path.join(here, "entry.png"))
