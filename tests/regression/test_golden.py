"""The current code writes exactly what the baseline (823af58) wrote.

Goldens: golden/manifest.json and golden/svg/, made by make_golden.py.  Each
case runs the generator through golden_driver.py and is compared on: exit
status, stdout, the set of files written, every SVG byte for byte, and the
text layers drawn.

Since render-without-inkscape (its acceptance.md, AC-25) every case renders
for real, with no program on PATH.  The manifest is unchanged and keeps the
Inkscape calls the baseline made under "tools", as history; they are no
longer compared.  An inked SVG's text-layer <image> box came from the
stand-in's fixed answer and is now the real one, so its four numbers are
left out (AC-21 of that item checks them against Inkscape's).  The text
layers are compared as a sorted list of hashes: the stand-in's file names
are gone.

The flat and proof PDFs are compared by sha256 too (golden/pdf_sha256.json,
made with make_golden.py --pdf-hashes; that item's Q-7).  They depend on our
PDF writer and on fontTools' glyph outlines, so a fontTools bump may change
them: look at the PDFs, then refresh the hashes.
"""

import difflib

import pytest

import support
from golden_cases import CASES, LIST_CASES
from golden_lib import (blob, load_manifest, load_pdf_hashes, pinned_pdf, run_case,
                        without_image_box)

MANIFEST = load_manifest()


def _pdf_hashes():
    """golden/pdf_sha256.json, read when a test needs it: a missing file
    fails those tests, not the collection of the whole suite."""
    try:
        return load_pdf_hashes()
    except FileNotFoundError:
        pytest.fail("tests/regression/golden/pdf_sha256.json is missing: "
                    "run make_golden.py --pdf-hashes")


def _svg_diff(expected_sha, actual_text, name):
    expected = blob(expected_sha)
    if expected is None:
        return f"(no stored blob for {name})"
    if without_image_box(expected) == without_image_box(actual_text):
        return None
    diff = difflib.unified_diff(
        expected.splitlines(), actual_text.splitlines(),
        f"golden/{name}", f"current/{name}", lineterm="", n=1)
    return "\n".join(list(diff)[:80])


def test_manifest_covers_every_case():
    assert set(MANIFEST["cases"]) == {c["id"] for c in CASES}
    assert set(MANIFEST["lists"]) == {c["id"] for c in LIST_CASES}


def test_pdf_hashes_cover_known_cases():
    PDF_HASHES = _pdf_hashes()
    assert set(PDF_HASHES["cases"]) <= {c["id"] for c in CASES}
    assert PDF_HASHES["cases"], "no flat/proof PDF pinned"


def test_goldens_hold_placeholder_data_only():
    """The stored goldens come from the example and tests/data only."""
    for p in (support.TESTS / "regression" / "golden").rglob("*"):
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "/Users/" not in text and "/home/" not in text, p


@pytest.mark.render
@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_output_matches_baseline(case, tmp_path):
    golden = MANIFEST["cases"][case["id"]]
    assert golden["argv"] == case["argv"], "golden_cases.py changed: run make_golden.py"
    got, _ = run_case(support.REPO, case, tmp_path)

    assert got["exit"] == golden["exit"]
    assert got["stdout"] == golden["stdout"]
    assert sorted(got["files"]) == sorted(golden["files"]), "different files written"

    out = tmp_path / "out"
    mismatched = []
    for name, sha in golden["files"].items():
        if sha is not None and got["files"][name] != sha:
            mismatched.append(_svg_diff(sha, (out / name).read_text(encoding="utf-8"), name))
    mismatched = [m for m in mismatched if m is not None]
    assert not mismatched, "\n\n".join(mismatched)
    # like with like: every text layer drawn once, as the baseline drew them
    assert sorted(got["textlayers"].values()) == sorted(golden["textlayers"].values()), \
        "the text layers drawn differ from the baseline's"
    # every flat and proof PDF written is pinned, byte for byte
    PDF_HASHES = _pdf_hashes()
    pinned = PDF_HASHES["cases"].get(case["id"], {})
    assert sorted(n for n in got["files"] if pinned_pdf(n)) == sorted(pinned), \
        "different flat/proof PDFs written: run make_golden.py --pdf-hashes"
    changed = [n for n, sha in pinned.items()
               if support.sha256((out / n).read_bytes()) != sha]
    assert not changed, (f"flat/proof PDF bytes changed: {changed} "
                         f"({PDF_HASHES['note']})")


@pytest.mark.parametrize("case", LIST_CASES, ids=[c["id"] for c in LIST_CASES])
def test_list_matches_baseline(case, tmp_path):
    golden = MANIFEST["lists"][case["id"]]
    got, _ = run_case(support.REPO, dict(case, argv=["--list", *case["argv"]]), tmp_path)
    assert got["exit"] == golden["exit"]
    assert got["stdout"] == golden["stdout"]
    assert not (tmp_path / "out").exists(), "--list must not write anything"
