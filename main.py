#!/usr/bin/env python3
"""Entrypoint for the World News Manga entry.

Copies the shipped, pre-rendered entry.png (produced by render.py) into the
output directory named by the MAKEFUN_OUTPUT_DIR environment variable,
defaulting to /output. The directory is created if missing. Prints the
destination path and byte count after writing. Deterministic and offline:
no network access, no randomness, no clock reads.
"""

import os
import shutil


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "entry.png")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "entry.png")
    shutil.copyfile(src, dst)
    print("Wrote %s (%d bytes)" % (dst, os.path.getsize(dst)))


if __name__ == "__main__":
    main()
