"""Developer tests for the packaging review fixes (R-1 .. R-3, F-3).

--json failures beyond AC-9's list, what counts as a checkout, and the
xlink:href the inked composite needs for Inkscape 1.2 (which may still open
the SVG).  Runs use the shipped example only, and render for real.
"""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

import support
from menkyo import build_diploma as bd
from menkyo import config as config_mod

EX = str(support.EXAMPLE)
XLINK = "{http://www.w3.org/1999/xlink}href"


def _cli(argv, capsys):
    with pytest.raises(SystemExit) as e:
        bd.cli(argv)
    cap = capsys.readouterr()
    return e.value.code, support.events(cap.out), cap.err


def _one_error(code, ev):
    kinds = [e["event"] for e in ev]
    assert code == 1
    assert kinds and kinds[-1] == "error" and kinds.count("error") == 1
    assert "done" not in kinds
    return ev[-1]["message"]


# ---------------------------------------------------------------- --json ----
@pytest.mark.parametrize("flag", ["--js", "--jso", "--json"])
def test_json_abbreviation_still_wraps_failures(flag, tmp_path, capsys):
    code, ev, _ = _cli(["-c", EX, "-a", "nope", f"--out={tmp_path}", flag], capsys)
    assert _one_error(code, ev).startswith("unknown award: nope")


def test_rejected_flag_message(tmp_path, capsys):
    code, ev, err = _cli(["-c", EX, "--dpi", "abc", f"--out={tmp_path}", "--json"], capsys)
    assert _one_error(code, ev) == "argument --dpi: invalid int value: 'abc'"
    assert err == ""


def test_rejected_flag_without_json_is_plain_argparse(tmp_path, capsys):
    code, ev, err = _cli(["-c", EX, "--dpi", "abc", f"--out={tmp_path}"], capsys)
    assert code == 2 and ev == []
    assert err.startswith("usage: menkyo") and "invalid int value" in err


def test_malformed_toml_is_a_message(tmp_path, capsys):
    bad = tmp_path / "bad.toml"
    bad.write_text("schema = 1\n[dojo\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        config_mod.load(str(bad))
    assert isinstance(e.value.code, str) and e.value.code.startswith(f"{bad}: ")
    code, ev, _ = _cli(["-c", str(bad), "--json"], capsys)
    assert _one_error(code, ev).startswith(f"{bad}: ")


def test_unexpected_exception_is_an_error_event(tmp_path, monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("simulated")
    monkeypatch.setattr(bd, "build_one", boom)
    code, ev, _ = _cli(["-c", EX, "-a", "dan", "-v", "overlay-flat", "-d", "",
                        f"--out={tmp_path}", "--json"], capsys)
    assert _one_error(code, ev) == "RuntimeError: simulated"


def test_informational_flags_stay_plain_under_json(capsys):
    with pytest.raises(SystemExit) as e:
        bd.cli(["--version", "--json"])
    assert e.value.code == 0
    assert capsys.readouterr().out.startswith("menkyo ")


# ------------------------------------------------------------- checkout ----
PROBE = ("import json, sys; sys.path.insert(0, sys.argv[1]); "
         "import menkyo; from menkyo import paths; "
         "print(json.dumps([paths.checkout_root(), menkyo.__version__]))")


@pytest.mark.parametrize("pyproject, is_checkout", [
    ('[project]\nname = "menkyo"\nversion = "9.9.9"\n', True),
    ('[project]\nname = "dojo-portal"\nversion = "1.0"\n', False),
    ("[project\n", False),
])
def test_checkout_needs_this_projects_pyproject(pyproject, is_checkout, tmp_path):
    root = tmp_path / "proj"
    support.copy_package(root / "src")
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", "-c", PROBE, str(root / "src")],
                       env=support.isolated_env(tmp_path), cwd=str(tmp_path),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    root_seen, version = json.loads(r.stdout)
    assert root_seen == (str(root) if is_checkout else None)
    if is_checkout:
        assert version == "9.9.9"
    else:
        assert version != "1.0"


# ---------------------------------------------------------------- xlink ----
@pytest.mark.render
def test_inked_svg_places_its_text_with_xlink_href(tmp_path, capsys):
    out = tmp_path / "out"
    bd.cli(["-c", EX, "-a", "dan", "-v", "overlay,overlay-flat", "-f", "svg",
            "-n", "", "-r", "", "-d", "", f"--out={out}"])
    inked = ET.parse(out / "dan-overlay.svg").getroot()
    images = inked.findall("{http://www.w3.org/2000/svg}image")
    assert len(images) == 1
    assert images[0].get(XLINK) == "dan-overlay-textlayer.png"
    assert images[0].get("href") is None
    # only the composite's root declares xlink; the flat sheet is as before
    flat = (out / "dan-overlay-flat.svg").read_text(encoding="utf-8")
    assert "xlink" not in flat


# ------------------------------------------------------- --dpi, glyphs -----
def test_dpi_out_of_range_under_list_json(tmp_path, capsys):
    """--dpi is checked for every run, --list included: one error event."""
    code, ev, err = _cli(["-c", EX, "--list", "--dpi=0", f"--out={tmp_path}", "--json"],
                         capsys)
    assert _one_error(code, ev) == "--dpi 0: use a resolution from 1 to 2400"
    assert len(ev) == 1 and err == ""


@pytest.mark.parametrize("ch, shown", [("\t", "'\\t'"), ("\n", "'\\n'")])
def test_a_control_character_is_named_on_one_line(ch, shown, tmp_path, capsys):
    code, ev, _ = _cli(["-c", EX, "-a", "dan", "-v", "overlay-flat", f"--name=ヤン{ch}ヤンセン",
                        "--rank=", "--date=", f"--out={tmp_path / 'out'}", "--json"], capsys)
    msg = _one_error(code, ev)
    assert "\n" not in msg and "\t" not in msg, msg
    assert f"the character {shown} (U+{ord(ch):04X}) in --name" in msg
    assert not (tmp_path / "out").exists()
