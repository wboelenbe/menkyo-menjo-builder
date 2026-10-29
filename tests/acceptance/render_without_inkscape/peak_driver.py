"""Run the menkyo command in this process and report its own peak RSS.

    python peak_driver.py REPORT.json -- MENKYO ARGS...

For AC-26's automated guard (docs/work/render-without-inkscape/acceptance.md).
On Linux the peak is VmHWM, which starts afresh at exec; ru_maxrss would
carry the parent's (pytest's) peak across the fork.  On macOS it is
ru_maxrss, in bytes.  The caller passes -c and an isolated HOME.
"""

import json
import resource
import sys
from pathlib import Path


def _peak_bytes():
    if sys.platform.startswith("linux"):
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) * 1024
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r if sys.platform == "darwin" else r * 1024


def main():
    report = sys.argv[1]
    assert sys.argv[2] == "--"
    from menkyo import build_diploma
    code = 0
    try:
        build_diploma.cli(sys.argv[3:])
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
    Path(report).write_text(json.dumps({"peak_rss": _peak_bytes(), "exit": code}))
    sys.exit(code)


if __name__ == "__main__":
    main()
