"""Reference renders (the Inkscape side), run inside the menkyo-spike-ref image.

    python ref_driver.py OUT CASE [CASE ...]      (cases from cases.py)

Runs menkyo's own main() for each case with -c example.toml and --out
OUT/<case>, unchanged, except that it intercepts what the contract needs and
.work/ would delete: the text-layer PNG before and after ink.ink_layer, and
the <image> element (bbox in mm) that _inked_text_image returns. Each stage's
start time goes to OUT/<case>/stages.json (S-3), and the wall time of the
whole case too.
"""
import json, os, shutil, sys, time

sys.path.insert(0, os.environ.get("MENKYO_SRC", "/menkyo/src"))
from menkyo import build_diploma as bd, ink, paths  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cases import CASES  # noqa: E402

out_root = sys.argv[1]
# SPIKE_CONFIG: a throwaway config written by the spike (G-3 traced glyphs).
EXAMPLE = os.environ.get("SPIKE_CONFIG") or paths.resource("example.toml")

for case in sys.argv[2:]:
    out = os.path.join(out_root, case)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    keep = os.path.join(out, "keep")
    os.makedirs(keep)
    stamps = []

    real_ink = ink.ink_layer
    def ink_spy(src, dst, dpi, *a, **k):
        shutil.copy(src, os.path.join(keep, "textlayer-raw.png"))
        r = real_ink(src, dst, dpi, *a, **k)
        shutil.copy(dst, os.path.join(keep, "textlayer-graded.png"))
        return r
    ink.ink_layer = ink_spy

    real_img = bd._inked_text_image
    def img_spy(*a, **k):
        el = real_img(*a, **k)
        open(os.path.join(keep, "image-element.txt"), "w").write(el)
        return el
    bd._inked_text_image = img_spy

    t0 = time.perf_counter()
    argv = ["-c", EXAMPLE, "--out", out] + CASES[case]
    bd.main(argv, progress=lambda e: stamps.append(
        (e["stage"], time.perf_counter() - t0)))
    wall = time.perf_counter() - t0
    ink.ink_layer, bd._inked_text_image = real_ink, real_img
    json.dump({"argv": argv, "wall": wall, "stages": stamps},
              open(os.path.join(out, "stages.json"), "w"), ensure_ascii=False, indent=1)
    print(case, f"{wall:.2f}s", sorted(f for f in os.listdir(out) if f != "keep"))
