"""(Re)generate tests/regression/golden/ from a source tree.

    uv run python tests/regression/make_golden.py              # from the baseline commit
    uv run python tests/regression/make_golden.py --ref v0.2.0 # from another commit
    uv run python tests/regression/make_golden.py --current    # from the working tree

The goldens pin what the generator writes: the SVG of every case in
golden_cases.py, the text layer it hands to Inkscape, every call it makes to
Inkscape and Ghostscript, and its stdout.  test_golden.py fails when the
current code differs.

They were first made from the last commit before packaging (d96c08d), which
proves the restructure changed nothing.  After an *intentional* change to the
layout or the output, refresh them with --current, look at the diff of
golden/svg/ and say why in the commit.

A --ref is extracted with `git archive` into a temporary directory; the
checkout itself is never switched.  Only the shipped example and the configs
in tests/data are used, so the goldens contain placeholder data only.
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
from golden_lib import BLOBS, GOLDEN, MANIFEST, blob_name, run_case  # noqa: E402


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
    args = ap.parse_args()

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
                  f"{len(got['tools'])} tool call(s)")
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
