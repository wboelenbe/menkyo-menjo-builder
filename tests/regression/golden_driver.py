"""Run the generator's main() once, from a given source tree, and record stdout.

    python -I golden_driver.py SPEC.json

SPEC holds: layout ("flat" for the pre-package tree, src/build_diploma.py;
"package" for src/menkyo/), src (the src/ directory), config, argv, out, and
result (where to write {"stdout", "exit"}).  It calls main() rather than the
`menkyo` command because the baseline has no cli(); the CLI wrapper is tested
separately.  Kept free of imports from tests/ so it runs against any tree.
"""

import contextlib
import io
import json
import sys


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        spec = json.load(fh)
    sys.path.insert(0, spec["src"])
    if spec["layout"] == "flat":
        import build_diploma as bd
    else:
        from menkyo import build_diploma as bd

    argv = ["-c", spec["config"], *spec["argv"], "--out", spec["out"]]
    buf = io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf):
            bd.main(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, (int, type(None))) else str(e.code)
    with open(spec["result"], "w", encoding="utf-8") as fh:
        json.dump({"stdout": buf.getvalue(), "exit": code}, fh, ensure_ascii=False)


if __name__ == "__main__":
    main()
