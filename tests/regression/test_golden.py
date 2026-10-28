"""The current code writes exactly what the baseline (d96c08d) wrote.

Goldens: golden/manifest.json and golden/svg/, made by make_golden.py.  Each
case runs the generator through golden_driver.py with the stand-in inkscape
and gs, and is compared on: exit status, stdout, the set of files written,
every SVG byte for byte, the text layer handed to Inkscape, and every call
made to Inkscape and Ghostscript (paths normalised).
"""

import difflib

import pytest

import support
from golden_cases import CASES, LIST_CASES
from golden_lib import blob, load_manifest, run_case

MANIFEST = load_manifest()


def _svg_diff(expected_sha, actual_text, name):
    expected = blob(expected_sha)
    if expected is None:
        return f"(no stored blob for {name})"
    diff = difflib.unified_diff(
        expected.splitlines(), support.normalise_svg(actual_text).splitlines(),
        f"golden/{name}", f"current/{name}", lineterm="", n=1)
    return "\n".join(list(diff)[:80])


def test_manifest_covers_every_case():
    assert set(MANIFEST["cases"]) == {c["id"] for c in CASES}
    assert set(MANIFEST["lists"]) == {c["id"] for c in LIST_CASES}


def test_goldens_hold_placeholder_data_only():
    """The stored goldens come from the example and tests/data only."""
    for p in (support.TESTS / "regression" / "golden").rglob("*"):
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "/Users/" not in text and "/home/" not in text, p


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_output_matches_baseline(case, tmp_path):
    golden = MANIFEST["cases"][case["id"]]
    assert golden["argv"] == case["argv"], "golden_cases.py changed: run make_golden.py"
    got, _ = run_case(support.REPO, case, tmp_path)

    assert got["exit"] == golden["exit"]
    assert got["stdout"] == golden["stdout"]
    assert sorted(got["files"]) == sorted(golden["files"]), "different files written"
    assert got["tools"] == golden["tools"], "different Inkscape / Ghostscript calls"

    out = tmp_path / "out"
    mismatched = []
    for name, sha in golden["files"].items():
        if sha is not None and got["files"][name] != sha:
            mismatched.append(_svg_diff(sha, (out / name).read_text(encoding="utf-8"), name))
    assert sorted(got["textlayers"]) == sorted(golden["textlayers"])
    for name, sha in golden["textlayers"].items():
        if got["textlayers"][name] != sha:
            text = (tmp_path / "captured" / name).read_text(encoding="utf-8")
            mismatched.append(_svg_diff(sha, text, "textlayer/" + name))
    assert not mismatched, "\n\n".join(mismatched)


@pytest.mark.parametrize("case", LIST_CASES, ids=[c["id"] for c in LIST_CASES])
def test_list_matches_baseline(case, tmp_path):
    golden = MANIFEST["lists"][case["id"]]
    got, _ = run_case(support.REPO, dict(case, argv=["--list", *case["argv"]]), tmp_path)
    assert got["exit"] == golden["exit"]
    assert got["stdout"] == golden["stdout"]
    assert not (tmp_path / "out").exists(), "--list must not write anything"
