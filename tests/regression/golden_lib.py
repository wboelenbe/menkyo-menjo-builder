"""Running a golden case and reducing its output to something comparable.

Shared by make_golden.py (which writes golden/) and test_golden.py (which
compares against it).
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import support

HERE = Path(__file__).resolve().parent
GOLDEN = HERE / "golden"
MANIFEST = GOLDEN / "manifest.json"
BLOBS = GOLDEN / "svg"
DRIVER = HERE / "golden_driver.py"
# The flat and proof PDFs' sha256 per case (render-without-inkscape, Q-7):
# written by make_golden.py --pdf-hashes, beside the manifest, which stays as
# it was made from the baseline.
PDF_HASHES = GOLDEN / "pdf_sha256.json"


def layout_of(root):
    """'package' for a tree with src/menkyo/, 'flat' for the old src/*.py."""
    return "package" if (Path(root) / "src" / "menkyo").is_dir() else "flat"


def config_path(root, name):
    root = Path(root)
    if name == "example":
        if layout_of(root) == "package":
            return root / "src" / "menkyo" / "example.toml"
        return root / "config" / "example.toml"
    return support.DATA / name


# The awards the baseline's example defined.  kyu-grades (its AC-14) added a
# fourth, `kyu`, to the shipped example; the goldens were made without it, so
# a case on the example runs on a copy holding only these.  Everything else
# in the example reaches the run unchanged, so the goldens still prove that
# dan, shihan and renshi draw what they drew.
BASELINE_AWARDS = ("dan", "shihan", "renshi")

_TABLE = re.compile(r"^\s*\[")
_SLUG = re.compile(r'^\s*slug\s*=\s*"([^"]*)"', re.M)


def baseline_awards_only(text):
    """`text`, a configuration, without the [[awards]] blocks whose slug is
    not one of BASELINE_AWARDS: from the block's header to the next table
    header (or the end).  Nothing else is touched."""
    lines = text.splitlines(keepends=True)
    heads = [i for i, l in enumerate(lines) if _TABLE.match(l)] + [len(lines)]
    drop = set()
    for start, end in zip(heads, heads[1:]):
        if lines[start].strip() != "[[awards]]":
            continue
        m = _SLUG.search("".join(lines[start:end]))
        if m and m.group(1) not in BASELINE_AWARDS:
            drop.update(range(start, end))
    return "".join(l for i, l in enumerate(lines) if i not in drop)


def blob_name(sha):
    return f"{sha[:20]}.svg"


def _norm(value, out):
    return value.replace(str(out), "<OUT>") if isinstance(value, str) else value


def run_case(root, case, work, python=sys.executable):
    """Run `case` against the source tree at `root`, inside `work`.

    Returns {"stdout", "exit", "files", "textlayers", "tools"} and, separately,
    {sha: normalised svg} for every SVG seen.

    Since render-without-inkscape every case renders for real and nothing
    stands in for a program on PATH, so "tools" is always empty.  The text
    layers are the document(..., layer="text") SVGs, captured by the driver;
    they are named after their order, the stand-in's file names being gone.
    """
    root, work = Path(root), Path(work)
    work.mkdir(parents=True, exist_ok=True)
    out, home = work / "out", work / "home"
    capture = work / "captured"
    config = config_path(root, case["config"])
    if case["config"] == "example":
        # kyu-grades: the baseline's three awards only (BASELINE_AWARDS)
        text = Path(config).read_text(encoding="utf-8")
        config = work / "example.toml"
        config.write_text(baseline_awards_only(text), encoding="utf-8")
    spec = {
        "layout": layout_of(root), "src": str(root / "src"),
        "config": str(config),
        "argv": case["argv"], "out": str(out), "result": str(work / "result.json"),
        "capture": str(capture),
    }
    (work / "spec.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    env = support.isolated_env(home, path="/usr/bin:/bin")
    r = subprocess.run([str(python), "-I", str(DRIVER), str(work / "spec.json")],
                       env=env, cwd=str(work), capture_output=True, text=True,
                       timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"driver failed for {case['id']}:\n{r.stderr}")
    result = json.loads((work / "result.json").read_text(encoding="utf-8"))

    blobs, files, textlayers = {}, {}, {}
    if out.exists():
        for p in sorted(out.rglob("*")):
            if p.is_dir():
                continue
            rel = p.relative_to(out).as_posix()
            if p.suffix == ".svg":
                raw = p.read_text(encoding="utf-8")
                sha = support.sha256(raw)
                files[rel] = sha
                blobs[sha] = raw
            else:
                # PNG / PDF bytes depend on the renderer: their presence is
                # the contract here (render-without-inkscape compares how
                # they look).
                files[rel] = None
    if capture.exists():
        for p in sorted(capture.glob("*.svg")):
            raw = p.read_text(encoding="utf-8")
            sha = support.sha256(raw)
            textlayers[p.name] = sha
            blobs[sha] = raw
    tools = []
    return {
        "argv": case["argv"], "config": case["config"],
        "stdout": _norm(result["stdout"], out), "exit": result["exit"],
        "files": files, "textlayers": textlayers, "tools": tools,
    }, blobs


# The text layer's <image> box came from the stand-in inkscape's fixed query
# answer; since render-without-inkscape it is the real outline box.  Only its
# four numbers are left out of the comparison.
_IMAGE_BOX = re.compile(r'(<image x=")[\d.]+(" y=")[\d.]+(" width=")[\d.]+(" height=")[\d.]+(")')


def without_image_box(svg):
    return _IMAGE_BOX.sub(r"\1X\2Y\3W\4H\5", svg)


# paper-format (its AC-7): every output name carries the sheet size after
# the variant, `<award>-<variant>-<size>[-<suffix>].<ext>`.  The goldens keep
# the names 823af58 wrote and are compared through this mapping, so they
# still prove the A3 bytes; only the names moved.
_VARIANT = re.compile(r"-(overlay-flat|overlay(?!-flat)|proof)(?!-a[34](?=[-.]))(?=[-.])")


def sized(text, size="a3"):
    """`text` with `-<size>` inserted after the variant of every output name
    in it: a file name, `wrote` lines, `--list` output, an xlink:href.  A name
    that already has a size keeps it, so it is idempotent."""
    return _VARIANT.sub(rf"-\1-{size}", text)


def pinned_pdf(name):
    """A flat or proof PDF: drawn by our writer and fontTools alone, no pdfium.

    Its bytes are pinned.  An inked overlay's PDF holds pdfium's raster of
    the text layer, and a PNG is pdfium's, so neither is.
    """
    return name.endswith(".pdf") and ("-overlay-flat" in name or "-proof" in name)


def load_pdf_hashes():
    return json.loads(PDF_HASHES.read_text(encoding="utf-8"))


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def blob(sha):
    p = BLOBS / blob_name(sha)
    return p.read_text(encoding="utf-8") if p.exists() else None
