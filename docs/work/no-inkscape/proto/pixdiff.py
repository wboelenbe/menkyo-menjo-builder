"""P-3: two PNGs (or PDFs) compared exactly.   python pixdiff.py A B

Byte equality, decoded-pixel equality, max |diff| per channel and the share
of pixels with any channel differing by more than 1.
"""
import hashlib, json, sys
import numpy as np
from PIL import Image
a, b = sys.argv[1:3]
ra, rb = open(a, "rb").read(), open(b, "rb").read()
out = dict(bytes_identical=ra == rb)
if a.endswith(".png"):
    A = np.asarray(Image.open(a).convert("RGBA")).astype(int)
    B = np.asarray(Image.open(b).convert("RGBA")).astype(int)
    d = np.abs(A - B)
    out.update(pixels_identical=bool((d == 0).all()), max_abs_diff_rgba=d.reshape(-1, 4).max(0).tolist(),
               share_gt1=float((d.max(-1) > 1).mean()))
print(json.dumps(out))
