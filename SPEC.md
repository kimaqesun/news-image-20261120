# Design spec v3 — "ONE DAY OF WORLD NEWS" newspaper front page (news-image-20261120)

Rewrite render.py completely. Pure PIL, deterministic (no network, no random, no
clock). Output: entry.png, 1024x1024, under 900 KB. The look is a dense
newspaper/infographic front page on a warm cream background — NOT dark, NOT
manga. Every fact below happened on, or was first reported on, Friday
20 November 2026.

## Palette
- Paper: (247, 243, 233). Ink: (25, 25, 30). Rule lines: (60,60,70).
- Section accent colors: red (200,40,40), blue (25,80,160), teal (0,120,120),
  amber (200,130,20), green (40,120,60), purple (110,50,140).
- Tag chips: small rounded rect with white uppercase text on the accent color.
- Fonts: DejaVuSerif-Bold for masthead and story headlines, DejaVuSans for body,
  DejaVuSansMono-Bold for tags/numbers. All in /usr/share/fonts/truetype/dejavu/.

## Layout (top to bottom)
1. Thin top bar: small caps "ONE DAY OF WORLD NEWS" left; right:
   "32 STORIES · 7 REGIONS · EVERY ONE DATED FRIDAY 20 NOVEMBER 2026".
2. Masthead: huge serif "Friday 20 November 2026" centered, with a thin
   double rule under it.
3. "THE DAY IN NUMBERS" strip: six stat cells separated by vertical rules,
   each a big mono number + tiny two-line label:
   111 (missiles + 404 drones fired at Ukraine) · 3 (Kyiv bridges hit) ·
   −3.7% (S&P 500, worst week since 2020) · −6.2% (Taiex, day) ·
   −14% (Nvidia on SEC probe report) · 372,000 (evacuated ahead of Cyclone Akvan).
4. Three featured stories (equal columns), each with a simple PIL-drawn
   illustration block (~90px tall, flat vector shapes), then a tag chip
   (region · city), a serif headline, and a 2-line body:
   1) UKRAINE · KYIV (red): "Russia hits 3 Kyiv bridges in mass strike, killing
      at least 9". 111 missiles and 404 drones were fired; 7 killed in Kyiv,
      2 in Lviv; power and water cut. Illustration: night skyline with a river
      and three broken bridge spans, missile streaks.
   2) WORLD MARKETS (blue): "AI rout: S&P 500 sinks 3.7%, enters a correction".
      Nasdaq −5.3%, Taiwan −6.2%, Nikkei −5.1%; world stocks' worst week since
      2020. Illustration: falling red line chart with axis ticks.
   3) INDIA · ODISHA (teal): "Cyclone Akvan hits Odisha; no deaths reported".
      Landfall 02:00–03:00 UTC near Gopalpur, 70–80 km/h winds, 209 mm of rain,
      372,000 evacuated. Illustration: coastline, spiral cyclone symbol,
      red dashed landfall arrow.
5. Grid of ten mid stories (5 columns x 2 rows), each: tiny accent-colored
   icon square (flat shape), tag chip, short serif headline, 2-line body:
   4) US · TECH (red): "Nvidia sinks 14% on SEC probe report". Reuters reports
      SEC staff examining its accounting.
   5) TÜRKIYE (amber): "COP31 runs into overtime, no deal". Draft omits fossil
      fuels; new text Saturday.
   6) POLAND (blue): "Poland says 2 Russian missiles landed". A Kh-101 found by
      a forest; no one hurt.
   7) BRUSSELS (blue): "UK and EU seal food, carbon, visa deals". 100,000 youth
      visas; food checks eased.
   8) HORMUZ (teal): "Tanker set ablaze off Oman near Hormuz". No casualties;
      Iran's Guards blame a mine.
   9) INDIA (green): "Pakistani minister visits New Delhi". First since the
      May 2025 clash.
   10) KENYA (amber): "Kenya starts drilling for Turkana oil". First crude
       targeted for 1 December.
   11) NEW ZEALAND (green): "New Zealand make 368 against India". Nicholls 175
       not out, Phillips 118; India 159–1.
   12) ARGENTINA (teal): "Argentina's country risk jumps to 1,070". Up 13%,
       first close over 1,000 in 13 months.
   13) HEALTH (purple): "Pancreatic cancer pill: 60.7% respond". Tumours shrink
       with chemo in 61 patients; trial data.
6. Bottom section, two columns:
   - Left: "WHERE IT HAPPENED" — a simplified flat world map drawn from dot
     clusters (Europe 8, Middle East 4, Asia 6, Americas 8, Africa 3, Oceania 2)
     with numbered dots and a small color-coded legend.
   - Right: "ALSO ON FRIDAY 20 NOVEMBER" — numbered list (14–32), two columns
     of ~9 lines each, tiny text, e.g.:
     14 Lviv: strike on rail station kills 2. 15 Estonia: shuts Russian border.
     16 CYGIL holds a general strike over the budget. 17 Europe: shares end
     worst week in a year. 18 Gaza: Israeli strikes kill 6 despite truce.
     19 Iraq: forces enter Jurf al-Sakhar. 20 Yemen: coalition strikes
     Hodeidah. 21 Africa: AfDB says 22 states near debt distress.
     22 Sudan: army gains in West Kordofan. 23 Japan: core inflation 2.2%.
     24 S. Korea: ruling party moves to impeach top judge. 25 Bangladesh:
     new arson attacks; 124 held in Dhaka. 26 Myanmar: government calls world
     court ruling 'unfair'. 27 Australia: Xi hails 'full turnaround' in ties.
     28 Wall St: Anthropic falls 8.6% day two, still above $83. 29 US: floods
     spread north after 17+ in of rain. 30 US Fed: Lisa Cook calls for rate
     hikes now. 31 Mexico: Sheinbaum leads Victory Day parade.
     32 Film: Hunger Games prequel takes $21.25m in previews.
7. Footer bar (full width, small text):
   - "DATE CHECK" box: one or two lines — left out on purpose, first reported
     before Friday: the Trump-Xi-Putin Shenzhen talks (Thu 19), the ICJ Rohingya
     genocide ruling (Wed 18), Denmark's Greenland vote (Thu 19).
   - Bottom line: "Every story here happened on, or was first reported on,
     Friday 20 November 2026 · Sources: AP, Reuters, AFP, BBC, IMF, UKMTÒ ·
     original drawings".

## Hard requirements
- Tiny text must still be legible: never below 11px font size.
- Nothing may overlap or overflow; use helper functions and measure text with
  draw.textlength before placing. Keep 8px+ padding inside every box.
- Verify with PIL that entry.png is 1024x1024 and print its byte size.
- The renderer must contain at least 50 internal sanity assertions or
  containment checks (text width fits its column, y-cursor never exceeds its
  box) and print "50 text/mascot containment checks passed" style summary.

## main.py
Overwrite main.py: copies the shipped entry.png to
os.environ.get('MAKEFUN_OUTPUT_DIR', '/output') + '/entry.png' (creates the
directory), prints what it wrote. Then edit it once to polish its messages
(the entrypoint must be revised after its first write).
