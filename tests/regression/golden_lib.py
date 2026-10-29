"""Running a golden case and reducing its output to something comparable.

Shared by make_golden.py (which writes golden/) and test_golden.py (which
compares against it).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import support

HERE = Path(__file__).resolve().parent
GOLDEN = HERE / "golden"
MANIFEST = GOLDEN / "manifest.json"
BLOBS = GOLDEN / "svg"
DRIVER = HERE / "golden_driver.py"


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
    """
    root, work = Path(root), Path(work)
    work.mkdir(parents=True, exist_ok=True)
    out, home = work / "out", work / "home"
    fakebin = support.make_fake_bin(work / "fakebin", python=python)
    log, capture = work / "tools.jsonl", work / "captured"
    spec = {
        "layout": layout_of(root), "src": str(root / "src"),
        "config": str(config_path(root, case["config"])),
        "argv": case["argv"], "out": str(out), "result": str(work / "result.json"),
    }
    (work / "spec.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    env = support.isolated_env(home, path_prepend=[fakebin], path="/usr/bin:/bin",
                               FAKE_TOOL_LOG=log, FAKE_CAPTURE_DIR=capture)
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
                # PNG / PDF here come from the stand-ins (or, for the text
                # layer, from numpy): their presence is the contract.
                files[rel] = None
    if capture.exists():
        for p in sorted(capture.glob("*.svg")):
            raw = p.read_text(encoding="utf-8")
            sha = support.sha256(raw)
            textlayers[p.name] = sha
            blobs[sha] = raw
    tools = [{"tool": c["tool"], "argv": [_norm(a, out) for a in c["argv"]],
              "fontconfig": c["fontconfig"]}
             for c in support.read_log(log)]
    return {
        "argv": case["argv"], "config": case["config"],
        "stdout": _norm(result["stdout"], out), "exit": result["exit"],
        "files": files, "textlayers": textlayers, "tools": tools,
    }, blobs


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def blob(sha):
    p = BLOBS / blob_name(sha)
    return p.read_text(encoding="utf-8") if p.exists() else None
