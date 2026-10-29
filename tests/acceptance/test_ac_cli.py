"""AC-5, AC-6, AC-11, AC-17: --version, --example-config, plain output,
`python -m menkyo` and the console script, from the checkout."""

import os
import pty
import subprocess
import sys
from pathlib import Path

import pytest

import support
from menkyo import __version__
from menkyo import config as config_mod

EX = str(support.EXAMPLE)


# ------------------------------------------------------------------ AC-5 ----
def test_ac5_version(home, tmp_path):
    r = support.run_menkyo(["--version"], support.isolated_env(home), tmp_path)
    assert (r.returncode, r.stdout, r.stderr) == (0, f"menkyo {support.project_version()}\n", "")
    assert __version__ == support.project_version()


@pytest.mark.parametrize("config", ["missing.toml", "broken.toml"])
def test_ac5_version_needs_no_working_config(config, home, tmp_path):
    (tmp_path / "broken.toml").write_text("schema = 7\n", encoding="utf-8")
    r = support.run_menkyo(["-c", tmp_path / config, "--version"],
                           support.isolated_env(home), tmp_path)
    assert (r.returncode, r.stdout) == (0, f"menkyo {support.project_version()}\n")


# ------------------------------------------------------------------ AC-6 ----
def test_ac6_example_config_is_the_shipped_file(home, tmp_path):
    r = support.run_menkyo(["--example-config"], support.isolated_env(home), tmp_path)
    assert r.returncode == 0 and r.stderr == ""
    assert r.stdout.encode("utf-8") == support.EXAMPLE.read_bytes()


def test_ac6_example_config_needs_no_working_config(home, tmp_path):
    (tmp_path / "broken.toml").write_text("schema = 7\n", encoding="utf-8")
    for cfg in ("broken.toml", "missing.toml"):
        r = support.run_menkyo(["-c", cfg, "--example-config"],
                               support.isolated_env(home), tmp_path)
        assert r.returncode == 0
        assert r.stdout.encode("utf-8") == support.EXAMPLE.read_bytes()


def test_ac6_example_config_round_trips(home, tmp_path):
    r = support.run_menkyo(["--example-config"], support.isolated_env(home), tmp_path)
    (tmp_path / "dojo.toml").write_text(r.stdout, encoding="utf-8")
    mine, shipped = config_mod.load(str(tmp_path / "dojo.toml")), config_mod.load(EX)
    mine.source = shipped.source = ""
    assert mine == shipped


# ----------------------------------------------------------------- AC-11 ----
def test_ac11_plain_stdout(fake_tools, home, tmp_path):
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", EX, "-a", "dan", "-v", "overlay,proof", "-f", "pdf,png",
                            "-d", "", f"--out={out}"],
                           fake_tools.env(home), tmp_path)
    assert r.returncode == 0
    assert r.stderr == ""                      # not a terminal: no progress
    assert r.stdout == (
        f"wrote {out}/dan-overlay-sample.pdf\n"
        f"wrote {out}/dan-overlay-sample.png\n"
        f"wrote {out}/dan-proof-sample.pdf\n"
        f"wrote {out}/dan-proof-sample.png\n"
        f"\n4 file(s) in {out}/\n")
    assert sorted(os.listdir(out)) == sorted(
        ["dan-overlay-sample.pdf", "dan-overlay-sample.png",
         "dan-proof-sample.pdf", "dan-proof-sample.png"])   # no .work, no .fontconfig


def test_ac11_progress_on_a_terminal(fake_tools, home, tmp_path):
    master, slave = pty.openpty()
    p = subprocess.Popen([sys.executable, "-m", "menkyo", "-c", EX, "-a", "dan",
                          "-v", "overlay", "-d", "", f"--out={tmp_path / 'out'}"],
                         stdout=subprocess.PIPE, stderr=slave,
                         env=fake_tools.env(home), cwd=tmp_path)
    os.close(slave)
    chunks = []
    while True:
        try:
            data = os.read(master, 4096)
        except OSError:
            break
        if not data:
            break
        chunks.append(data)
    stdout, _ = p.communicate(timeout=120)
    os.close(master)
    err = b"".join(chunks).decode("utf-8").replace("\r\n", "\n")
    assert p.returncode == 0
    assert err.splitlines() == ["[1/3] dan overlay: rendering the text",
                                "[2/3] dan overlay: grading the ink",
                                "[3/3] dan overlay: writing the PDF"]
    assert stdout.decode("utf-8").startswith("wrote ")


@pytest.mark.parametrize("flags, message", [
    (["-a", "nope"], "unknown award: nope"),
    (["-r", "0"], "--rank 0: dan grades run from 1 to 10"),
    (["-d", "yesterday"], "--date yesterday: use YYYY-MM-DD, or 'today'"),
])
def test_ac11_plain_errors(flags, message, fake_tools, home, tmp_path):
    r = support.run_menkyo(["-c", EX, *flags, f"--out={tmp_path / 'o'}"],
                           fake_tools.env(home), tmp_path)
    assert r.returncode == 1 and r.stdout == ""
    assert message in r.stderr and "Traceback" not in r.stderr


def test_ac11_plain_missing_inkscape(home, tmp_path):
    if any(os.path.exists(os.path.join(d, "inkscape"))
           for d in __import__("menkyo.paths").paths._EXTRA_BIN):
        pytest.skip("an Inkscape outside PATH would be found")
    r = support.run_menkyo(["-c", EX, "-a", "dan", "-v", "overlay", "-d", "",
                            f"--out={tmp_path / 'o'}"],
                           support.isolated_env(home, path=str(tmp_path)), tmp_path)
    assert r.returncode == 1 and r.stdout == ""
    assert "inkscape was not found. Please install Inkscape" in r.stderr


def test_ac11_clean_empties_the_output_first(fake_tools, home, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.pdf").write_text("old")
    r = support.run_menkyo(["-c", EX, "-a", "dan", "-v", "overlay-flat", "-f", "svg",
                            "-d", "", "--clean", f"--out={out}"], fake_tools.env(home), tmp_path)
    assert r.returncode == 0
    assert os.listdir(out) == ["dan-overlay-flat-sample.svg"]


# ----------------------------------------------------------------- AC-17 ----
def test_ac17_console_script_and_module_agree(fake_tools, home, tmp_path):
    script = Path(sys.executable).parent / "menkyo"
    assert script.exists(), "the menkyo console script is not installed in this env"
    args = ["-c", EX, "--list", "-a", "all", "-v", "overlay,overlay-flat,proof",
            "-f", "pdf,png"]
    a = support.run_menkyo(args, support.isolated_env(home), tmp_path, exe=[str(script)])
    b = support.run_menkyo(args, support.isolated_env(home), tmp_path)
    assert a.returncode == b.returncode == 0
    assert a.stdout == b.stdout and len(a.stdout.splitlines()) == 3 * 3 * 2


def test_ac17_help(home, tmp_path):
    r = support.run_menkyo(["-c", EX, "--help"], support.isolated_env(home), tmp_path)
    assert r.returncode == 0 and r.stdout.startswith("usage: menkyo ")
    for flag in ("--json", "--version", "--example-config", "--no-ink",
                 "--list", "--out", "--suffix", "--honorific", "--supersample"):
        assert flag in r.stdout
