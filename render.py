#!/usr/bin/env python3
"""Render the v6 "ONE DAY OF WORLD NEWS" photo-card front page.

Implements SPEC.md section "v6 -- photo-card redesign (current directive)",
which overrides the older cream-newspaper / doodle-sticker layout sections:
a dark tech-theme news-aggregator card grid (background (10, 14, 26)) built
from the 13 shipped, pre-cropped, watermark-free photos in photos/*.jpg.

- Header: small caps "ONE DAY OF WORLD NEWS", huge white serif date, thin rule.
- THE DAY IN NUMBERS strip on dark: white mono numbers, red/blue accents.
- 3 featured cards: photo fills the top ~55% of the card, dark gradient
  scrim over the photo bottom, colored tag chip at the card's top-left,
  white bold serif headline + 2-line light-grey body under the photo.
- 10 grid cards: same treatment, photo ~40% of card height, pastel-tinted
  cream body area below with dark ink text for legibility.
- WHERE IT HAPPENED dot map, ALSO ON FRIDAY list (14-32) and DATE CHECK
  footer kept, restyled dark with white text.
- Cards: 16px rounded corners, 1px light-grey borders on dark. Text never
  sits on a busy photo area without the scrim (only the solid chip does).

Pure PIL, fully deterministic -- no network, no randomness, no clock reads.
Every text placement, photo paste and drawn box is guarded by an internal
containment check; the run aborts on the first violation and prints a
summary count when all checks pass. Output: entry.png, 1024x1024, < 900 KB.
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

BG = (10, 14, 26)            # v6 dark tech background
CARD_BG = (17, 22, 38)       # featured card body panel
PANEL = (16, 21, 36)         # map / date-check panel
BORDER = (96, 102, 120)      # 1px light-grey card border on dark
RULE_D = (58, 64, 82)        # dark-theme rule lines
MAP_GRID = (40, 46, 64)      # faint map graticule

WHITE = (245, 247, 252)      # headlines / headers on dark
LIGHT = (198, 204, 218)      # featured body text on dark
ALSO_TEXT = (214, 219, 230)  # also-list / date-check text on dark
MUTED = (160, 167, 184)      # labels / footer on dark

INK = (25, 25, 30)           # dark ink on the cream grid-card bodies
GRID_BODY = (66, 70, 82)     # grid body text on cream

# Section accent colors (chip fills, white uppercase text on top).
RED = (200, 40, 40)
BLUE = (25, 80, 160)
TEAL = (0, 120, 120)
AMBER = (200, 130, 20)
GREEN = (40, 120, 60)
PURPLE = (110, 50, 140)

# Brightened accents for dots / numbers / accents on the dark background.
BRED = (235, 96, 96)
BBLUE = (100, 152, 235)
BTEAL = (45, 190, 190)
BAMBER = (235, 172, 64)
BGREEN = (96, 192, 116)
BPURPLE = (172, 124, 222)

# v6 grid-card body tints: pastel cream family, dark ink text on top.
TINTS = [(249, 246, 238), (236, 246, 239), (236, 243, 250), (250, 246, 229)]

CARD_R = 16                  # card corner radius (px)
FEAT_W, FEAT_H = 320, 200    # featured card size
FEAT_PHOTO_H = 110           # ~55% of the featured card
GRID_W, GRID_H = 190, 170    # grid card size
GRID_PHOTO_H = 68            # ~40% of the grid card

PHOTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos")
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


def hrule(d, x0, x1, y, color=RULE_D, width=1):
    check(0 <= x0 < x1 <= W and 0 <= y < H, "hrule in page at y=%d" % y)
    d.line([(x0, y), (x1, y)], fill=color, width=width)


def vrule(d, x, y0, y1, color=RULE_D, width=1):
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


# ----------------------------------------------------------------------
# Photo-card toolkit: crop-to-fill, rounded top corners, gradient scrim
# ----------------------------------------------------------------------

def load_photo(name, pw, ph):
    """Open a shipped photo and center-crop-to-fill exactly (pw, ph)."""
    path = os.path.join(PHOTO_DIR, name)
    check(os.path.isfile(path), "photo file exists: " + name)
    with Image.open(path) as im:
        im = im.convert("RGB")
        sw, sh = im.size
        check(sw >= pw and sh >= ph, "photo large enough to fill: " + name)
        scale = max(pw / sw, ph / sh)
        rw = max(pw, math.ceil(sw * scale))
        rh = max(ph, math.ceil(sh * scale))
        im = im.resize((rw, rh), Image.Resampling.LANCZOS)
        left = (rw - pw) // 2
        top = (rh - ph) // 2
        im = im.crop((left, top, left + pw, top + ph))
    check(im.size == (pw, ph), "photo crop-to-fill size: " + name)
    return im


def top_round_mask(pw, ph, r):
    """Opaque mask with the TOP two corners rounded (bottom stays square
    because the rounded rect's bottom corners fall outside the mask)."""
    check(0 < r <= min(pw, ph) // 2, "mask radius sane: %d" % r)
    mask = Image.new("L", (pw, ph), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, pw - 1, ph - 1 + r], radius=r, fill=255)
    check(mask.size == (pw, ph), "mask matches photo area")
    return mask


def apply_scrim(photo, scrim_h, max_alpha, color):
    """Dark gradient scrim over the bottom scrim_h rows of the photo:
    alpha ramps linearly 0 -> max_alpha so the panel below blends in."""
    pw, ph = photo.size
    check(0 < scrim_h <= ph, "scrim height inside photo: %d <= %d" % (scrim_h, ph))
    check(0 <= max_alpha <= 255, "scrim alpha sane: %d" % max_alpha)
    overlay = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(scrim_h):
        y = ph - scrim_h + i
        a = round(max_alpha * (i + 1) / scrim_h)
        od.line([(0, y), (pw - 1, y)], fill=color + (a,))
    out = Image.alpha_composite(photo.convert("RGBA"), overlay).convert("RGB")
    check(out.size == (pw, ph), "scrim keeps photo size")
    return out


def draw_card(d, x, y, cw, ch, fill, name):
    """Rounded card base; the border is stroked after the photo paste."""
    check(x >= MARGIN and y >= 0 and x + cw <= W - MARGIN and y + ch <= H,
          "card inside page: " + name)
    d.rounded_rectangle([x, y, x + cw - 1, y + ch - 1], radius=CARD_R, fill=fill)


def card_photo(d, x, y, cw, ch, photo_h, name, scrim_h, max_alpha, scrim_color):
    """Paste the crop-to-fill photo into the card top with rounded top
    corners and a gradient scrim, then stroke the 1px light-grey border."""
    check(photo_h < ch, "photo leaves a body area: " + name)
    check(y + photo_h <= y + ch - 20, "photo top within card: " + name)
    photo = load_photo(name, cw, photo_h)
    photo = apply_scrim(photo, scrim_h, max_alpha, scrim_color)
    mask = top_round_mask(cw, photo_h, CARD_R)
    d._image.paste(photo, (x, y), mask)
    d.rounded_rectangle([x, y, x + cw - 1, y + ch - 1], radius=CARD_R,
                        outline=BORDER, width=1)


def card_chip(d, x, y, cw, photo_h, st, ch=18, pad=10):
    """Solid accent chip at the card's top-left, on the photo. A solid
    chip is the only thing allowed to sit on the photo without scrim."""
    cw_chip = chip(d, x + pad, y + pad, st["tag"], st["color"], cw - 2 * pad, ch=ch)
    check(y + pad + ch <= y + photo_h - 6, "chip stays on photo: %s" % st["tag"])
    check(x + pad + cw_chip <= x + cw - pad, "chip padded in card: %s" % st["tag"])
    return cw_chip


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
    dict(tag="UKRAINE \u00b7 KYIV", color=RED, photo="kyiv.jpg",
         head="Russia hits 3 Kyiv bridges in mass strike, killing at least 9",
         body="111 missiles and 404 drones fired; 7 dead in Kyiv, 2 in Lviv; "
              "power and water cut."),
    dict(tag="WORLD MARKETS", color=BLUE, photo="markets.jpg",
         head="AI rout: S&P 500 sinks 3.7%, enters a correction",
         body="Nasdaq \u22125.3%, Taiex \u22126.2%, Nikkei \u22125.1%; world "
              "stocks' worst week since 2020."),
    dict(tag="INDIA \u00b7 ODISHA", color=TEAL, photo="cyclone.jpg",
         head="Cyclone Akvan hits Odisha; no deaths reported",
         body="Landfall 02:00\u201303:00 UTC near Gopalpur; 70\u201380 km/h "
              "winds, 209 mm rain; 372,000 evacuated."),
]

