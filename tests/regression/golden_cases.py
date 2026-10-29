"""The runs whose output is pinned in golden/manifest.json.

Every case is run by golden_driver.py, once against the baseline (or the
current code, when refreshing) by make_golden.py and once against the current
code by test_golden.py.  The driver adds `-c <config>` and `--out <dir>`.
Every case renders for real (render-without-inkscape); there is no stand-in
program any more.

Every case that renders passes --date explicitly: the example's [sample]
date is `today`, which would make the output depend on the day it ran.

Since the plain-white item every case names its variants explicitly, and
only the three that remain (overlay, overlay-flat, proof): the goldens are
generated from 823af58, the last commit with the coloured variants, whose
`--all`, `-v all` and default variant set still included them.  What
`--all`, `-v all` and the defaults mean now is pinned by
tests/acceptance/test_ac_plain_white.py instead.
"""

# The variants that survive plain-white, in their order.
PLAIN = "overlay,overlay-flat,proof"

# config: "example" (the layout's own shipped example) or a file in tests/data.
CASES = [
    # --- pure SVG, no external program involved (-f svg, --no-ink) ---------
    dict(id="sample", config="example",
         argv=["-a", "all", "-v", PLAIN, "--no-ink", "-f", "svg", "-d", "2026-09-05"]),
    dict(id="blank", config="example",
         argv=["-a", "all", "-v", PLAIN, "--no-ink", "-f", "svg",
               "-n", "", "-r", "", "-d", ""]),
    dict(id="filled", config="example",
         argv=["-a", "all", "-v", PLAIN, "--no-ink", "-f", "svg", "-n", "ヤン・ヤンセン",
               "-r", "2", "-d", "2024-07-01"]),
    dict(id="no-honorific", config="example",
         argv=["-a", "all", "-v", PLAIN, "--no-ink", "-f", "svg", "-n", "ヤン・ヤンセン",
               "-r", "shodan", "-d", "2026-12-31", "--honorific", ""]),
    dict(id="licence-rank", config="example",
         argv=["-a", "shihan,renshi", "-v", PLAIN, "--no-ink", "-f", "svg",
               "-r", "師範", "-n", "", "-d", ""]),
    dict(id="long-name", config="example",
         argv=["-a", "dan", "-v", "overlay-flat,proof", "-f", "svg",
               "-n", "アレクサンドル・ファン・デル・フェルデン",
               "-r", "10", "-d", "2020-10-20"]),
    dict(id="minimal-config", config="minimal.toml",
         argv=["-a", "all", "-v", PLAIN, "--no-ink", "-f", "svg"]),
    # dropped.toml still carries a `colour` per award: it must change nothing.
    dict(id="dropped-config", config="dropped.toml",
         argv=["-a", "all", "-v", PLAIN, "--no-ink", "-f", "svg"]),
    dict(id="dropped-config-rank", config="dropped.toml",
         argv=["-v", "overlay-flat,proof", "-f", "svg", "-r", "4", "-d", ""]),
    # --- rendering runs: the inked composite and the text layer it draws
    #     (the Inkscape calls they made are in the manifest as history) ------
    dict(id="inked", config="example",
         argv=["-a", "all", "-v", PLAIN, "-f", "pdf,png,svg",
               "-n", "", "-r", "", "-d", "2026-09-05"]),
    dict(id="inked-sample", config="example",
         argv=["-v", "overlay", "-d", "2026-09-05"]),
    # Was `supersample` (the same run with --supersample 2) until
    # remove-supersample took the flag away; see that item's acceptance.md.
    # The SVG and the text layer are the ones that case pinned.
    dict(id="inked-svg", config="example",
         argv=["-a", "dan", "-v", "overlay", "-f", "svg", "-d", ""]),
    dict(id="png-dpi", config="example",
         argv=["-a", "renshi", "-v", "proof,overlay-flat", "-f", "png",
               "--dpi", "150", "-d", ""]),
    dict(id="flat-pdf", config="example",
         argv=["-a", "dan", "-v", "overlay-flat,proof", "-f", "pdf", "-d", ""]),
]

# `--list` runs: only stdout matters.
LIST_CASES = [
    dict(id="overlay", config="example", argv=["-v", "overlay"]),
    dict(id="plain", config="example", argv=["-a", "all", "-v", PLAIN]),
    dict(id="plain-formats", config="example",
         argv=["-a", "all", "-v", PLAIN, "-f", "pdf,png,svg"]),
    dict(id="name", config="example", argv=["-v", "overlay", "-n", "ヤン・ヤンセン"]),
    dict(id="rank", config="example", argv=["-v", "overlay", "-r", "2"]),
    dict(id="rank-name", config="example",
         argv=["-v", "overlay", "-r", "nidan", "-n", "ヤン・ヤンセン"]),
    dict(id="name-odd-chars", config="example",
         argv=["-v", "overlay", "-n", "ヤン　ヤンセン/x:y"]),
    dict(id="name-spaces", config="example", argv=["-v", "overlay", "-n", "ヤン  ヤンセン"]),
    dict(id="suffix-empty", config="example", argv=["-v", "overlay", "--suffix", ""]),
    dict(id="suffix-given", config="example",
         argv=["-v", "overlay", "--suffix", "archive", "-n", "ヤン・ヤンセン"]),
    dict(id="all-cleared", config="example",
         argv=["-v", "overlay", "-n", "", "-r", "", "-d", ""]),
    dict(id="date-only", config="example", argv=["-v", "overlay", "-d", "2026-09-05"]),
    dict(id="shihan", config="example",
         argv=["-a", "shihan", "-v", "proof,overlay-flat"]),
    dict(id="licence-rank", config="example",
         argv=["-v", "overlay", "-r", "師範", "-a", "renshi"]),
    dict(id="minimal", config="minimal.toml", argv=["-a", "all", "-v", PLAIN]),
    dict(id="dropped", config="dropped.toml", argv=["-v", PLAIN, "-f", "png,pdf"]),
]
