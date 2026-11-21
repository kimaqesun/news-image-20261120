# Design spec — "WORLD NEWS MANGA" (news-image-20261120)

Build render.py (pure PIL, deterministic: no network, no random, no clock) that
renders entry.png: a 1024x1024 manga/anime-style summary of 20 November 2026
world news. Output size under 900 KB.

## Look
- Dark background (deep indigo ~ (18,16,28)) with a subtle halftone dot texture.
- Manga speed lines near the corners.
- Cream paper panels (~ (246,240,230)) with thick dark ink outlines (~4px) and
  rounded corners; each panel has a colored tag tab overlapping its top edge.
- Palette of accents: coral red, warm yellow, sky blue, mint green, purple, orange.
- DejaVu fonts only (DejaVuSans-Bold for headlines, DejaVuSans for body,
  DejaVuSansMono-Bold for tags), from /usr/share/fonts/truetype/dejavu/.

## Layout
1. Masthead plate at top: coral rounded rectangle, big bold title
   "WORLD NEWS MANGA!", subtitle line "FRIDAY 20 NOVEMBER 2026 · THE WORLD IN ONE PAGE".
2. Wide top panel (PANEL 1 · SHENZHEN SUMMIT): headline "Trump, Xi, Putin: first
   three-way summit ever!", body about nuclear-risk dialogue in Shenzhen, Russia
   calling it a watershed, Europe excluded. Decorate right side with three chibi
   circle-head mascots (blue, orange, red) with dot eyes and smiles.
3. Two columns below, three panels per column:
   - PANEL 2 · THE HAGUE: "World court: Myanmar guilty of genocide", first-ever
     state conviction under the 1948 Convention (9-6). Small gavel mascot.
   - PANEL 3 · TAIPEI: "AI bubble pops! Taiex -6.2%, week -18%", Anthropic record
     IPO same day. Falling red chart line with arrowhead mascot.
   - PANEL 4 · KYIV & RIYADH: "Missiles rain on two capitals", Russia fires ~100
     missiles and 400 drones; a Houthi missile hits Riyadh's tallest tower.
     Warning triangle mascot.
   - PANEL 5 · ANTALYA: "COP31 ends — fossil-fuel words stripped", 200 governments
     short of a deal. Sad earth mascot (blue circle, worried face).
   - PANEL 6 · NEW DELHI: "Gen Z revolt over deleted voters!", 130 million deleted
     names, education minister resigned. Megaphone mascot.
   - PANEL 7 · BRUSSELS: "UK and EU meet to mend Brexit fences", PM Burnham,
     decade after the vote; Denmark seals a Greenland deal. Two-circle handshake
     mascot.
4. Bottom ticker bar: dark rounded strip with two small mono lines of extra
   headlines (Korea court overturns Han's jail term; Fiji declares drought
   disaster; Yemen crisis deepens; Iraq deploys to Jurf al-Sakhar; Iran war cost
   $48.3B).

## Hard requirements
- No text may touch or overflow a panel border; mascots stay in their own zone
  (reserve the right ~150px of each panel for the mascot, wrap text narrower).
- Keep every panel body to its allotted lines so nothing is clipped.
- render.py should print the file size when done.
Then write main.py: copies the shipped entry.png to
os.environ.get('MAKEFUN_OUTPUT_DIR', '/output') + '/entry.png' (creates dir),
prints what it wrote. Deterministic, no network.
