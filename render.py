#!/usr/bin/env python3
"""Manga/anime-style news poster — 'WORLD NEWS MANGA', Friday 20 Nov 2026.

Flat cel-shaded look, manga panels, halftone dots, chibi mascots.
Deterministic PIL only. 1024x1024 PNG.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math, os

W = H = 1024
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'entry.png')
F = '/usr/share/fonts/truetype/dejavu/'
def font(n, s): return ImageFont.truetype(F + n, s)

f_mast = font('DejaVuSans-Bold.ttf', 56)
f_sub = font('DejaVuSansMono-Bold.ttf', 18)
f_head = font('DejaVuSans-Bold.ttf', 24)
f_body = font('DejaVuSans.ttf', 16)
f_tag = font('DejaVuSansMono-Bold.ttf', 13)
f_big = font('DejaVuSans-Bold.ttf', 30)

# palette
BG = (18, 16, 28)
PAPER = (246, 240, 230)
INK = (30, 26, 38)
ACCENTS = [(255, 105, 130), (255, 196, 70), (90, 200, 250), (130, 240, 160), (200, 120, 255), (255, 150, 90)]

img = Image.new('RGB', (W, H), BG)
draw = ImageDraw.Draw(img)

# halftone dot field (background texture)
for ry in range(60):
    for cx in range(64):
        x = cx * 16 + (8 if ry % 2 else 0)
        y = ry * 16
        r = 1.2 + 2.2 * abs(math.sin(cx * 0.35 + ry * 0.3))
        c = (38, 32, 58) if (cx + ry) % 3 else (52, 40, 80)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=c)
# speed lines corners
for i in range(26):
    wdt = 2 + (i % 3) * 2
    off = i * 14
    draw.line([(W, 40 + off), (W - 200 - i * 8, 40 + off)], fill=(60, 48, 92), width=wdt)
    draw.line([(0, H - 40 - off), (150 + i * 8, H - 40 - off)], fill=(60, 48, 92), width=wdt)

def wrap(text, fnt, maxw):
    words = text.split(); lines, cur = [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if draw.textlength(t, font=fnt) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def panel(x0, y0, x1, y1, accent, tag, head, body, body_lines=3, text_w=None):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=PAPER, outline=INK, width=4)
    draw.rounded_rectangle([x0 + 7, y0 + 7, x1 - 7, y1 - 7], radius=12, outline=accent, width=2)
    # tag tab
    tw = draw.textlength(tag, font=f_tag) + 20
    draw.rounded_rectangle([x0 + 14, y0 - 14, x0 + 14 + tw, y0 + 14], radius=8, fill=accent, outline=INK, width=3)
    draw.text((x0 + 24, y0 - 7), tag, font=f_tag, fill=INK)
    tw = text_w or (x1 - x0 - 36)
    yy = y0 + 26
    for ln in wrap(head, f_head, tw)[:2]:
        draw.text((x0 + 18, yy), ln, font=f_head, fill=INK); yy += 29
    yy += 3
    for ln in wrap(body, f_body, tw)[:body_lines]:
        draw.text((x0 + 18, yy), ln, font=f_body, fill=(64, 58, 74)); yy += 20
    return yy

# masthead plate
draw.rounded_rectangle([40, 34, 984, 148], radius=18, fill=(255, 105, 130), outline=INK, width=5)
draw.text((66, 44), 'WORLD NEWS MANGA!', font=f_mast, fill=INK)
draw.text((70, 112), 'FRIDAY 20 NOVEMBER 2026 · THE WORLD IN ONE PAGE', font=f_sub, fill=INK)

# ---- TOP PANEL: summit (full width, with three chibi leader circles) ----
y = panel(40, 172, 984, 340, (255, 196, 70), 'PANEL 1 · SHENZHEN SUMMIT',
          'Trump, Xi, Putin: first three-way summit ever!',
          'Nuclear-risk dialogue agreed in Shenzhen. Russia calls it a watershed; excluded Europe watches — and drills.', 3, text_w=580)
# three chibi heads with flag colors
for i, (cx, col) in enumerate([(750, (90, 200, 250)), (830, (255, 140, 90)), (910, (230, 90, 110))]):
    cy = 262
    draw.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=col, outline=INK, width=4)   # head
    draw.ellipse([cx - 12, cy - 4, cx - 4, cy + 4], fill=INK)                             # eyes
    draw.ellipse([cx + 4, cy - 4, cx + 12, cy + 4], fill=INK)
    draw.arc([cx - 14, cy + 6, cx + 14, cy + 26], 20, 160, fill=INK, width=4)            # smile
    draw.rounded_rectangle([cx - 22, cy + 34, cx + 22, cy + 58], radius=10, fill=PAPER, outline=INK, width=4)  # body

# ---- LEFT COLUMN ----
xL0, xL1 = 40, 512
y = panel(xL0, 360, xL1, 512, (90, 200, 250), 'PANEL 2 · THE HAGUE',
          'World court: Myanmar guilty of genocide',
          'First-ever state conviction under the 1948 Convention (9–6). Rights groups push sanctions now.', 3, text_w=300)
# gavel mascot
gx, gy = 445, 452
draw.rounded_rectangle([gx - 6, gy - 30, gx + 10, gy + 20], radius=6, fill=(150, 100, 60), outline=INK, width=3)
draw.rounded_rectangle([gx - 26, gy - 8, gx + 30, gy + 8], radius=6, fill=(180, 130, 80), outline=INK, width=3)

y = panel(xL0, 538, xL1, 690, (255, 105, 130), 'PANEL 3 · TAIPEI',
          'AI bubble pops! Taiex −6.2%, week −18%',
          'Asian markets tumble on valuation fear — as Anthropic\'s record IPO debuts. Euphoria and dread at once.', 3, text_w=300)
# falling chart mascot
cx, cy = 445, 640
draw.line([(cx - 40, cy - 28), (cx - 10, cy - 10), (cx + 12, cy - 22), (cx + 40, cy + 26)], fill=(230, 60, 80), width=5)
draw.polygon([(cx + 40, cy + 26), (cx + 24, cy + 14), (cx + 34, cy + 2)], fill=(230, 60, 80))
draw.text((cx - 52, cy - 44), '!', font=f_big, fill=(230, 60, 80))

y = panel(xL0, 716, xL1, 878, (130, 240, 160), 'PANEL 4 · KYIV & RIYADH',
          'Missiles rain on two capitals',
          'Russia fires ~100 missiles and 400 drones at Ukraine. A Houthi missile hits Riyadh\'s tallest tower.', 3, text_w=300)
# warning triangle mascot
cx, cy = 445, 818
draw.polygon([(cx, cy - 34), (cx + 34, cy + 28), (cx - 34, cy + 28)], fill=(255, 196, 70), outline=INK)
draw.line([(cx, cy - 14), (cx, cy + 6)], fill=INK, width=5)
draw.ellipse([cx - 3, cy + 10, cx + 3, cy + 16], fill=INK)

# ---- RIGHT COLUMN ----
xR0, xR1 = 536, 984
y = panel(xR0, 360, xR1, 512, (200, 120, 255), 'PANEL 5 · ANTALYA',
          'COP31 ends — fossil-fuel words stripped',
          '200 governments still short of a deal; a bloc demands an explicit phase-out. Activists warn of failure.', 3, text_w=320)
# sad earth mascot
cx, cy = 905, 452
draw.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=(110, 200, 230), outline=INK, width=4)
draw.arc([cx - 30, cy - 20, cx + 10, cy + 10], 200, 340, fill=INK, width=4)
draw.arc([cx - 10, cy - 20, cx + 30, cy + 10], 200, 340, fill=INK, width=4)
draw.arc([cx - 16, cy + 6, cx + 16, cy + 26], 200, 340, fill=INK, width=4)

y = panel(xR0, 538, xR1, 690, (255, 150, 90), 'PANEL 6 · NEW DELHI',
          'Gen Z revolt over deleted voters!',
          'A mass movement demands answers for 130 million deleted names; the education minister has resigned.', 3, text_w=320)
# megaphone mascot
cx, cy = 905, 640
draw.polygon([(cx - 30, cy - 16), (cx + 8, cy - 34), (cx + 8, cy + 34), (cx - 30, cy + 16)], fill=(255, 196, 70), outline=INK)
draw.rounded_rectangle([cx - 38, cy - 12, cx - 26, cy + 12], radius=4, fill=(255, 150, 90), outline=INK, width=3)
for a in (-30, -15, 0):
    draw.line([(cx + 14, cy - 4), (cx + 14 + 18 * math.cos(math.radians(a)), cy - 4 + 18 * math.sin(math.radians(a)))], fill=INK, width=4)

y = panel(xR0, 716, xR1, 878, (255, 196, 70), 'PANEL 7 · BRUSSELS',
          'UK and EU meet to mend Brexit fences',
          'A decade after the vote, PM Burnham calls it a step to undo the damage. Denmark seals a Greenland deal.', 3, text_w=320)
# handshake mascot: two circles
cx, cy = 905, 818
draw.ellipse([cx - 40, cy - 16, cx - 6, cy + 16], fill=(90, 200, 250), outline=INK, width=4)
draw.ellipse([cx + 6, cy - 16, cx + 40, cy + 16], fill=(255, 140, 90), outline=INK, width=4)
draw.ellipse([cx - 4, cy - 10, cx + 4, cy + 2], fill=PAPER, outline=INK, width=3)

# ---- bottom ticker ----
draw.rounded_rectangle([40, 892, 984, 972], radius=14, fill=(38, 32, 58), outline=(120, 110, 160), width=2)
t1 = 'ALSO TODAY · KOREA COURT OVERTURNS HAN\'S JAIL TERM · FIJI DECLARES DROUGHT DISASTER'
t2 = 'YEMEN CRISIS DEEPENS · IRAQ DEPLOYS TO JURF AL-SAKHAR · IRAN WAR COST: $48.3B'
draw.text((60, 906), t1, font=f_tag, fill=(220, 214, 235))
draw.text((60, 930), t2, font=f_tag, fill=(220, 214, 235))

img.save(OUT, 'PNG', optimize=True)
sz = os.path.getsize(OUT)
print('written', OUT, sz, 'bytes', '(%.0f KiB)' % (sz / 1024))
