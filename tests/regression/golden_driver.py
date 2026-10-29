"""Run the generator's main() once, from a given source tree, and record stdout.

    python -I golden_driver.py SPEC.json

SPEC holds: layout ("flat" for the pre-package tree, src/build_diploma.py;
"package" for src/menkyo/), src (the src/ directory), config, argv, out,
result (where to write {"stdout", "exit"}) and capture (a directory: every
document(..., layer="text") SVG the run draws is saved there in order, as
NN-textlayer.svg, which is the text layer that goes to the renderer).  It calls main() rather than the
`menkyo` command because the baseline has no cli(); the CLI wrapper is tested
separately.  Kept free of imports from tests/ so it runs against any tree.
"""

import contextlib
import io
import json
import sys


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        spec = json.load(fh)
    sys.path.insert(0, spec["src"])
    if spec["layout"] == "flat":
        import build_diploma as bd
    else:
        from menkyo import build_diploma as bd

    capture = spec.get("capture")
    real_document = bd.document

    def document(*a, **k):
        svg = real_document(*a, **k)
        if capture and k.get("layer") == "text":
            import os
            os.makedirs(capture, exist_ok=True)
            n = len(os.listdir(capture))
            with open(os.path.join(capture, f"{n:02d}-textlayer.svg"), "w",
                      encoding="utf-8") as fh:
                fh.write(svg)
        return svg

    bd.document = document
    argv = ["-c", spec["config"], *spec["argv"], "--out", spec["out"]]
    buf = io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf):
            bd.main(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, (int, type(None))) else str(e.code)
    with open(spec["result"], "w", encoding="utf-8") as fh:
        json.dump({"stdout": buf.getvalue(), "exit": code}, fh, ensure_ascii=False)


if __name__ == "__main__":
    main()
