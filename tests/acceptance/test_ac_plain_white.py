"""plain-white: drop the coloured variants, the drawn border, the award
colours, the paper tint and the press conversions; keep overlay, overlay-flat
and proof on plain white paper.

See docs/work/plain-white/acceptance.md.  The AC numbers here are that
item's (as agreed, see its "Agreement").  AC-8 is
tests/regression/test_golden.py, AC-19 is
test_ac_render.py and AC-22 is the rest of the suite.  Runs use the stand-in
inkscape and the shipped example or a configuration the test writes.

This file is the one place that spells out the words the rest of the
repository may no longer contain, so it excludes itself from that scan.
"""

import dataclasses
import importlib.util
import inspect
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import support
from menkyo import build_diploma as bd
from menkyo import config as config_mod
from menkyo import paths

THIS = Path(__file__).resolve()
EX = str(support.EXAMPLE)
BEFORE = "823af58"          # HEAD when the item was planned

PLAIN = ["overlay", "overlay-flat", "proof"]
AWARDS = ["dan", "shihan", "renshi"]
CHOOSE = "choose from: overlay, overlay-flat, proof (or 'all')"


# ----------------------------------------------------------------- helpers ----
def _git(*args):
    if not shutil.which("git") or not (support.REPO / ".git").exists():
        return None
    r = subprocess.run(["git", "-C", str(support.REPO), *args],
                       capture_output=True, text=True)
    return r if r.returncode == 0 else None


_WALK_SKIP = {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist",
              "crest", "ref"}


def repo_files():
    """Tracked and untracked-but-not-ignored files, relative to REPO; without
    git (the Docker image), a walk that skips what .gitignore would."""
    r = _git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if r is not None:
        names = [n for n in r.stdout.split("\0") if n]
        return sorted({n for n in names if (support.REPO / n).is_file()})
    out = []
    for root, dirs, files in os.walk(support.REPO):
        dirs[:] = [d for d in dirs if d not in _WALK_SKIP]
        for f in files:
            if f == "dojo.toml" or f.endswith(".pyc"):
                continue
            out.append(str(Path(root, f).relative_to(support.REPO)))
    return sorted(out)


def text_of(rel):
    try:
        return (support.REPO / rel).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def listing(args, home, tmp_path, json=False):
    r = support.run_menkyo(["-c", EX, "--list", *args, f"--out={tmp_path / 'o'}"]
                           + (["--json"] if json else []),
                           support.isolated_env(home), tmp_path)
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / "o").exists()
    return r.stdout.splitlines()


def _cli(argv, capsys):
    """cli() in-process; (exit code, events, stderr)."""
    with pytest.raises(SystemExit) as e:
        bd.cli(argv)
    cap = capsys.readouterr()
    return e.value.code, support.events(cap.out), cap.err


def _one_error(code, ev):
    kinds = [e["event"] for e in ev]
    assert code == 1
    assert kinds and kinds[-1] == "error" and kinds.count("error") == 1, kinds
    assert "done" not in kinds
    return ev[-1]["message"]


