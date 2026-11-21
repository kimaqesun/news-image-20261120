# World News Manga — news-image-20261120

A manga-style summary of 20 November 2026's world news in one 1024x1024 PNG.

- `render.py` — deterministic PIL renderer that produces `entry.png`
- `entry.png` — the shipped entry image
- `main.py` — entrypoint: copies the shipped image to `/output/entry.png`
- Style: cel-shaded manga panels, halftone dots, chibi mascots

Usage: `MAKEFUN_OUTPUT_DIR=/tmp/mftest python3 main.py` copies `entry.png` to `$MAKEFUN_OUTPUT_DIR/entry.png` (default `/output`); re-render the image with `python3 render.py`.

MIT licensed.
