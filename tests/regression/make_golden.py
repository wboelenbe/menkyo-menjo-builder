"""(Re)generate tests/regression/golden/ from a source tree.

    uv run python tests/regression/make_golden.py              # from the baseline commit
    uv run python tests/regression/make_golden.py --ref v0.2.0 # from another commit
    uv run python tests/regression/make_golden.py --current    # from the working tree
    uv run python tests/regression/make_golden.py --pdf-hashes # flat/proof PDF hashes only

The goldens pin what the generator writes: the SVG of every case in
golden_cases.py, the text layers it draws, and its stdout.  test_golden.py
fails when the current code differs.  (Until render-without-inkscape they
also pinned every call to Inkscape, made through a stand-in; the manifest
still holds those calls as history.)

They were first made from the last commit before packaging (d96c08d), which
proved the restructure changed nothing, and are now made from 823af58, the
last commit before plain-white, which proves that removing the coloured
variants left the other three untouched.  After an *intentional* change to the
layout or the output, refresh them with --current, look at the diff of
golden/svg/ and say why in the commit.

A --ref is extracted with `git archive` into a temporary directory; the
checkout itself is never switched.  Every case renders for real, so a --ref
from before render-without-inkscape needs a real Inkscape on /usr/bin:/bin;
there is no stand-in any more.  Only the shipped example and the configs
in tests/data are used, so the goldens contain placeholder data only.

--pdf-hashes renders the working tree and rewrites golden/pdf_sha256.json
only: the sha256 of every flat and proof PDF the cases write
(render-without-inkscape, Q-7).  Those PDFs come from our writer and
fontTools' glyph outlines alone, so they are pinned byte for byte; a
fontTools bump may move them, and then they are looked at and refreshed.
The manifest is left alone.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))        # tests/, for support
sys.path.insert(0, str(HERE))

import support  # noqa: E402
from golden_cases import CASES, LIST_CASES  # noqa: E402
from golden_lib import (BLOBS, GOLDEN, MANIFEST, PDF_HASHES, blob_name,  # noqa: E402
                        pinned_pdf, run_case)

PDF_NOTE = ("The sha256 of the flat and proof PDFs (render-without-inkscape, Q-7). "
            "They are drawn by menkyo's own PDF writer from fontTools' glyph "
            "outlines, without pdfium, so they are byte for byte the same on every "
            "platform. A fontTools release may change the outlines and so these "
            "hashes: look at the PDFs, then refresh with make_golden.py --pdf-hashes.")


def pdf_hashes():
    from importlib.metadata import version
    cases = {}
    with tempfile.TemporaryDirectory(prefix="menkyo-golden-") as tmp:
        for case in CASES:
            work = Path(tmp) / case["id"]
            got, _ = run_case(support.REPO, case, work)
            pinned = {n: support.sha256((work / "out" / n).read_bytes())
                      for n in sorted(got["files"]) if pinned_pdf(n)}
            if pinned:
                cases[case["id"]] = pinned
                print(f"{case['id']}: {len(pinned)} PDF(s)")
    doc = {"note": PDF_NOTE, "source": "working tree",
           "fonttools": version("fonttools"), "cases": cases}
    PDF_HASHES.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")
    print(f"wrote {PDF_HASHES.relative_to(support.REPO)}")


def extract(ref, dest):
    archive = subprocess.run(["git", "-C", str(support.REPO), "archive", ref],
                             check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--ref", default=support.BASELINE_REF,
                   help=f"commit to generate from (default: {support.BASELINE_REF})")
    g.add_argument("--current", action="store_true",
                   help="generate from the working tree instead")
    g.add_argument("--pdf-hashes", action="store_true",
                   help="only rewrite golden/pdf_sha256.json, from the working tree")
    args = ap.parse_args()
    if args.pdf_hashes:
        return pdf_hashes()

    with tempfile.TemporaryDirectory(prefix="menkyo-golden-") as tmp:
        tmp = Path(tmp)
        if args.current:
            root, source = support.REPO, "working tree"
        else:
            (tmp / "tree").mkdir()
            root = extract(args.ref, tmp / "tree")
            source = args.ref

        manifest = {"source": source, "cases": {}, "lists": {}}
        blobs = {}
        for case in CASES:
            got, b = run_case(root, case, tmp / "run" / case["id"])
            manifest["cases"][case["id"]] = got
            blobs.update(b)
            print(f"{case['id']}: {len(got['files'])} file(s), "
                  f"{len(got['textlayers'])} text layer(s)")
        for case in LIST_CASES:
            got, _ = run_case(root, dict(case, argv=["--list", *case["argv"]]),
                              tmp / "list" / case["id"])
            manifest["lists"][case["id"]] = {
                "argv": case["argv"], "config": case["config"],
                "stdout": got["stdout"], "exit": got["exit"]}

    shutil.rmtree(BLOBS, ignore_errors=True)
    BLOBS.mkdir(parents=True)
    for sha, text in blobs.items():
        (BLOBS / blob_name(sha)).write_text(text, encoding="utf-8")
    GOLDEN.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    print(f"wrote {MANIFEST.relative_to(support.REPO)} and {len(blobs)} SVG(s) "
          f"from {source}")


if __name__ == "__main__":
    main()