MID = [
    dict(tag="US \u00b7 TECH", color=RED, photo="nvidia.jpg",
         head="Nvidia sinks 14% on SEC probe report",
         body="Reuters: SEC staff examining its accounting."),
    dict(tag="T\u00dcRKIYE", color=AMBER, photo="cop31.jpg",
         head="COP31 runs into overtime, no deal",
         body="Draft omits fossil fuels; new text Saturday."),
    dict(tag="POLAND", color=BLUE, photo="poland.jpg",
         head="Poland says 2 Russian missiles landed",
         body="A Kh-101 found by a forest; no one hurt."),
    dict(tag="BRUSSELS", color=BLUE, photo="ukeu.jpg",
         head="UK and EU seal food, carbon, visa deals",
         body="100,000 youth visas; food checks eased."),
    dict(tag="HORMUZ", color=TEAL, photo="hormuz.jpg",
         head="Tanker set ablaze off Oman near Hormuz",
         body="No casualties; Iran's Guards blame a mine."),
    dict(tag="INDIA", color=GREEN, photo="indiapk.jpg",
         head="Pakistani minister visits New Delhi",
         body="First visit since the May 2025 clash."),
    dict(tag="KENYA", color=AMBER, photo="kenya.jpg",
         head="Kenya starts drilling for Turkana oil",
         body="First crude targeted for 1 December."),
    dict(tag="NEW ZEALAND", color=GREEN, photo="nz.jpg",
         head="New Zealand make 368 against India",
         body="Nicholls 175 not out, Phillips 118; India 159\u20131."),
    dict(tag="ARGENTINA", color=TEAL, photo="argentina.jpg",
         head="Argentina's country risk jumps to 1,070",
         body="Up 13%; first close over 1,000 in 13 months."),
    dict(tag="HEALTH", color=PURPLE, photo="health.jpg",
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
               "BBC, IMF, UKMTO \u00b7 news photos")

# v6.1 map: each dot is a real-world location (story number, latitude,
# longitude in degrees).  Positions are projected onto the shipped dark world
# map with the equirectangular math below, so the dots land on the right
# continents.  Closely clustered stories are spread a few degrees so their
# numbered markers never collide; longitudes/latitudes stay inside the same
# continent.  Brightened accent colors for the dark panel.
MAP_REGIONS = [
    ("EUROPE", BBLUE, [(15, 53.01, 26.54), (6, 53.01, 17.59),
                       (1, 50.05, 34.76), (14, 45.75, 23.20),
                       (7, 51.38, 1.54), (17, 48.91, 10.00),
                       (16, 34.59, 31.54), (5, 42.39, 32.65)]),
    ("MIDDLE EAST", BAMBER, [(18, 27.93, 36.22), (19, 32.80, 44.10),
                             (20, 15.70, 43.63), (8, 26.20, 56.30)]),
    ("ASIA", BTEAL, [(9, 28.61, 77.21), (3, 18.83, 84.41),
                     (25, 24.76, 90.33), (26, 19.23, 96.70),
                     (23, 35.68, 139.69), (24, 37.57, 126.98)]),
    ("AMERICAS", BRED, [(31, 19.43, -99.13), (29, 39.00, -93.00),
                        (30, 34.02, -83.98), (2, 40.19, -78.49),
                        (28, 47.29, -64.04), (4, 38.50, -123.25),
                        (32, 32.90, -116.95), (12, -34.60, -58.38),
                        (13, 41.18, -69.61)]),
    ("AFRICA", BGREEN, [(21, 9.27, 38.55), (22, 12.00, 29.00),
                        (10, 1.85, 35.51)]),
    ("OCEANIA", BPURPLE, [(27, -35.12, 138.00), (11, -35.12, 174.78)]),
]
MAP_COUNTS = {"EUROPE": 8, "MIDDLE EAST": 4, "ASIA": 6,
              "AMERICAS": 9, "AFRICA": 3, "OCEANIA": 2}

# Equirectangular projection of photos/worldmap_dark.png (1280 x 567,
# transparent oceans).  The source spans roughly 176W..195E and 85N..60S.
WORLD_MAP_PNG = "worldmap_dark.png"
MAP_LON_MIN, MAP_LON_MAX = -176.0, 195.0
MAP_LAT_TOP, MAP_LAT_BOT = 85.0, -60.0
MAP_CENTER_LAT = 9.0       # latitude at the vertical center of the panel crop
MAP_PAD_X = 5              # left/right padding inside the panel


# ----------------------------------------------------------------------
# Sections
# ----------------------------------------------------------------------

def top_bar(d):
    y = 14
    fl = font("mono", 12)
    fr = font("sans", 11)
    wl = put(d, MARGIN, y + 2, TOP_LEFT, fl, WHITE, 300, 40, label="top-left")
    wr = text_w(d, TOP_RIGHT, fr)
    check(wl + wr + 24 <= CONTENT_W, "top bar texts do not collide")
    put(d, W - MARGIN - wr, y + 4, TOP_RIGHT, fr, MUTED, wr + 1, 40,
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
    put(d, W // 2, y0 + 4, MASTHEAD, f, WHITE, CONTENT_W - 32, y0 + 76,
        anchor="mt", label="masthead")
    ry = y0 + 4 + ascent + descent + 4
    check(ry + 4 <= y0 + 84, "masthead rule within budget")
    hrule(d, MARGIN, W - MARGIN, ry, BORDER, 1)  # thin rule under the date
    return ry + 4


def numbers_strip(d, y0):
    f_head = font("mono", 12)
    head = "THE DAY IN NUMBERS"
    hw = text_w(d, head, f_head)
    hx = W // 2 - hw / 2
    put(d, W // 2, y0, head, f_head, BBLUE, CONTENT_W, y0 + 16,
        anchor="mt", label="numbers header")
    hrule(d, MARGIN, hx - 12, y0 + 7, RULE_D)
    hrule(d, hx + hw + 12, W - MARGIN, y0 + 7, RULE_D)
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
            vrule(d, x0, cell_top + 4, cell_bot - 4, RULE_D)
        # red / blue accent tick above each white mono number
        accent = BRED if i % 2 == 0 else BBLUE
        bar_w = 28
        check(cx - bar_w / 2 >= x0 + 4 and cx + bar_w / 2 <= x1 - 4,
              "stat accent tick inside cell: %s" % num)
        d.rectangle([cx - bar_w / 2, cell_top, cx + bar_w / 2, cell_top + 2],
                    fill=accent)
        nw = text_w(d, num, f_num)
        check(nw <= cw - 16, "stat number fits cell: %s" % num)
        put(d, cx, cell_top + 6, num, f_num, WHITE, cw - 16,
            cell_top + 6 + na + nd, anchor="mt", label="stat " + num)
        ly = cell_top + 6 + na + nd + 2
        for j, lab in enumerate((l1, l2)):
            lw = text_w(d, lab, f_lab)
            check(lw <= cw - 12, "stat label fits cell: %r" % lab)
            put(d, cx, ly + j * 13, lab, f_lab, MUTED, cw - 12, cell_bot,
                anchor="mt", label="stat label")
        check(ly + 26 <= cell_bot, "stat cell vertical budget: %s" % num)
    hrule(d, MARGIN, W - MARGIN, cell_bot + 6)
    return cell_bot + 6


def featured_row(d, y0):
    """Three photo cards: photo ~55% top, scrim, chip, white serif head,
    2-line light-grey body on the dark card panel below the photo."""
    gap = 16
    colw = (CONTENT_W - 2 * gap) // 3  # 320
    check(colw == FEAT_W, "featured card width")
    check(FEAT_PHOTO_H == round(0.55 * FEAT_H), "featured photo ~55% of card")
    bottom_limit = y0 + FEAT_H
    inner = colw - 20
    for i, st in enumerate(FEATURED):
        x = MARGIN + i * (colw + gap)
        draw_card(d, x, y0, colw, FEAT_H, CARD_BG, "feat-" + st["photo"])
        card_photo(d, x, y0, colw, FEAT_H, FEAT_PHOTO_H, st["photo"],
                   scrim_h=55, max_alpha=205, scrim_color=CARD_BG)
        card_chip(d, x, y0, colw, FEAT_PHOTO_H, st, ch=18, pad=10)
        # headline + body live strictly BELOW the photo (never on it)
        text_top = y0 + FEAT_PHOTO_H + 8
        check(text_top >= y0 + FEAT_PHOTO_H, "featured text off photo: %s" % st["tag"])
        hs = 17
        while hs > 14:
            lines = wrap(d, st["head"], font("serif", hs), inner)
            if len(lines) <= 2:
                break
            hs -= 1
        hf = font("serif", hs)
        lines = wrap(d, st["head"], hf, inner)
        check(len(lines) <= 2, "featured headline <= 2 lines: %r" % st["head"])
        hend = put_lines(d, x + 10, text_top, lines, hf, WHITE, hs + 3, inner,
                         bottom_limit - 8, label="featured head")
        bf = font("sans", 12)
        blines = wrap(d, st["body"], bf, inner)
        check(len(blines) <= 2, "featured body <= 2 lines: %r" % st["body"])
        bend = put_lines(d, x + 10, hend + 3, blines, bf, LIGHT, 15, inner,
                         bottom_limit - 8, label="featured body")
        check(bend <= bottom_limit - 8, "featured card fits: %s" % st["tag"])
    return bottom_limit + 6


def mid_grid(d, y0):
    """Ten photo cards, 5 x 2: photo ~40% top with scrim + chip, pastel
    cream body below with dark ink headline and body text."""
    hgap, vgap = 10, 8
    colw = (CONTENT_W - 4 * hgap) // 5  # 190
    check(colw == GRID_W, "grid card width")
    check(GRID_PHOTO_H == round(0.40 * GRID_H), "grid photo ~40% of card")
    inner = colw - 16
    hf = font("serif", 14)
    bf = font("sans", 11)
    for i, st in enumerate(MID):
        r, c = divmod(i, 5)
        x = MARGIN + c * (colw + hgap)
        y = y0 + r * (GRID_H + vgap)
        cell_bot = y + GRID_H
        tint = TINTS[i % 4]
        check(tint in TINTS, "grid tint from palette: %s" % st["tag"])
        draw_card(d, x, y, colw, GRID_H, tint, "grid-" + st["photo"])
        card_photo(d, x, y, colw, GRID_H, GRID_PHOTO_H, st["photo"],
                   scrim_h=30, max_alpha=165, scrim_color=BG)
        card_chip(d, x, y, colw, GRID_PHOTO_H, st, ch=16, pad=8)
        text_top = y + GRID_PHOTO_H + 8
        check(text_top >= y + GRID_PHOTO_H, "grid text off photo: %s" % st["tag"])
        lines = wrap(d, st["head"], hf, inner)
        check(len(lines) <= 2, "mid headline <= 2 lines: %r" % st["head"])
        hend = put_lines(d, x + 8, text_top, lines, hf, INK, 17, inner,
                         cell_bot - 6, label="mid head")
        blines = wrap(d, st["body"], bf, inner)
        check(len(blines) <= 2, "mid body <= 2 lines: %r" % st["body"])
        bend = put_lines(d, x + 8, hend + 3, blines, bf, GRID_BODY, 13, inner,
                         cell_bot - 6, label="mid body")
        check(bend <= cell_bot - 6, "mid card fits: %s" % st["tag"])
    end = y0 + 2 * GRID_H + vgap
    check(end + 6 <= H, "grid section inside page")
    return end + 6


def world_map_geometry(panel_w, panel_h):
    """Aspect-preserving map geometry for the panel.

    The dark map is scaled to fill the panel width (460 px, 1280x567 source)
    keeping its aspect, then a panel-height band is cropped from it.  Return
    the scaled size, crop row and the equirectangular latitude window that
    band represents, so dots can be projected into exactly the same pixels.
    """
    map_w = panel_w - 2 * MAP_PAD_X
    check(map_w > 0, "world map has positive width")
    map_h = round(map_w * 567 / 1280)
    full_span = MAP_LAT_TOP - MAP_LAT_BOT
    span = full_span * panel_h / map_h
    target_top = MAP_CENTER_LAT + span / 2
    crop_top = round((MAP_LAT_TOP - target_top) / full_span * map_h)
    check(0 <= crop_top and crop_top + panel_h <= map_h,
          "world map crop inside scaled image")
    lat_top = MAP_LAT_TOP - crop_top / map_h * full_span
    return map_w, map_h, crop_top, lat_top, span


def load_world_map(map_w, map_h, crop_top, crop_h):
    """Load the dark world-map asset, scale it to (map_w, map_h) keeping its
    aspect, and crop the panel band.  Transparent oceans stay transparent."""
    path = os.path.join(PHOTO_DIR, WORLD_MAP_PNG)
    check(os.path.isfile(path), "world map asset exists")
    with Image.open(path) as im:
        im = im.convert("RGBA")
        sw, sh = im.size
        check((sw, sh) == (1280, 567), "world map source is 1280x567")
        check(map_h == round(map_w * sh / sw), "world map keeps aspect")
        scaled = im.resize((map_w, map_h), Image.Resampling.LANCZOS)
    band = scaled.crop((0, crop_top, map_w, crop_top + crop_h))
    check(band.size == (map_w, crop_h), "world map band size")
    return band


def project_latlon(lat, lon, lat_top, span, map_w, panel_h):
    """Equirectangular projection of a (lat, lon) onto the map band.

    Longitude maps linearly across the full image width; latitude maps
    linearly across the cropped band.  Return offsets from the map's top-left.
    Latitudes just outside the cropped band (the far north/south) are clamped
    to the panel so their numbered dots stay inside it.
    """
    fx = (lon - MAP_LON_MIN) / (MAP_LON_MAX - MAP_LON_MIN)
    fy = (lat_top - lat) / span
    check(-0.08 <= fx <= 1.08 and -0.08 <= fy <= 1.08,
          "lat/lon near map: %.2f,%.2f" % (lat, lon))
    mx = min(map_w - 6, max(6, fx * map_w))
    my = min(panel_h - 6, max(6, fy * panel_h))
    return mx, my


def world_map(d, x, y, w, h):
    """WHERE IT HAPPENED panel.

    v6.1: composite the real dark world map behind the dots (scaled to the
    panel width, aspect preserved), then draw the panel frame, graticule,
    numbered dots and legend on TOP of the map.  Dot coordinates come from
    real lat/lon via an equirectangular projection, so they sit on the right
    continents.
    """
    panel = (x, y, x + w, y + h)
    d.rectangle(panel, fill=PANEL)

    mw, mh, crop_top, lat_top, span = world_map_geometry(w, h)
    band = load_world_map(mw, mh, crop_top, h)
    d._image.paste(band, (x + MAP_PAD_X, y), band)
    check(band.size == (mw, h), "world map composited at panel width")

    d.rectangle(panel, outline=BORDER, width=1)
    for gx in range(1, 6):
        vrule(d, x + round(gx * w / 6), y + 1, y + h - 1, MAP_GRID)
    for gy in range(1, 4):
        hrule(d, x + 1, x + w - 1, y + round(gy * h / 4), MAP_GRID)

    f_num = font("mono", 11)
    na, _ = f_num.getmetrics()
    r = 3
    circles = []  # (cx, cy, num)
    for name, color, pts in MAP_REGIONS:
        check(len(pts) == MAP_COUNTS[name], "map count " + name)
        for num, lat, lon in pts:
            mx, my = project_latlon(lat, lon, lat_top, span, mw, h)
            cx, cy = x + MAP_PAD_X + mx, y + my
            check(x + r <= cx <= x + w - r and y + r <= cy <= y + h - r,
                  "dot inside map: %d" % num)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
            circles.append((cx, cy, num, color))

    # Pairwise circle containment: dots never touch or overlap.
    for i in range(len(circles)):
        for j in range(i + 1, len(circles)):
            ax, ay, an, _ = circles[i]
            bx, by, bn, _ = circles[j]
            dist2 = (ax - bx) ** 2 + (ay - by) ** 2
            check(dist2 >= (2 * r + 4) ** 2,
                  "dots %d/%d spaced (%.1fpx)" % (an, bn, math.sqrt(dist2)))

    # Number labels go on TOP, choosing whichever nearby side is free so
    # they never cover a dot or another number.
    def rect_circle_hit(box, cx, cy, rr):
        rx = max(box[0], min(cx, box[2]))
        ry = max(box[1], min(cy, box[3]))
        return (rx - cx) ** 2 + (ry - cy) ** 2 < rr * rr

    def rect_hit(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    placed = []
    for cx, cy, num, color in circles:
        label = str(num)
        tw = text_w(d, label, f_num)
        box = None
        for gap in (r + 3, r + 9, r + 15, r + 21):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                           (1, 1), (-1, 1), (1, -1), (-1, -1)):
                if dx > 0:
                    nx = cx + gap
                elif dx < 0:
                    nx = cx - gap - tw
                else:
                    nx = cx - tw / 2
                if dy > 0:
                    ny = cy + gap
                elif dy < 0:
                    ny = cy - gap - na
                else:
                    ny = cy - na / 2
                trial = (nx, ny, nx + tw, ny + na)
                if not (trial[0] >= x + 1 and trial[2] <= x + w - 2
                        and trial[1] >= y + 1 and trial[3] <= y + h - 1):
                    continue
                if any(rect_circle_hit(trial, ox, oy, r + 1)
                       for ox, oy, _, _ in circles):
                    continue
                if any(rect_hit(trial, old) for old in placed):
                    continue
                box = trial
                break
            if box is not None:
                break
        check(box is not None, "dot number placed: %d" % num)
        assert box is not None  # narrows the optional for static analysis
        placed.append(box)
        # If the label had to sit away from its dot, add a thin leader line
        # so the association stays unambiguous over the busy map.
        bx = max(box[0], min(cx, box[2]))
        by = max(box[1], min(cy, box[3]))
        check((cx - bx) ** 2 + (cy - by) ** 2 <= (MAP_PAD_X + 24) ** 2,
              "leader line short: %d" % num)
        if (cx - bx) ** 2 + (cy - by) ** 2 > (r + 2) ** 2:
            d.line([(cx, cy), (bx, by)], fill=color, width=1)
        d.text((box[0], box[1]), label, font=f_num, fill=WHITE)
    return circles


def bottom_section(d, y0):
    left_w = 470
    div_x = MARGIN + left_w + 10
    right_x = div_x + 10
    right_w = W - MARGIN - right_x
    sec_bot = y0 + 180
    fh = font("mono", 13)
    # left: map
    put(d, MARGIN, y0, "WHERE IT HAPPENED", fh, WHITE, left_w, y0 + 18,
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
        put(d, lx + 12, ly, label, fl, MUTED, lw + 1, sec_bot, label="legend")
        lx += 12 + lw + 6
    check(lx - 6 <= div_x - 6, "legend row fits left column")
    check(ly + 14 <= sec_bot, "legend vertical budget")
    vrule(d, div_x, y0, sec_bot - 4, RULE_D)
    # right: numbered also-list, two columns (14..23, 24..32)
    put(d, right_x, y0, "ALSO ON FRIDAY 20 NOVEMBER", fh, WHITE, right_w,
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
            put(d, sx, yy, num, fn, WHITE, nw + 1, sec_bot, label="also num")
            yy = put_lines(d, tx, yy, lines, ft, ALSO_TEXT, 13, avail, sec_bot,
                           label="also item")
            yy += 2
        check(yy - 2 <= sec_bot, "also column fits: col %d" % col)
    return sec_bot


def footer(d, y0):
    box_bot = y0 + 40
    d.rounded_rectangle([MARGIN, y0, W - MARGIN, box_bot], radius=8,
                        fill=CARD_BG, outline=BORDER, width=1)
    fl = font("mono", 11)
    fb = font("sans", 11)
    put(d, MARGIN + 8, y0 + 6, DATE_CHECK_LABEL, fl, BRED, CONTENT_W - 16,
        y0 + 20, label="date check label")
    put(d, MARGIN + 8, y0 + 22, DATE_CHECK_ITEMS, fb, ALSO_TEXT, CONTENT_W - 16,
        box_bot - 4, label="date check items")
    fbot = font("sans", 11)
    bw = text_w(d, BOTTOM_LINE, fbot)
    check(bw <= CONTENT_W, "bottom line fits page")
    put(d, W // 2, box_bot + 6, BOTTOM_LINE, fbot, MUTED, CONTENT_W,
        H - 4, anchor="mt", label="bottom line")
    return box_bot + 6


# ----------------------------------------------------------------------
# Main render
# ----------------------------------------------------------------------

def render(path):
    img = Image.new("RGB", (W, H), BG)
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
    print("%d text/photo containment checks passed" % CHECKS)
    print("entry.png: 1024x1024, %d bytes (%.1f KB)" % (nbytes, nbytes / 1024))
    return CHECKS


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    render(os.path.join(here, "entry.png"))