def _tree(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def _help(home):
    env = support.isolated_env(home, COLUMNS="1000")        # no wrapping
    r = support.run_menkyo(["-c", EX, "--help"], env, support.REPO)
    assert r.returncode == 0, r.stderr
    return r.stdout


# ------------------------------------------------------------------ AC-1 ----
def test_ac1_the_variants_are_the_plain_three():
    assert list(bd.VARIANTS) == PLAIN
    assert [v for v, kw in bd.VARIANTS.items() if kw.get("inked")] == ["overlay"]


# `--all` overrides `-a` (unchanged, AC-22), so it is not combined with
# `-a dan` here; test_ac1_all_flag_lists_every_award_and_variant covers it.
@pytest.mark.parametrize("flags", [["-v", "all"], ["-v", " ALL "], ["--variants=all"]])
def test_ac1_all_means_the_plain_three(flags, home, tmp_path):
    got = listing(["-a", "dan", *flags, "-f", "pdf"], home, tmp_path)
    assert got == [f"dan-{v}-sample.pdf" for v in PLAIN]


def test_ac1_all_flag_lists_every_award_and_variant(home, tmp_path):
    got = listing(["--all"], home, tmp_path)
    assert got == [f"{a}-{v}-sample.pdf" for a in AWARDS for v in PLAIN]


def test_ac1_all_writes_what_the_explicit_list_writes(fake_tools, tmp_path):
    common = ["-c", EX, "--no-ink", "-f", "svg", "-d", "2026-09-05"]
    bd.main(common + ["--all", f"--out={tmp_path / 'a'}"])
    bd.main(common + ["-a", "dan,shihan,renshi", "-v", ",".join(PLAIN),
                      f"--out={tmp_path / 'b'}"])
    a, b = _tree(tmp_path / "a"), _tree(tmp_path / "b")
    assert sorted(a) == sorted(f"{x}-{v}-sample.svg" for x in AWARDS for v in PLAIN)
    assert a == b


# ------------------------------------------------------------------ AC-2 ----
REMOVED = [
    ("full", "full"), ("full-cream", "full-cream"), ("full-flat", "full-flat"),
    ("overlay,full", "full"), ("proof,full-cream,full-flat", "full-cream, full-flat"),
]


@pytest.mark.parametrize("variants, bad", REMOVED, ids=[r[0] for r in REMOVED])
def test_ac2_removed_variants_are_rejected(variants, bad, fake_tools, home, tmp_path):
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", EX, "-a", "dan", "-v", variants, "-d", "",
                            f"--out={out}"], fake_tools.env(home), tmp_path)
    assert r.returncode == 1 and r.stdout == ""
    assert f"unknown variant: {bad}\n{CHOOSE}" in r.stderr
    assert "Traceback" not in r.stderr
    assert not out.exists(), "nothing may be written before the error"
    assert fake_tools.calls() == []


@pytest.mark.parametrize("variants, bad", REMOVED, ids=[r[0] for r in REMOVED])
def test_ac2_removed_variants_are_json_errors(variants, bad, fake_tools, tmp_path, capsys):
    out = tmp_path / "out"
    code, ev, err = _cli(["-c", EX, "-a", "dan", "-v", variants, "-d", "",
                          f"--out={out}", "--json"], capsys)
    assert _one_error(code, ev) == f"unknown variant: {bad}\n{CHOOSE}"
    assert ev == [ev[-1]] and err == ""
    assert not out.exists()


# ------------------------------------------------------------------ AC-3 ----
@pytest.mark.parametrize("flag", ["--press", "--pre", "--pr"])
def test_ac3_press_is_rejected(flag, fake_tools, home, tmp_path):
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", EX, "-a", "dan", "-v", "overlay-flat", flag, "-d", "",
                            f"--out={out}"], fake_tools.env(home), tmp_path)
    assert r.returncode == 2 and r.stdout == ""
    assert r.stderr.startswith("usage: menkyo")
    assert f"unrecognized arguments: {flag}" in r.stderr
    assert not out.exists()
    assert fake_tools.calls() == []


@pytest.mark.parametrize("flag", ["--press", "--pre"])
def test_ac3_press_is_a_json_error(flag, fake_tools, tmp_path, capsys):
    out = tmp_path / "out"
    code, ev, err = _cli(["-c", EX, "-a", "dan", "-v", "overlay-flat", flag, "-d", "",
                          f"--out={out}", "--json"], capsys)
    assert f"unrecognized arguments: {flag}" in _one_error(code, ev)
    assert ev == [ev[-1]] and err == ""
    assert not out.exists()


def test_ac3_press_is_rejected_by_list_too(home, tmp_path):
    r = support.run_menkyo(["-c", EX, "--list", "--press"], support.isolated_env(home),
                           tmp_path)
    assert r.returncode == 2 and r.stdout == ""
    assert "unrecognized arguments: --press" in r.stderr


