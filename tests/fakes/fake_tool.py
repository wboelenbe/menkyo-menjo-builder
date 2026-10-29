"""A stand-in for `inkscape`, so the CLI can run end to end without it.

Invoked as `fake_tool.py inkscape ARGS...` by the small shell wrapper that
support.make_fake_bin() writes.  Standard library only, so it runs under
whichever Python the wrapper names.

It writes plausible output files (a real, tiny PNG; a stub PDF), never draws
anything, and is deterministic.  Environment knobs:

    FAKE_TOOL_LOG       append one JSON line per call: tool, argv, whether
                        FONTCONFIG_FILE was set and the font dirs it names
    FAKE_CAPTURE_DIR    copy the SVG given to `inkscape --query-*` here,
                        which is the generator's text layer
    FAKE_INKSCAPE_FAIL  fail (exit 1, message on stderr) when the export type
                        or "query" matches this value
"""

import json
import os
import re
import shutil
import struct
import sys
import zlib

# What `inkscape --query-x --query-y --query-width --query-height` answers,
# in CSS px.  Arbitrary; the box only places the <image>, and the goldens pin it.
QUERY = ("100.0", "200.0", "40.0", "30.0")


def _png(path, w=64, h=48):
    """A valid RGBA PNG: transparent, with an opaque black block in the middle."""
    rows = []
    for y in range(h):
        row = bytearray([0])                       # filter: none
        for x in range(w):
            inside = w // 4 <= x < 3 * w // 4 and h // 4 <= y < 3 * h // 4
            row += bytes((0, 0, 0, 255 if inside else 0))
        rows.append(bytes(row))

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
        fh.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)))
        fh.write(chunk(b"IDAT", zlib.compress(b"".join(rows))))
        fh.write(chunk(b"IEND", b""))


def _log(tool, argv):
    log = os.environ.get("FAKE_TOOL_LOG")
    if not log:
        return
    conf = os.environ.get("FONTCONFIG_FILE")
    dirs = []
    if conf and os.path.exists(conf):
        dirs = re.findall(r"<dir>(.*?)</dir>", open(conf, encoding="utf-8").read())
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"tool": tool, "argv": argv,
                             "fontconfig": bool(conf), "font_dirs": dirs},
                            ensure_ascii=False) + "\n")


def _fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def inkscape(argv):
    src = next((a for a in argv if not a.startswith("-")), None)
    if "--query-x" in argv:
        if os.environ.get("FAKE_INKSCAPE_FAIL") == "query":
            _fail("fake inkscape: simulated query failure")
        cap = os.environ.get("FAKE_CAPTURE_DIR")
        if cap and src:
            os.makedirs(cap, exist_ok=True)
            shutil.copy(src, os.path.join(cap, os.path.basename(src)))
        print("\n".join(QUERY))
        return
    kind = next((a.split("=", 1)[1] for a in argv
                 if a.startswith("--export-type=")), None)
    out = next((a.split("=", 1)[1] for a in argv
                if a.startswith("--export-filename=")), None)
    if os.environ.get("FAKE_INKSCAPE_FAIL") == kind:
        _fail(f"fake inkscape: simulated {kind} export failure")
    if out is None:
        _fail("fake inkscape: no --export-filename")
    if kind == "png":
        _png(out)
    elif kind == "pdf":
        with open(out, "wb") as fh:
            fh.write(b"%PDF-1.4\n% fake inkscape\n%%EOF\n")
    else:
        _fail(f"fake inkscape: unexpected export type {kind}")


def main():
    tool, argv = sys.argv[1], sys.argv[2:]
    _log(tool, argv)
    {"inkscape": inkscape}[tool](argv)


if __name__ == "__main__":
    main()
