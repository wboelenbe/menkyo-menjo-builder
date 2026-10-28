"""The runs whose output is pinned in golden/manifest.json.

Every case is run by golden_driver.py, once against the baseline (or the
current code, when refreshing) by make_golden.py and once against the current
code by test_golden.py.  The driver adds `-c <config>` and `--out <dir>`, and
puts the stand-in inkscape / gs first on PATH.

Every case that renders passes --date explicitly: the example's [sample]
date is `today`, which would make the output depend on the day it ran.
"""

# config: "example" (the layout's own shipped example) or a file in tests/data.
CASES = [
    # --- pure SVG, no external program involved (-f svg, --no-ink) ---------
    dict(id="sample", config="example",
         argv=["--all", "--no-ink", "-f", "svg", "-d", "2026-09-05"]),
    dict(id="blank", config="example",
         argv=["--all", "--no-ink", "-f", "svg", "-n", "", "-r", "", "-d", ""]),
    dict(id="filled", config="example",
         argv=["--all", "--no-ink", "-f", "svg", "-n", "ヤン・ヤンセン",
               "-r", "2", "-d", "2024-07-01"]),
    dict(id="no-honorific", config="example",
         argv=["--all", "--no-ink", "-f", "svg", "-n", "ヤン・ヤンセン",
               "-r", "shodan", "-d", "2026-12-31", "--honorific", ""]),
    dict(id="licence-rank", config="example",
         argv=["-a", "shihan,renshi", "-v", "all", "--no-ink", "-f", "svg",
               "-r", "師範", "-n", "", "-d", ""]),
    dict(id="long-name", config="example",
         argv=["-a", "dan", "-v", "overlay-flat,proof", "-f", "svg",
               "-n", "アレクサンドル・ファン・デル・フェルデン",
               "-r", "10", "-d", "2020-10-20"]),
    dict(id="minimal-config", config="minimal.toml",
         argv=["--all", "--no-ink", "-f", "svg"]),
    dict(id="dropped-config", config="dropped.toml",
         argv=["--all", "--no-ink", "-f", "svg"]),
    dict(id="dropped-config-rank", config="dropped.toml",
         argv=["-v", "overlay-flat,proof", "-f", "svg", "-r", "4", "-d", ""]),
    # --- through the stand-in inkscape / gs: the inked composite, the text
    #     layer handed to Inkscape, and every call made to either program ---
    dict(id="inked", config="example",
         argv=["--all", "-f", "pdf,png,svg", "--press", "-n", "", "-r", "", "-d", "2026-09-05"]),
    dict(id="inked-default", config="example", argv=["-d", "2026-09-05"]),
    dict(id="supersample", config="example",
         argv=["-a", "dan", "-v", "overlay", "-f", "svg", "--supersample", "2",
               "-d", ""]),
    dict(id="png-dpi", config="example",
         argv=["-a", "renshi", "-v", "proof,full-flat,overlay-flat", "-f", "png",
               "--dpi", "150", "-d", ""]),
    dict(id="flat-press", config="example",
         argv=["-a", "dan", "-v", "overlay-flat,full-flat,proof", "-f", "pdf",
               "--press", "-d", ""]),
]

# `--list` runs: only stdout matters.
LIST_CASES = [
    dict(id="default", config="example", argv=[]),
    dict(id="all", config="example", argv=["--all"]),
    dict(id="all-press-formats", config="example",
         argv=["--all", "--press", "-f", "pdf,png,svg"]),
    dict(id="name", config="example", argv=["-n", "ヤン・ヤンセン"]),
    dict(id="rank", config="example", argv=["-r", "2"]),
    dict(id="rank-name", config="example", argv=["-r", "nidan", "-n", "ヤン・ヤンセン"]),
    dict(id="name-odd-chars", config="example", argv=["-n", "ヤン　ヤンセン/x:y"]),
    dict(id="name-spaces", config="example", argv=["-n", "ヤン  ヤンセン"]),
    dict(id="suffix-empty", config="example", argv=["--suffix", ""]),
    dict(id="suffix-given", config="example",
         argv=["--suffix", "archive", "-n", "ヤン・ヤンセン"]),
    dict(id="all-cleared", config="example", argv=["-n", "", "-r", "", "-d", ""]),
    dict(id="date-only", config="example", argv=["-d", "2026-09-05"]),
    dict(id="shihan-press", config="example",
         argv=["-a", "shihan", "-v", "proof,full,overlay-flat", "--press"]),
    dict(id="licence-rank", config="example", argv=["-r", "師範", "-a", "renshi"]),
    dict(id="minimal-press", config="minimal.toml", argv=["--all", "--press"]),
    dict(id="dropped", config="dropped.toml", argv=["-v", "all", "-f", "png,pdf"]),
]
