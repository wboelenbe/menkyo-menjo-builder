"""AC-7 .. AC-10: the --json event contract (README, "As a package").

Runs use the stand-in inkscape (tests/fakes), so they need no Inkscape.

Rewritten for plain-white (docs/work/plain-white/acceptance.md): the press
conversions, their progress stage, their files and their failure cases are
gone.  What the defaults and `--all` add up to is pinned in
test_ac_plain_white.py.
"""

import json
import os
import sys

import pytest

import support
from menkyo import build_diploma as bd
from menkyo import paths

EX = str(support.EXAMPLE)
STAGES = {"text", "ink", "pdf", "png"}
LABELS = {"text": "rendering the text", "ink": "grading the ink",
          "pdf": "writing the PDF", "png": "writing the PNG"}


def run_json(args, fake_tools, home, tmp_path, **env):
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", EX, *args, f"--out={out}", "--json"],
                           env=fake_tools.env(home, **env), cwd=tmp_path)
    return r, support.events(r.stdout), out


# ------------------------------------------------------------------ AC-7 ----
def test_ac7_success_stream(fake_tools, home, tmp_path):
    r, ev, out = run_json(["-a", "dan", "-v", "overlay,proof", "-f", "pdf,png",
                           "-n", "ヤン・ヤンセン", "-r", "2", "-d", "2026-09-05"],
                          fake_tools, home, tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""                      # stderr is not a terminal here
    kinds = [e["event"] for e in ev]
    assert kinds[-1] == "done" and kinds.count("done") == 1
    assert set(kinds) == {"progress", "file", "done"}

    progress = [e for e in ev if e["event"] == "progress"]
    total = progress[0]["total"]
    assert [p["step"] for p in progress] == list(range(1, total + 1))
    assert all(p["total"] == total for p in progress)
    for p in progress:
        assert set(p) == {"event", "step", "total", "award", "variant", "stage", "label"}
        assert p["stage"] in STAGES and p["award"] == "dan"
        assert p["label"] == f"dan {p['variant']}: {LABELS[p['stage']]}"
    assert [(p["variant"], p["stage"]) for p in progress] == [
        ("overlay", "text"), ("overlay", "ink"), ("overlay", "pdf"),
        ("overlay", "png"), ("proof", "pdf"), ("proof", "png")]

    files = [e["path"] for e in ev if e["event"] == "file"]
    assert all(set(e) == {"event", "path"} for e in ev if e["event"] == "file")
    tag = "2-ヤン-ヤンセン"
    assert files == [str(out / f"dan-overlay-{tag}.pdf"),
                     str(out / f"dan-overlay-{tag}.png"), str(out / f"dan-proof-{tag}.pdf"),
                     str(out / f"dan-proof-{tag}.png")]
    assert all(os.path.isfile(f) for f in files)
    assert ev[-1] == {"event": "done", "out": str(out), "files": files}


def test_ac7_a_file_event_follows_its_progress(fake_tools, home, tmp_path):
    """Files for a variant are reported before the next variant's progress."""
    r, ev, _ = run_json(["-a", "dan,shihan", "-v", "overlay-flat", "-d", ""],
                        fake_tools, home, tmp_path)
    assert r.returncode == 0
    assert [e["event"] for e in ev] == ["progress", "file", "progress", "file", "done"]


def test_ac7_progress_callback_in_process(fake_tools, tmp_path):
    seen = []
    bd.main(["-c", EX, "-a", "dan", "-v", "overlay", "-d", "", f"--out={tmp_path}"],
            progress=seen.append)
    assert [(s["step"], s["total"], s["stage"]) for s in seen] == \
        [(1, 3, "text"), (2, 3, "ink"), (3, 3, "pdf")]


# ------------------------------------------------------------------ AC-8 ----
TOTALS = [
    # (flags, expected total, expected number of files)
    (["-a", "dan", "-v", "overlay", "-f", "pdf"], 3, 1),
    (["-a", "dan", "-v", "overlay-flat", "-f", "pdf"], 1, 1),
    (["-a", "dan", "-v", "overlay", "--no-ink", "-f", "pdf,png"], 2, 2),
    (["-a", "dan", "-v", "overlay,overlay-flat"], 4, 2),
    (["-a", "dan", "-v", "proof", "-f", "pdf,png"], 2, 2),
    (["-a", "dan,shihan", "-v", "overlay,proof", "-f", "pdf,png,svg"], 12, 2 * (4 + 3)),
    (["-a", "dan", "-v", "overlay-flat", "-f", "svg"], 0, 1),
    (["-a", "dan", "-v", "overlay", "-f", "svg"], 2, 2),
    (["-a", "all", "-v", "overlay,overlay-flat,proof", "-f", "pdf,png"], 24, 18),
    (["-a", "all", "-v", "overlay,overlay-flat,proof", "--no-ink"], 9, 9),
    # the defaults, --all and -v all: test_ac_plain_white.py
]


@pytest.mark.parametrize("flags, total, nfiles", TOTALS,
                         ids=[" ".join(t[0]) or "defaults" for t in TOTALS])
def test_ac8_step_totals(flags, total, nfiles, fake_tools, home, tmp_path):
    r, ev, _ = run_json([*flags, "-d", "2026-09-05"], fake_tools, home, tmp_path)
    assert r.returncode == 0, r.stderr
    progress = [e for e in ev if e["event"] == "progress"]
    assert len(progress) == total
    assert [p["step"] for p in progress] == list(range(1, total + 1))
    assert all(p["total"] == total for p in progress)
    files = [e["path"] for e in ev if e["event"] == "file"]
    assert len(files) == nfiles and ev[-1]["files"] == files


# ------------------------------------------------------------------ AC-9 ----
def _cli_error(argv, capsys):
    """Run cli() in-process; return (exit code, events, stderr)."""
    with pytest.raises(SystemExit) as e:
        bd.cli(argv)
    cap = capsys.readouterr()
    return e.value.code, support.events(cap.out), cap.err


def _assert_one_error(code, ev, contains, detail=None):
    assert code == 1
    assert ev, "no events at all"
    assert ev[-1]["event"] == "error", ev
    assert [e["event"] for e in ev].count("error") == 1
    assert contains in ev[-1]["message"], ev[-1]
    assert "done" not in [e["event"] for e in ev]
    if detail is not None:
        assert detail in ev[-1].get("detail", ""), ev[-1]


@pytest.mark.parametrize("flags, contains", [
    (["-a", "nope"], "unknown award: nope"),
    (["-v", "nope"], "unknown variant: nope"),
    (["-f", "jpg"], "unknown format: jpg"),
    (["-r", "11"], "--rank 11: dan grades run from 1 to 10"),
    (["-d", "2026-13-01"], "--date 2026-13-01: use YYYY-MM-DD"),
    (["--supersample", "5"], "--supersample must be between 1 and 4"),
])
def test_ac9_user_errors(flags, contains, fake_tools, tmp_path, capsys):
    code, ev, _ = _cli_error(["-c", EX, *flags, f"--out={tmp_path}", "--json"], capsys)
    _assert_one_error(code, ev, contains)


def test_ac9_missing_config(fake_tools, tmp_path, capsys):
    code, ev, _ = _cli_error(["-c", str(tmp_path / "none.toml"), "--json"], capsys)
    _assert_one_error(code, ev, "no configuration at")


def test_ac9_invalid_config(fake_tools, tmp_path, capsys):
    bad = tmp_path / "bad.toml"
    bad.write_text("schema = 9\n", encoding="utf-8")
    code, ev, _ = _cli_error(["-c", str(bad), "--json"], capsys)
    _assert_one_error(code, ev, "schema = 9")


def test_ac9_inkscape_missing(no_tools, tmp_path, capsys):
    code, ev, _ = _cli_error(["-c", EX, "-a", "dan", "-v", "overlay", "-d", "",
                              f"--out={tmp_path}", "--json"], capsys)
    _assert_one_error(code, ev, "inkscape was not found. Please install Inkscape")


@pytest.mark.parametrize("stage", ["query", "png", "pdf"])
def test_ac9_inkscape_fails(stage, fake_tools, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_INKSCAPE_FAIL", stage)
    code, ev, _ = _cli_error(["-c", EX, "-a", "dan", "-v", "overlay", "-f", "pdf", "-d", "",
                              f"--out={tmp_path}", "--json"], capsys)
    _assert_one_error(code, ev, "inkscape failed.", detail="fake inkscape: simulated")
    assert ev[-1]["message"] == "inkscape failed."


def test_ac9_error_exit_code_from_the_real_command(fake_tools, home, tmp_path):
    """The same, through the installed console entry point, as a process."""
    r, ev, _ = run_json(["-a", "nope"], fake_tools, home, tmp_path)
    assert r.returncode == 1
    assert ev == [{"event": "error", "message": ev[0]["message"]}]
    assert ev[0]["message"].startswith("unknown award: nope")
    assert "Traceback" not in r.stderr

    r, ev, _ = run_json(["-a", "dan", "-v", "overlay", "-d", ""], fake_tools, home, tmp_path,
                        FAKE_INKSCAPE_FAIL="pdf")
    assert r.returncode == 1
    assert [e["event"] for e in ev][-1] == "error"
    assert ev[-1]["message"] == "inkscape failed."
    assert "simulated pdf export failure" in ev[-1]["detail"]
    assert "Traceback" not in r.stderr


@pytest.mark.parametrize("flags", [["--dpi", "abc"], ["--no-such-flag"]],
                         ids=["bad-flag-value", "unknown-flag"])
def test_ac9_bad_flags_are_error_events(flags, fake_tools, tmp_path, capsys):
    """A caller that only reads stdout must learn about a rejected flag too."""
    code, ev, _ = _cli_error(["-c", EX, *flags, f"--out={tmp_path}", "--json"], capsys)
    _assert_one_error(code, ev, "")


def test_ac9_unwritable_out_is_an_error_event(fake_tools, tmp_path, capsys):
    blocker = tmp_path / "a-file"
    blocker.write_text("x")
    code, ev, _ = _cli_error(["-c", EX, "-a", "dan", "-v", "overlay-flat", "-d", "",
                              f"--out={blocker / 'sub'}", "--json"], capsys)
    _assert_one_error(code, ev, "")


@pytest.mark.parametrize("flag", ["--js", "--jso"])
def test_ac9_abbreviated_json_is_json(flag, fake_tools, tmp_path, capsys):
    """Agreement 2: --json is decided the way argparse parses it."""
    code, ev, err = _cli_error(["-c", EX, "-a", "nope", f"--out={tmp_path}", flag], capsys)
    _assert_one_error(code, ev, "unknown award: nope")
    assert err == ""


@pytest.mark.parametrize("argv", [["-c", EX, "--json=1"], ["--json", "-c"], ["-c", EX, "--json", "--out"]],
                         ids=["json-with-value", "config-without-value", "out-without-value"])
def test_ac9_odd_argv_is_an_error_event(argv, fake_tools, tmp_path, capsys):
    code, ev, err = _cli_error(argv, capsys)
    _assert_one_error(code, ev, "argument ")
    assert err == ""


@pytest.mark.parametrize("kind", ["malformed", "not-utf8", "directory"])
def test_ac9_unreadable_config_is_an_error_event(kind, fake_tools, tmp_path, capsys):
    """Agreement 1: any failure, including a config that cannot be read."""
    bad = tmp_path / "bad.toml"
    if kind == "malformed":
        bad.write_text("schema = 1\n[dojo\n", encoding="utf-8")
    elif kind == "not-utf8":
        bad.write_bytes(b"schema = 1\n# \xff\xfe\n")
    else:
        bad.mkdir()
    code, ev, err = _cli_error(["-c", str(bad), "--json"], capsys)
    _assert_one_error(code, ev, str(bad))
    assert err == ""


def test_ac9_informational_flags_stay_plain(fake_tools, home, tmp_path):
    """Agreement 3: --help, --version and --example-config ignore --json."""
    env = support.isolated_env(home)
    for flags, start in ((["--help"], "usage: menkyo"), (["--version"], "menkyo "),
                         (["--example-config"], "#")):
        r = support.run_menkyo(["-c", EX, *flags, "--json"], env, tmp_path)
        assert r.returncode == 0 and r.stdout.startswith(start), (flags, r.stdout[:80])


# ----------------------------------------------------------------- AC-10 ----
@pytest.mark.parametrize("flags", [[], ["--all", "-f", "pdf,png,svg"],
                                   ["-n", "ヤン・ヤンセン", "-r", "2"], ["--suffix", ""]])
def test_ac10_list_json_matches_plain_list(flags, home, tmp_path):
    env = support.isolated_env(home)
    out = tmp_path / "out"
    plain = support.run_menkyo(["-c", EX, "--list", *flags, f"--out={out}"], env, tmp_path)
    js = support.run_menkyo(["-c", EX, "--list", *flags, f"--out={out}", "--json"], env, tmp_path)
    assert plain.returncode == js.returncode == 0
    ev = support.events(js.stdout)
    assert all(set(e) == {"event", "file"} and e["event"] == "planned" for e in ev)
    assert [e["file"] for e in ev] == plain.stdout.splitlines()
    assert js.stderr == "" and not out.exists()
    assert "done" not in [e["event"] for e in ev]      # Agreement 4
