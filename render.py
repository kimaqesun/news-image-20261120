#!/usr/bin/env python3
"""Render the v3 "ONE DAY OF WORLD NEWS" newspaper front page.

Implements SPEC.md (design spec v3) from scratch: a dense, warm-cream
newspaper/infographic front page covering 32 stories, all dated Friday
20 November 2026. Pure PIL, fully deterministic -- no network, no
randomness, no clock reads. Output: entry.png, 1024x1024, under 900 KB.

Every text placement and every drawn box is guarded by an internal
containment check; the run aborts on the first violation and prints a
summary count when all checks pass.
"""

import math
import os

from PIL import Image, ImageDraw, ImageFont

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


def chip(d, x, y, text, color, max_w):
    """Rounded accent chip with white uppercase mono text; returns width."""
    f = font("mono", 11)
    tw = text_w(d, text, f)
    cw = int(tw) + 14
    ch = 18
    check(cw <= max_w, "chip fits column: %r" % text)
    check(x + cw <= W - MARGIN + 1, "chip inside page: %r" % text)
    d.rounded_rectangle([x, y, x + cw, y + ch], radius=9, fill=color)
    ascent, _ = f.getmetrics()
    ty = y + (ch - ascent) // 2
    check(ty >= y + 2 and ty + ascent <= y + ch - 2, "chip text padded: %r" % text)
    d.text((x + 7, ty), text, font=f, fill=(255, 255, 255))
    return cw


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
    dict(tag="US \u00b7 TECH", color=RED, icon="chip",
         head="Nvidia sinks 14% on SEC probe report",
         body="Reuters: SEC staff examining its accounting."),
    dict(tag="T\u00dcRKIYE", color=AMBER, icon="globe",
         head="COP31 runs into overtime, no deal",
         body="Draft omits fossil fuels; new text Saturday."),
    dict(tag="POLAND", color=BLUE, icon="missile",
         head="Poland says 2 Russian missiles landed",
         body="A Kh-101 found by a forest; no one hurt."),
    dict(tag="BRUSSELS", color=BLUE, icon="stars",
         head="UK and EU seal food, carbon, visa deals",
         body="100,000 youth visas; food checks eased."),
    dict(tag="HORMUZ", color=TEAL, icon="flame",
         head="Tanker set ablaze off Oman near Hormuz",
         body="No casualties; Iran's Guards blame a mine."),
    dict(tag="INDIA", color=GREEN, icon="handshake",
         head="Pakistani minister visits New Delhi",
         body="First visit since the May 2025 clash."),
    dict(tag="KENYA", color=AMBER, icon="derrick",
         head="Kenya starts drilling for Turkana oil",
         body="First crude targeted for 1 December."),
    dict(tag="NEW ZEALAND", color=GREEN, icon="ball",
         head="New Zealand make 368 against India",
         body="Nicholls 175 not out, Phillips 118; India 159\u20131."),
    dict(tag="ARGENTINA", color=TEAL, icon="arrow",
         head="Argentina's country risk jumps to 1,070",
         body="Up 13%; first close over 1,000 in 13 months."),
    dict(tag="HEALTH", color=PURPLE, icon="pill",
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

# Map dots: (story number, x, y) in local map coordinates.
MAP_REGIONS = [
    ("EUROPE", BLUE, [(15, 262, 18), (6, 240, 34), (1, 288, 32),
                      (14, 264, 44), (7, 222, 48), (17, 238, 64),
                      (16, 278, 66), (5, 306, 56)]),
    ("MIDDLE EAST", AMBER, [(18, 312, 78), (19, 340, 66),
                            (20, 324, 110), (8, 364, 84)]),
    ("ASIA", TEAL, [(9, 330, 46), (3, 342, 96), (25, 372, 104),
                    (26, 396, 118), (23, 432, 44), (24, 410, 56)]),
    ("AMERICAS", RED, [(31, 72, 92), (29, 92, 60), (30, 120, 52),
                       (2, 134, 40), (28, 150, 62), (4, 44, 52),
                       (32, 36, 74), (12, 112, 142)]),
    ("AFRICA", GREEN, [(21, 228, 98), (22, 282, 88), (10, 296, 116)]),
    ("OCEANIA", PURPLE, [(27, 398, 132), (11, 438, 150)]),
]
MAP_COUNTS = {"EUROPE": 8, "MIDDLE EAST": 4, "ASIA": 6,
              "AMERICAS": 8, "AFRICA": 3, "OCEANIA": 2}


# ----------------------------------------------------------------------
# Illustrations (flat vector shapes, pure PIL)
# ----------------------------------------------------------------------

def art_kyiv(d, x, y, w, h):
    """Night skyline, river, three broken bridge spans, missile streaks."""
    check(h == 90, "kyiv art height")
    d.rectangle([x, y, x + w, y + h], fill=(24, 32, 62))
    # deterministic stars
    for sx, sy in [(30, 12), (80, 8), (150, 16), (210, 10), (262, 14), (296, 8)]:
        d.rectangle([x + sx, y + sy, x + sx + 1, y + sy + 1], fill=(240, 238, 225))
    # skyline silhouettes
    base = y + 62
    for bx, bw, bh in [(8, 26, 30), (40, 18, 44), (64, 30, 24), (100, 20, 38),
                       (126, 26, 50), (158, 18, 28), (182, 28, 40), (216, 20, 22),
                       (242, 26, 46), (274, 30, 30)]:
        d.rectangle([x + bx, base - bh, x + bx + bw, base], fill=(14, 16, 26))
        for wy in range(base - bh + 5, base - 4, 9):
            for wx in range(x + bx + 4, x + bx + bw - 3, 8):
                d.rectangle([wx, wy, wx + 2, wy + 3], fill=(212, 175, 90))
    # river
    d.rectangle([x, y + 62, x + w, y + h], fill=(38, 66, 118))
    for rx in range(10, w - 20, 46):
        d.line([(x + rx, y + 72), (x + rx + 22, y + 72)], fill=(70, 100, 156), width=1)
        d.line([(x + rx + 12, y + 82), (x + rx + 34, y + 82)], fill=(70, 100, 156), width=1)
    # three broken bridge spans across the river
    deck_y = y + 66
    for bx0, bx1 in [(14, 104), (118, 208), (222, 306)]:
        gap0 = bx0 + (bx1 - bx0) // 2 - 7
        gap1 = gap0 + 14
        d.line([(x + bx0, deck_y), (x + gap0, deck_y)], fill=(200, 198, 188), width=3)
        d.line([(x + gap1, deck_y), (x + bx1, deck_y)], fill=(200, 198, 188), width=3)
        # fallen span pieces tilting into the water
        d.line([(x + gap0, deck_y), (x + gap0 + 9, deck_y + 12)],
               fill=(200, 198, 188), width=3)
        d.line([(x + gap1, deck_y), (x + gap1 - 6, deck_y + 9)],
               fill=(160, 158, 150), width=2)
        for px in (bx0 + 6, bx1 - 6):
            d.line([(x + px, deck_y), (x + px, deck_y + 16)],
                   fill=(150, 148, 140), width=2)
    # missile streaks with heads
    for mx, my, ln in [(250, 6, 40), (282, 14, 34), (222, 4, 30)]:
        x0, y0 = x + mx, y + my
        x1, y1 = x0 - ln, y0 + ln
        d.line([(x0, y0), (x1, y1)], fill=(232, 170, 60), width=2)
        d.polygon([(x1, y1), (x1 + 7, y1 - 2), (x1 + 2, y1 - 7)], fill=RED)


def art_chart(d, x, y, w, h):
    """Falling red line chart with axis ticks."""
    check(h == 90, "chart art height")
    d.rectangle([x, y, x + w, y + h], fill=(252, 250, 243))
    ax_l, ax_b = x + 26, y + h - 16
    ax_t, ax_r = y + 8, x + w - 12
    for gy in range(ax_t + 8, ax_b, 16):
        d.line([(ax_l, gy), (ax_r, gy)], fill=FAINT, width=1)
    d.line([(ax_l, ax_t), (ax_l, ax_b)], fill=INK, width=2)
    d.line([(ax_l, ax_b), (ax_r, ax_b)], fill=INK, width=2)
    for ty in range(ax_t + 8, ax_b, 16):
        d.line([(ax_l - 4, ty), (ax_l, ty)], fill=INK, width=1)
    for tx in range(ax_l + 24, ax_r, 48):
        d.line([(tx, ax_b), (tx, ax_b + 4)], fill=INK, width=1)
    pts = [(0.0, 0.18), (0.14, 0.30), (0.26, 0.24), (0.40, 0.52),
           (0.52, 0.46), (0.66, 0.72), (0.80, 0.66), (1.0, 0.95)]
    px = [(ax_l + 6 + p[0] * (ax_r - ax_l - 14),
           ax_t + 4 + p[1] * (ax_b - ax_t - 10)) for p in pts]
    for i in range(len(px) - 1):
        d.line([px[i], px[i + 1]], fill=RED, width=3)
    ex, ey = px[-1]
    d.polygon([(ex + 1, ey + 1), (ex - 8, ey - 3), (ex - 2, ey - 9)], fill=RED)
    d.ellipse([px[0][0] - 3, px[0][1] - 3, px[0][0] + 3, px[0][1] + 3], fill=BLUE)


def art_cyclone(d, x, y, w, h):
    """Coastline, spiral cyclone symbol, red dashed landfall arrow."""
    check(h == 90, "cyclone art height")
    d.rectangle([x, y, x + w, y + h], fill=(168, 214, 210))
    # land mass on the right with a ragged coastline
    coast = [(x + w, y), (x + 238, y), (x + 226, y + 18), (x + 238, y + 34),
             (x + 220, y + 52), (x + 232, y + 68), (x + 218, y + h), (x + w, y + h)]
    d.polygon(coast, fill=(224, 206, 168))
    d.line(coast[1:-1], fill=(150, 128, 86), width=2)
    # spiral cyclone symbol over the sea
    cx, cy = x + 110, y + 44
    for r, a0, a1 in [(27, 200, 540), (20, 160, 500), (13, 120, 460), (7, 80, 420)]:
        d.arc([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=(0, 86, 88), width=3)
    d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(0, 86, 88))
    # red dashed landfall arrow toward the coast near Gopalpur
    sx, sy, ex, ey = x + 160, y + 74, x + 228, y + 54
    n = 6
    for i in range(n):
        t0, t1 = i / n, (i + 0.55) / n
        d.line([(sx + (ex - sx) * t0, sy + (ey - sy) * t0),
                (sx + (ex - sx) * t1, sy + (ey - sy) * t1)], fill=RED, width=2)
    d.polygon([(ex + 4, ey - 1), (ex - 6, ey - 6), (ex - 4, ey + 5)], fill=RED)
    d.ellipse([ex - 2, ey - 2, ex + 2, ey + 2], fill=RED)
    # rain bands
    for rx, ry in [(30, 12), (52, 70), (150, 16), (180, 78)]:
        d.line([(x + rx, y + ry), (x + rx + 8, y + ry + 5)], fill=(90, 150, 150), width=2)


ART_FUNCS = {"kyiv": art_kyiv, "chart": art_chart, "cyclone": art_cyclone}


def draw_icon(d, x, y, kind, color):
    """18x18 accent icon square with a flat white glyph."""
    s = 18
    d.rounded_rectangle([x, y, x + s, y + s], radius=4, fill=color)
    wh = (255, 255, 255)
    if kind == "chip":  # falling mini chart
        d.line([(x + 4, y + 6), (x + 8, y + 9), (x + 11, y + 8), (x + 14, y + 13)],
               fill=wh, width=2)
    elif kind == "globe":
        d.ellipse([x + 4, y + 4, x + 14, y + 14], outline=wh, width=2)
        d.line([(x + 4, y + 9), (x + 14, y + 9)], fill=wh, width=1)
    elif kind == "missile":
        d.line([(x + 4, y + 13), (x + 12, y + 5)], fill=wh, width=2)
        d.polygon([(x + 14, y + 3), (x + 10, y + 5), (x + 13, y + 8)], fill=wh)
    elif kind == "stars":
        for ox, oy in [(6, 5), (11, 8), (6, 11)]:
            d.ellipse([x + ox, y + oy, x + ox + 3, y + oy + 3], fill=wh)
    elif kind == "flame":
        d.polygon([(x + 9, y + 3), (x + 13, y + 10), (x + 9, y + 14),
                   (x + 5, y + 10)], fill=wh)
    elif kind == "handshake":
        d.ellipse([x + 3, y + 6, x + 10, y + 13], outline=wh, width=2)
        d.ellipse([x + 8, y + 6, x + 15, y + 13], outline=wh, width=2)
    elif kind == "derrick":
        d.polygon([(x + 9, y + 3), (x + 13, y + 14), (x + 5, y + 14)], outline=wh)
        d.line([(x + 6, y + 10), (x + 12, y + 10)], fill=wh, width=1)
    elif kind == "ball":
        d.ellipse([x + 4, y + 4, x + 14, y + 14], outline=wh, width=2)
        d.arc([x + 5, y + 5, x + 13, y + 13], 300, 120, fill=wh, width=1)
    elif kind == "arrow":
        d.line([(x + 5, y + 13), (x + 12, y + 6)], fill=wh, width=2)
        d.polygon([(x + 14, y + 4), (x + 9, y + 5), (x + 13, y + 9)], fill=wh)
    elif kind == "pill":
        d.rounded_rectangle([x + 3, y + 7, x + 15, y + 12], radius=3, fill=wh)
        d.line([(x + 9, y + 7), (x + 9, y + 12)], fill=color, width=1)
    else:
        raise AssertionError("unknown icon " + kind)
    check(x + s <= W and y + s <= H, "icon in page: " + kind)


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
    while size > 40 and text_w(d, MASTHEAD, font("serif", size)) > CONTENT_W - 32:
        size -= 2
    f = font("serif", size)
    ascent, descent = f.getmetrics()
    check(ascent + descent <= 84, "masthead height budget")
    put(d, W // 2, y0 + 4, MASTHEAD, f, INK, CONTENT_W - 32, y0 + 88,
        anchor="mt", label="masthead")
    ry = y0 + 4 + ascent + descent + 4
    check(ry + 4 <= 140, "masthead rules within budget")
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
    cell_top, cell_bot = y0 + 20, y0 + 102
    f_num = font("mono", 24)
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
        ly = cell_top + 4 + na + nd + 6
        for j, lab in enumerate((l1, l2)):
            lw = text_w(d, lab, f_lab)
            check(lw <= cw - 12, "stat label fits cell: %r" % lab)
            put(d, cx, ly + j * 14, lab, f_lab, RULE, cw - 12, cell_bot,
                anchor="mt", label="stat label")
        check(ly + 28 <= cell_bot, "stat cell vertical budget: %s" % num)
    hrule(d, MARGIN, W - MARGIN, cell_bot + 8)
    return cell_bot + 8


def featured_row(d, y0):
    gap = 16
    colw = (CONTENT_W - 2 * gap) // 3  # 320
    bottom_limit = y0 + 212
    for i, st in enumerate(FEATURED):
        x = MARGIN + i * (colw + gap)
        inner = colw - 16
        ART_FUNCS[st["art"]](d, x, y0, colw, 90)
        check(y0 + 90 <= bottom_limit, "featured art budget")
        cy = y0 + 98
        chip(d, x, cy, st["tag"], st["color"], inner)
        # headline: largest serif size that wraps to <= 2 lines
        hs = 18
        while hs > 14:
            lines = wrap(d, st["head"], font("serif", hs), inner)
            if len(lines) <= 2:
                break
            hs -= 1
        hf = font("serif", hs)
        lines = wrap(d, st["head"], hf, inner)
        check(len(lines) <= 2, "featured headline <= 2 lines: %r" % st["head"])
        hy = cy + 26
        hend = put_lines(d, x, hy, lines, hf, INK, hs + 5, inner,
                         bottom_limit, label="featured head")
        bf = font("sans", 12)
        blines = wrap(d, st["body"], bf, inner)
        check(len(blines) <= 2, "featured body <= 2 lines: %r" % st["body"])
        bend = put_lines(d, x, hend + 6, blines, bf, RULE, 16, inner,
                         bottom_limit, label="featured body")
        check(bend <= bottom_limit, "featured column fits: %s" % st["tag"])
    hrule(d, MARGIN, W - MARGIN, bottom_limit + 8)
    return bottom_limit + 8


def mid_grid(d, y0):
    gap = 12
    colw = (CONTENT_W - 4 * gap) // 5  # 188
    rowh = 106
    inner = colw - 8
    hf = font("serif", 14)
    bf = font("sans", 11)
    for i, st in enumerate(MID):
        r, c = divmod(i, 5)
        x = MARGIN + c * (colw + gap)
        y = y0 + r * (rowh + gap)
        cell_bot = y + rowh
        draw_icon(d, x, y, st["icon"], st["color"])
        cw = chip(d, x + 24, y, st["tag"], st["color"], inner - 24)
        check(24 + cw <= colw, "icon+chip row fits: %s" % st["tag"])
        lines = wrap(d, st["head"], hf, inner)
        check(len(lines) <= 3, "mid headline <= 3 lines: %r" % st["head"])
        hend = put_lines(d, x + 1, y + 24, lines, hf, INK, 17, inner,
                         cell_bot, label="mid head")
        blines = wrap(d, st["body"], bf, inner)
        check(len(blines) <= 2, "mid body <= 2 lines: %r" % st["body"])
        bend = put_lines(d, x + 1, hend + 4, blines, bf, RULE, 14, inner,
                         cell_bot, label="mid body")
        check(bend <= cell_bot, "mid cell fits: %s" % st["tag"])
    end = y0 + 2 * rowh + gap
    hrule(d, MARGIN, W - MARGIN, end + 8)
    return end + 8


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
    sec_bot = y0 + 224
    fh = font("mono", 13)
    # left: map
    put(d, MARGIN, y0, "WHERE IT HAPPENED", fh, INK, left_w, y0 + 18,
        label="map header")
    map_y, map_h = y0 + 24, 160
    world_map(d, MARGIN, map_y, left_w, map_h)
    # legend: two rows of three color-coded region entries
    fl = font("sans", 11)
    ly0 = map_y + map_h + 8
    lx = MARGIN
    for i, (name, color, pts) in enumerate(MAP_REGIONS):
        row, col = divmod(i, 3)
        if col == 0:
            lx = MARGIN
        ly = ly0 + row * 16
        d.rectangle([lx, ly + 2, lx + 8, ly + 10], fill=color)
        label = "%s %d" % (name, len(pts))
        lw = text_w(d, label, fl)
        check(lx + 12 + lw <= div_x - 6, "legend item fits: %s" % name)
        put(d, lx + 12, ly, label, fl, RULE, lw + 1, sec_bot, label="legend")
        lx += 12 + lw + 12
    check(ly0 + 16 + 14 <= sec_bot, "legend vertical budget")
    vrule(d, div_x, y0, sec_bot - 4, RULE)
    # right: numbered also-list, two columns (14..23, 24..32)
    put(d, right_x, y0, "ALSO ON FRIDAY 20 NOVEMBER", fh, INK, right_w,
        y0 + 18, label="also header")
    sub_gap = 14
    sub_w = (right_w - sub_gap) // 2
    fn = font("mono", 11)
    ft = font("sans", 11)
    list_y = y0 + 24
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
            yy += 3
        check(yy - 3 <= sec_bot, "also column fits: col %d" % col)
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
    y = masthead(d, y + 6)              # double rule ~134
    check(y <= 140, "masthead section budget")
    y = numbers_strip(d, y + 8)         # header + cells + rule
    check(y <= 254, "numbers section budget")
    y = featured_row(d, y + 8)
    check(y <= 482, "featured section budget")
    y = mid_grid(d, y + 8)
    check(y <= 722, "mid grid section budget")
    y = bottom_section(d, y + 8)
    check(y <= 954, "bottom section budget")
    y = footer(d, y + 4)
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