# ------------------------------------------------------------------ AC-4 ----
# Open question 1, decided by the user: `overlay` alone.
def test_ac4_default_variants():
    assert bd.DEFAULT_VARIANTS == ["overlay"]
    assert bd.DEFAULT_FORMATS == ["pdf"]


def test_ac4_default_list(home, tmp_path):
    assert listing([], home, tmp_path) == [f"{a}-overlay-sample.pdf" for a in AWARDS]


def test_ac4_default_run(fake_tools, home, tmp_path):
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", EX, "-d", "2026-09-05", f"--out={out}", "--json"],
                           fake_tools.env(home), tmp_path)
    assert r.returncode == 0, r.stderr
    ev = support.events(r.stdout)
    progress = [e for e in ev if e["event"] == "progress"]
    assert [(p["award"], p["variant"], p["stage"]) for p in progress] == [
        (a, "overlay", s) for a in AWARDS for s in ("text", "ink", "pdf")]
    assert all(p["total"] == 9 for p in progress)
    assert ev[-1] == {"event": "done", "out": str(out),
                      "files": [str(out / f"{a}-overlay-sample.pdf") for a in AWARDS]}


# ------------------------------------------------------------------ AC-5 ----
def test_ac5_a_full_run_needs_only_inkscape(fake_tools, home, tmp_path):
    """Every variant, every format, with nothing but (a stand-in) Inkscape."""
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", EX, "--all", "-f", "pdf,png,svg", "-d", "2026-09-05",
                            f"--out={out}", "--json"], fake_tools.env(home), tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert {c["tool"] for c in fake_tools.calls()} == {"inkscape"}
    names = sorted(os.listdir(out))
    assert not [n for n in names if n.endswith(("-K.pdf", "-CMYK.pdf"))], names
    expected = set()
    for a in AWARDS:
        for v in PLAIN:
            expected |= {f"{a}-{v}-sample.{e}" for e in ("pdf", "png", "svg")}
        expected.add(f"{a}-overlay-sample-textlayer.png")
    assert set(names) == expected


def test_ac5_ghostscript_is_not_a_known_tool():
    assert "gs" not in paths._INSTALL_HINT
    assert set(paths._INSTALL_HINT) == {"inkscape"}


# ------------------------------------------------------------------ AC-6 ----
def test_ac6_stages():
    assert bd.STAGES == {"text": "rendering the text", "ink": "grading the ink",
                         "pdf": "writing the PDF", "png": "writing the PNG"}
    assert list(bd.STAGES) == ["text", "ink", "pdf", "png"]


TOTALS = [
    # (flags, expected total, expected number of files)
    (["--all", "-f", "pdf,png"], 3 * (4 + 2 + 2), 3 * 6),
    (["--all", "--no-ink"], 3 * 3, 9),
    (["--all", "-f", "pdf,png,svg"], 3 * (4 + 2 + 2), 3 * (4 + 3 + 3)),
    (["-a", "dan", "-v", "all", "-f", "svg"], 2, 4),
    (["-a", "renshi", "-v", "all", "--no-ink", "-f", "png"], 3, 3),
]


@pytest.mark.parametrize("flags, total, nfiles", TOTALS, ids=[" ".join(t[0]) for t in TOTALS])
def test_ac6_step_totals(flags, total, nfiles, fake_tools, home, tmp_path):
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", EX, *flags, "-d", "2026-09-05", f"--out={out}", "--json"],
                           fake_tools.env(home), tmp_path)
    assert r.returncode == 0, r.stderr
    ev = support.events(r.stdout)
    progress = [e for e in ev if e["event"] == "progress"]
    assert [p["step"] for p in progress] == list(range(1, total + 1))
    assert all(p["total"] == total for p in progress)
    assert {p["stage"] for p in progress} <= set(bd.STAGES)
    files = [e["path"] for e in ev if e["event"] == "file"]
    assert len(files) == nfiles and ev[-1]["files"] == files


