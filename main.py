#!/usr/bin/env python3
"""Entry: news-image-20261120 — 'WORLD NEWS MANGA'.

Writes the rendered 1024x1024 news poster (shipped in this repo as
entry.png, produced by render.py) to /output/entry.png.
Deterministic: no network, no randomness, no clock use.
"""
import os
import shutil

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'entry.png')
DST = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output') + '/entry.png'

os.makedirs(os.path.dirname(DST), exist_ok=True)
shutil.copyfile(SRC, DST)
print('wrote', DST, os.path.getsize(DST), 'bytes')
