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
    spec = {
        "layout": layout_of(root), "src": str(root / "src"),
        "config": str(config_path(root, case["config"])),
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