# ------------------------------------------------------------------ AC-7 ----
def test_ac7_list_every_format(home, tmp_path):
    got = listing(["--all", "-f", "pdf,png,svg"], home, tmp_path)
    assert got == [f"{a}-{v}-sample.{e}" for a in AWARDS for v in PLAIN
                   for e in ("pdf", "png", "svg")]


def test_ac7_list_json_is_the_same(home, tmp_path):
    plain = listing(["--all", "-f", "pdf,png"], home, tmp_path)
    js = support.events("\n".join(listing(["--all", "-f", "pdf,png"], home, tmp_path,
                                          json=True)))
    assert [e["file"] for e in js] == plain
    assert all(set(e) == {"event", "file"} and e["event"] == "planned" for e in js)
    assert len(plain) == 18


# ------------------------------------------------------------------ AC-9 ----
# Open question 2, agreed: accepted and ignored.
def _example_without_colour():
    text = support.EXAMPLE.read_text(encoding="utf-8")
    return "\n".join(l for l in text.splitlines()
                     if not re.match(r"\s*colour\s*=", l)) + "\n"


def _with_colour(value):
    return re.sub(r"^(grade_column = \w+.*)$", rf"\1\ncolour = {value}",
                  _example_without_colour(), flags=re.M)


COLOURS = ['"#8a6a33"', '"#ff0000"', '"not a colour"', '""', "5"]


@pytest.mark.parametrize("value", COLOURS)
def test_ac9_colour_is_accepted_and_ignored(value, fake_tools, tmp_path):
    plain = tmp_path / "plain.toml"
    plain.write_text(_example_without_colour(), encoding="utf-8")
    coloured = tmp_path / "coloured.toml"
    coloured.write_text(_with_colour(value), encoding="utf-8")
    assert coloured.read_text(encoding="utf-8").count("\ncolour = ") == 3

    a, b = config_mod.load(str(plain)), config_mod.load(str(coloured))
    a.source = b.source = ""
    assert a == b

    for cfg, out in ((plain, "a"), (coloured, "b")):
        bd.main(["-c", str(cfg), "--all", "--no-ink", "-f", "svg", "-d", "2026-09-05",
                 f"--out={tmp_path / out}"])
    assert _tree(tmp_path / "a") == _tree(tmp_path / "b")
    assert len(_tree(tmp_path / "a")) == 9


def test_ac9_colour_draws_no_warning(fake_tools, home, tmp_path):
    coloured = tmp_path / "coloured.toml"
    coloured.write_text(_with_colour('"#8a336f"'), encoding="utf-8")
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", coloured, "-a", "dan", "-v", "overlay-flat", "-d", "",
                            f"--out={out}", "--json"], fake_tools.env(home), tmp_path)
    assert r.returncode == 0 and r.stderr == ""
    assert [e["event"] for e in support.events(r.stdout)] == ["progress", "file", "done"]


def test_ac9_an_award_has_no_colour():
    names = [f.name for f in dataclasses.fields(config_mod.Award)]
    assert names == ["slug", "heading", "formula", "grade_column"]


def test_ac9_save_writes_no_colour(tmp_path):
    cfg = config_mod.load(EX)
    path = config_mod.save(cfg, str(tmp_path / "dojo.toml"))
    text = Path(path).read_text(encoding="utf-8")
    assert "colour" not in text
    back = config_mod.load(path)
    assert [(a.slug, a.heading, a.formula, a.grade_column) for a in back.awards] == \
        [(a.slug, a.heading, a.formula, a.grade_column) for a in cfg.awards]


# ----------------------------------------------------------------- AC-10 ----
def test_ac10_example_config_has_no_colours():
    text = support.EXAMPLE.read_text(encoding="utf-8")
    assert not re.search(r"colou?r", text, re.I)
    for gone in ("full", "cream", "drawn border", "tint"):
        assert gone not in text.lower(), gone


def test_ac10_example_config_still_round_trips(home, tmp_path):
    r = support.run_menkyo(["--example-config"], support.isolated_env(home), tmp_path)
    assert r.returncode == 0
    assert r.stdout.encode("utf-8") == support.EXAMPLE.read_bytes()
    c = config_mod.load(EX)
    assert c.slugs == AWARDS
    assert (c.stock_border, c.safe_inset, c.text_drop) == (22.0, 38.0, 0.05)


