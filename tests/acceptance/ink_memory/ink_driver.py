"""Driver for the ink-memory render tests (docs/work/ink-memory/acceptance.md).

    python ink_driver.py REPORT.json {current|reference} CAPTURE_DIR -- MENKYO ARGS...

Runs the generator's main() in this process, with real Inkscape on PATH, and
writes REPORT.json with this process's own peak RSS (Inkscape's subprocesses
are not counted). With `reference`, ink.ink_layer is replaced by the pinned
823af58 copy in reference_ink.py, so the same build can be measured with
today's and the old grading. Either way, the text raster handed to
ink_layer is copied to CAPTURE_DIR/preink-N.png first, and the graded result
to CAPTURE_DIR/inked-N.png, so a test can compare the two implementations on
the exact input Inkscape produced.

The caller passes -c and an isolated HOME; this script reads no config itself.
"""

import importlib.util
import json
import os
import resource
import shutil
import sys
from pathlib import Path


def _peak_bytes():
    """This process's peak RSS. On Linux that is VmHWM, which belongs to the
    address space and starts afresh at exec: ru_maxrss survives execve there,
    and subprocess spawns through vfork, so it would report the parent's
    peak (pytest's, over a GB) instead of this run's."""
    if sys.platform.startswith("linux"):
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) * 1024
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r if sys.platform == "darwin" else r * 1024


def main():
    report, which, capture = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    assert sys.argv[4] == "--"
    argv = sys.argv[5:]
    capture.mkdir(parents=True, exist_ok=True)

    from menkyo import build_diploma, ink

    impl = ink.ink_layer
    if which == "reference":
        spec = importlib.util.spec_from_file_location(
            "reference_ink", Path(__file__).with_name("reference_ink.py"))
        ref = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ref)
        impl = ref.ink_layer
    calls = []

    def wrapped(png_path, out_path, dpi, *a, **kw):
        n = len(calls)
        shutil.copy(png_path, capture / f"preink-{n}.png")
        r = impl(png_path, out_path, dpi, *a, **kw)
        shutil.copy(out_path, capture / f"inked-{n}.png")
        calls.append({"dpi": dpi})
        return r

    ink.ink_layer = wrapped
    code = 0
    try:
        build_diploma.main(argv)
    except SystemExit as e:
        code = e.code or 0
    Path(report).write_text(json.dumps(
        {"peak_rss": _peak_bytes(), "calls": calls, "exit": code}))
    sys.exit(code)


if __name__ == "__main__":
    main()
