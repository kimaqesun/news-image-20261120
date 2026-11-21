#!/usr/bin/env python3
"""Entrypoint for the ONE DAY OF WORLD NEWS newspaper front page (v3).

Copies the shipped, pre-rendered entry.png (produced by render.py) into
the output directory named by MAKEFUN_OUTPUT_DIR, defaulting to /output.
The directory is created if missing. Reports the destination, byte count
and verifies the copy. Deterministic and offline: no network access, no
randomness, no clock reads.
"""

import os
import shutil
import sys


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "entry.png")
    if not os.path.isfile(src):
        print("error: shipped entry.png not found next to main.py; "
              "run 'python3 render.py' first to generate it.", file=sys.stderr)
        return 1

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "entry.png")
    shutil.copyfile(src, dst)

    src_size = os.path.getsize(src)
    dst_size = os.path.getsize(dst)
    if dst_size != src_size:
        print("error: copy size mismatch (%d != %d bytes)" % (dst_size, src_size),
              file=sys.stderr)
        return 1

    print("ONE DAY OF WORLD NEWS -- Friday 20 November 2026, 32 stories")
    print("Delivered entry.png -> %s" % dst)
    print("Size: %d bytes (%.1f KB), 1024x1024 newspaper front page"
          % (dst_size, dst_size / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())