# ----------------------------------------------------------------- AC-11 ----
def test_ac11_paper_keys_still_drive_the_proof(fake_tools, tmp_path):
    cfg = tmp_path / "paper.toml"
    cfg.write_text(_example_without_colour().replace("border = 22.0", "border = 10.0")
                   .replace("safe_inset = 38.0", "safe_inset = 20.0"), encoding="utf-8")
    assert config_mod.load(str(cfg)).stock_border == 10.0
    bd.main(["-c", str(cfg), "-a", "dan", "-v", "proof", "-f", "svg", "-d", "",
             f"--out={tmp_path / 'o'}"])
    svg = (tmp_path / "o" / "dan-proof-sample.svg").read_text(encoding="utf-8")
    assert '<rect x="10.0" y="10.0" width="400.0" height="277.0"' in svg
    assert '<rect x="20.0" y="20.0" width="380.0" height="257.0"' in svg


# ----------------------------------------------------------------- AC-12 ----
def test_ac12_help(home):
    text = _help(home)
    assert "comma-separated: overlay,overlay-flat,proof (default: overlay)" in text
    for gone in ("--press", "full-cream", "full-flat", "-v full", "CMYK", "-K ", " -K",
                 "printer", "cream", "border", "stock", "bought"):
        assert gone not in text, gone
    for kept in ("--awards", "--variants", "--formats", "--no-ink", "--name", "--rank",
                 "--date", "--honorific", "--suffix", "--dpi", "--all",
                 "--out", "--clean", "--list", "--json", "--version", "--example-config",
                 "--config"):
        assert kept in text, kept


# ----------------------------------------------------------------- AC-13 ----
def test_ac13_the_border_module_is_gone():
    assert not (support.PACKAGE / "border.py").exists()
    assert importlib.util.find_spec("menkyo.border") is None
    assert not hasattr(bd, "border")


def test_ac13_no_colour_machinery_left():
    for name in ("SEPIA", "CREAM", "CREST_C_BORDERED"):
        assert not hasattr(bd, name), name
    for fn in (bd.document, bd.build_one, bd.render):
        params = set(inspect.signature(fn).parameters)
        for gone in ("drawn_border", "paper", "border_colour", "press", "convert"):
            assert gone not in params, (fn.__name__, gone)
    for kw in bd.VARIANTS.values():
        assert set(kw) <= {"inked", "guides"}, kw


@pytest.mark.slow
def test_ac13_wheel_has_no_border_module(dist):
    with zipfile.ZipFile(dist["wheel"]) as z:
        names = z.namelist()
    assert "menkyo/build_diploma.py" in names
    assert "menkyo/border.py" not in names


# ----------------------------------------------------------------- AC-14 ----
# What may no longer be mentioned anywhere but the history.  Case-insensitive
# unless (?-i:...).
FORBIDDEN = [
    r"full-cream", r"full-flat", r"(?:-v|--variants)[ =]['\"]?full\b",
    r"(?<![\w-])--press\b", r"\bpress=", r"[\"'`]press[\"'`]", r"converting for the press",
    r"\bCMYK\b", r"-K\.pdf", r"[\"'`]-K[\"'`]", r"PDFSETTINGS", r"prepress", r"K-only",
    r"inkcov", r"ghostscript", r"\bgs\b", r"FAKE_GS",
    r"\bborder\.py\b", r"border_svg", r"from \. import [^\n]*\bborder\b",
    r"\bimport border\b", r"drawn[_ ]border", r"border_colou?r", r"engraved border",
    r"CREST_C_BORDERED", r"(?-i:\bSEPIA\b)", r"\bcream\b", r"paper tint",
    r"#f7f1e3", r"#8a6a33", r"#8a336f",
    # plain white paper only (open question 4): the bought-stock route ends.
    # 賞状 on its own stays allowed.
    r"賞状用紙", r"\bbought\b",
]
# In the package's Python only: the award colour.  (A bare `gs` is caught
# everywhere by FORBIDDEN, since review R-3.)
FORBIDDEN_IN_SRC = [r"[\"']colour[\"']", r"\.colour\b", r"\bcolour\s*="]
SCAN_EXCLUDE_FILES = {"DECISIONS.md", str(THIS.relative_to(support.REPO))}
# .claude/ is the agents' configuration, which no item edits (open question 9).
SCAN_EXCLUDE_DIRS = ("docs/work/", ".claude/")


def _scan(patterns, files):
    pattern = re.compile("|".join(f"(?:{p})" for p in patterns), re.I)
    hits = []
    for rel in files:
        text = text_of(rel)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            m = pattern.search(line)
            if m:
                hits.append(f"{rel}:{n}: {m.group(0)!r} in {line.strip()[:100]!r}")
    return hits


def test_ac14_no_references_left():
    files = [f for f in repo_files()
             if f not in SCAN_EXCLUDE_FILES and not f.startswith(SCAN_EXCLUDE_DIRS)]
    hits = _scan(FORBIDDEN, files)
    assert hits == [], "\n" + "\n".join(hits)


def test_ac14_no_colour_or_gs_in_the_package():
    files = [f for f in repo_files() if f.startswith("src/menkyo/") and f.endswith(".py")]
    assert "src/menkyo/build_diploma.py" in files
    hits = _scan(FORBIDDEN_IN_SRC, files)
    assert hits == [], "\n" + "\n".join(hits)


# ----------------------------------------------------------------- AC-15 ----
def _readme():
    return (support.REPO / "README.md").read_text(encoding="utf-8")


def _section(text, heading):
    part = text.split(f"\n## {heading}\n", 1)
    assert len(part) == 2, heading
    return part[1].split("\n## ", 1)[0]


def test_ac15_readme_variants_table():
    rows = re.findall(r"^\| `([\w-]+)` \|", _section(_readme(), "Variants"), re.M)
    assert rows == PLAIN


def test_ac15_readme_options_table():
    options = _section(_readme(), "Options")
    row = next(l for l in options.splitlines() if l.startswith("| `-v`"))
    assert "(default: `overlay`)" in row and "full" not in row


def test_ac15_readme_config_example_has_no_colour():
    block = _readme().split("```toml\n", 1)[1].split("```", 1)[0]
    assert "colour" not in block
    assert "[paper]" in block and "border" in block and "safe_inset" in block


def test_ac15_readme_stages_and_requirements():
    readme = _readme()
    package = _section(readme, "As a package")
    stage_line = next(l for l in package.splitlines() if l.startswith("`stage` is one of"))
    assert re.findall(r"`(\w+)`", stage_line)[1:] == ["text", "ink", "pdf", "png"]
    assert "Inkscape" in _section(readme, "Quick start")
    headings = [l for l in readme.splitlines() if l.startswith("## ")]
    printing = [h[3:] for h in headings if "printing" in h.lower()]
    assert printing, headings
    assert not [h for h in printing if re.search(r"border|stock", h, re.I)], printing
    assert any("white" in _section(readme, h).lower() for h in printing), printing


# ----------------------------------------------------------------- AC-16 ----
# The item that removed the flag (its acceptance.md, AC-10, user-approved) rewords the last two bullets of the 2026-09-05 "Output, and
# the ... cap" entry into the past tense.  Those bullets, and nothing else,
# are left out of the byte-for-byte history comparison.  The flag's name is
# spelled in two halves: that item's AC-11 bans it from the repository.
_REWORDED_BULLETS = re.compile(
    r"^- \*\*`--super" r"sample` .*?(?=\n\n## 2026-09-05 — Printing the three hand slots\n)",
    re.M | re.S)


def _without_reworded_bullets(text):
    stripped, n = _REWORDED_BULLETS.subn("<reworded bullets>", text, count=1)
    assert n == 1, "the reworded 2026-09-05 bullets were not found"
    return stripped


def _entries():
    text = (support.REPO / "DECISIONS.md").read_text(encoding="utf-8")
    return text.split("\n## Open\n", 1)


def test_ac16_decisions_entry_appended_history_untouched():
    """History up to 823af58 is untouched, and this item's entry is among the
    entries after it, found by its heading: other items (ink-memory) may
    append theirs too, before or after it."""
    entries, _ = _entries()
    old = _git("show", f"{BEFORE}:DECISIONS.md")
    if old is not None:
        old_entries = old.stdout.split("\n## Open\n", 1)[0]
        kept = _without_reworded_bullets(old_entries)
        now = _without_reworded_bullets(entries)
        assert now.startswith(kept), "an earlier entry was changed"
        new = now[len(kept):]
    else:
        new = entries                   # no git (the Docker image)
    blocks = [b for b in re.split(r"^(?=## )", new, flags=re.M) if b.startswith("## ")]
    mine = [b for b in blocks
            if re.match(r"## \d{4}-\d{2}-\d{2} — ", b)
            and "white" in b.splitlines()[0].lower()]
    assert len(mine) == 1, [b.splitlines()[0] for b in blocks]
    for word in ("--press", "Ghostscript", "overlay", "proof", "colour", "portal"):
        assert word in mine[0], word


def test_ac16_open_items_retired():
    _, open_ = _entries()
    items = re.findall(r"^- \*\*(.+?)\*\*", open_, re.M)
    for gone in ("Plain white only", "press files", "drawn border", "Source the 賞状用紙"):
        assert not [i for i in items if gone in i], (gone, items)
    for kept in ("Render without Inkscape", "An annotated version in Dutch"):
        assert [i for i in items if i.startswith(kept)], (kept, items)


# ----------------------------------------------------------------- AC-17 ----
def test_ac17_claude_md_pyproject_and_tests_readme():
    claude = (support.REPO / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Inkscape renders" in claude
    pyproject = (support.REPO / "pyproject.toml").read_text(encoding="utf-8")
    comment = next(l for l in pyproject.splitlines() if "system programs" in l)
    assert "inkscape" in comment.lower()
    marker = next(l for l in pyproject.splitlines() if l.strip().startswith('"render:'))
    assert "Inkscape" in marker
    tests_readme = (support.TESTS / "README.md").read_text(encoding="utf-8")
    assert "823af58" in tests_readme


# ----------------------------------------------------------------- AC-18 ----
def _apt_packages(text):
    m = re.search(r"apt-get install -y --no-install-recommends \\\s*\n((?:.*\\\s*\n)*.*)",
                  text)
    assert m, "no apt-get install"
    return set(re.findall(r"[a-z][\w.+-]+", m.group(1).split("&&")[0]))


def test_ac18_test_image_has_no_ghostscript():
    df = (support.TESTS / "docker" / "Dockerfile").read_text(encoding="utf-8")
    pkgs = _apt_packages(df)
    assert {"inkscape", "poppler-utils", "fontconfig", "fonts-noto-cjk"} <= pkgs, pkgs
    assert "ghostscript" not in pkgs
    assert "REQUIRE_RENDER=1" in df


def test_ac18_workflow_has_no_ghostscript():
    wf = (support.REPO / ".github" / "workflows" / "package.yml").read_text(encoding="utf-8")
    pkgs = _apt_packages(wf)
    assert {"inkscape", "poppler-utils", "fontconfig", "fonts-noto-cjk"} <= pkgs, pkgs
    assert "ghostscript" not in pkgs
    smoke = wf.split("Smoke test the installed wheel", 1)[1]
    assert re.search(r"-v overlay,overlay-flat\b", smoke)
    assert "pdffonts out/dan-overlay-flat-sample.pdf" in smoke


# ----------------------------------------------------------------- AC-20 ----
@pytest.mark.slow
def test_ac20_installed_wheel(installed, fake_tools, home, tmp_path):
    """From outside the checkout: the same contract as from the checkout."""
    exe = [str(installed["menkyo"])]
    env = fake_tools.env(home)
    site = next(installed["venv"].glob("lib/python*/site-packages"))
    assert not (site / "menkyo" / "border.py").exists()

    r = support.run_menkyo(["--list", "--all"], env, tmp_path, exe=exe)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == [f"{a}-{v}-sample.pdf" for a in AWARDS for v in PLAIN]

    r = support.run_menkyo(["--list"], env, tmp_path, exe=exe)
    assert r.stdout.splitlines() == [f"{a}-overlay-sample.pdf" for a in AWARDS]

    r = support.run_menkyo(["-a", "dan", "-v", "full", "--json"], env, tmp_path, exe=exe)
    assert r.returncode == 1
    assert support.events(r.stdout) == [
        {"event": "error", "message": f"unknown variant: full\n{CHOOSE}"}]

    r = support.run_menkyo(["-a", "dan", "--press"], env, tmp_path, exe=exe)
    assert r.returncode == 2 and "unrecognized arguments: --press" in r.stderr

    r = support.run_menkyo(["--help"], support.isolated_env(home, COLUMNS="1000"),
                           tmp_path, exe=exe)
    assert "--press" not in r.stdout
    assert "overlay,overlay-flat,proof (default: overlay)" in r.stdout
    assert fake_tools.calls() == []


# ----------------------------------------------------------------- AC-21 ----
def _runs(mask, axis):
    """Lengths of the runs of True along `axis` (1: rows, 0: columns)."""
    import numpy as np
    m = mask if axis == 1 else mask.T
    out = []
    for line in m:
        d = np.diff(np.concatenate(([0], line.astype(int), [0])))
        starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
        out += list(ends - starts)
    return out


def test_ac21_readme_image_is_plain_white():
    """docs/three_up.png: the default overlay PNGs of the example config,
    flattened onto white, three sheets side by side, 1890 x 455, each with a
    1 px light-grey outline and at least 4 px of white around it.  No sepia
    or purple border and no cream are left."""
    import numpy as np
    from PIL import Image
    path = support.REPO / "docs" / "three_up.png"
    assert path.is_file()
    assert "docs/three_up.png" in _readme()
    with Image.open(path) as im:
        assert im.size == (1890, 455)
        rgb = np.asarray(im.convert("RGB")).astype(int)
    lo, hi = rgb.min(axis=2), rgb.max(axis=2)
    chroma = hi - lo
    # at least 4 px of white all round the image (and so at its corners)
    frame = np.ones(lo.shape, bool)
    frame[4:-4, 4:-4] = False
    assert lo[frame].min() >= 245, int(lo[frame].min())
    # no colour anywhere: no border, no tint
    assert (chroma > 24).mean() < 0.001, float((chroma > 24).mean())
    # black text
    assert (hi < 80).sum() > 1000, "no black text in the image"
    # three outlined sheets: light grey, long straight runs, top and bottom
    # edges of three sheets across, left and right edges of three sheets down
    grey = (lo >= 120) & (hi <= 240) & (chroma <= 12)
    assert sum(1 for r in _runs(grey, 1) if r >= 300) >= 6, "sheet outlines (horizontal)"
    assert sum(1 for r in _runs(grey, 0) if r >= 200) >= 6, "sheet outlines (vertical)"


# ----------------------------------------------------------------- AC-23 ----
def test_ac23_version_is_0_2_0(home, tmp_path):
    assert support.project_version() == "0.2.0"
    r = support.run_menkyo(["--version"], support.isolated_env(home), tmp_path)
    assert (r.returncode, r.stdout) == (0, "menkyo 0.2.0\n")


@pytest.mark.slow
def test_ac23_wheel_is_0_2_0(dist, installed, home, tmp_path):
    assert dist["wheel"].name == "menkyo-0.2.0-py3-none-any.whl"
    r = support.run_menkyo(["--version"], support.isolated_env(home), tmp_path,
                           exe=[str(installed["menkyo"])])
    assert (r.returncode, r.stdout) == (0, "menkyo 0.2.0\n")
