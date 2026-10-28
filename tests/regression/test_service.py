"""menkyo.service: what the desktop window and the web page share."""

import pytest

import support
from menkyo import config as config_mod
from menkyo.service import GRADES, MAX_NAME, OUTPUTS, FormError, make_argv, run_build


@pytest.fixture
def cfg():
    return config_mod.load(str(support.EXAMPLE))


def argv(cfg, **kw):
    base = dict(award="dan", output="overlay", folder="/out")
    base.update(kw)
    return make_argv(cfg, **base)


def test_every_slot_passed_explicitly(cfg):
    assert argv(cfg) == [
        f"--config={cfg.source}", "--awards=dan", "--variants=overlay",
        "--formats=pdf", "--name=", "--rank=", "--date=", "--out=/out"]


def test_filled_form(cfg):
    got = argv(cfg, name="  ヤン・ヤンセン ", grade="二段", date="2026-09-05",
               output="overlay,full-cream", folder="/tmp/x y", press=True)
    assert got == [
        f"--config={cfg.source}", "--awards=dan", "--variants=overlay,full-cream",
        "--formats=pdf", "--name=ヤン・ヤンセン", "--rank=二段", "--date=2026-09-05",
        "--out=/tmp/x y", "--press"]


def test_values_starting_with_a_dash_stay_values(cfg):
    got = argv(cfg, name="-n")
    assert "--name=-n" in got
    assert all(a.startswith("--") and "=" in a for a in got)


def test_grade_dropped_on_a_licence(cfg):
    assert "--rank=" in argv(cfg, award="shihan", grade="二段")


@pytest.mark.parametrize("kw, message", [
    (dict(award="nope"), "Unknown certificate type."),
    (dict(name="ア" * (MAX_NAME + 1)), f"at most {MAX_NAME} characters"),
    (dict(grade="11段"), "Unknown grade."),
    (dict(grade="2"), "Unknown grade."),
    (dict(date="2026-02-30"), "That date does not exist."),
    (dict(date="today"), "That date does not exist."),
    (dict(output="proof"), "Unknown output kind."),
    (dict(folder=""), "Please choose a folder"),
])
def test_form_errors(cfg, kw, message):
    with pytest.raises(FormError) as e:
        argv(cfg, **kw)
    assert message in str(e.value)


def test_name_of_max_length_is_fine(cfg):
    assert f"--name={'ア' * MAX_NAME}" in argv(cfg, name="ア" * MAX_NAME)


def test_form_constants():
    assert GRADES[0] == "" and GRADES[1] == "初段" and GRADES[-1] == "十段"
    assert len(GRADES) == 11
    assert set(OUTPUTS.values()) == {"overlay", "full-cream", "overlay,full-cream"}


# ---------------------------------------------------------------- run_build --
def test_run_build_returns_the_files(cfg, fake_tools, tmp_path):
    out = tmp_path / "out"
    ok, files, msg = run_build(argv(cfg, output="overlay,full-cream", folder=str(out),
                                    name="ヤン・ヤンセン", grade="二段", date="2026-09-05"))
    assert (ok, msg) == (True, "")
    assert files == [str(out / "dan-overlay-二段-ヤン・ヤンセン.pdf".replace("・", "-")),
                     str(out / "dan-full-cream-二段-ヤン・ヤンセン.pdf".replace("・", "-"))]
    assert all((out / f).exists() for f in files)


def test_run_build_blank_form_ignores_the_sample(cfg, fake_tools, tmp_path):
    """The example's [sample] must not reach a form-made certificate."""
    out = tmp_path / "out"
    ok, files, _ = run_build(argv(cfg, folder=str(out)))
    assert ok and files == [str(out / "dan-overlay.pdf")]
    layer = (fake_tools.capture / "dan-overlay-textlayer.svg").read_text(encoding="utf-8")
    assert "ジ" not in layer and ">五<" not in layer      # no sample name, no 五段
    # the date column (x = 205) keeps its blank grid: only 西暦 年 月 日
    import re
    date_chars = re.findall(r'<text x="205\.000"[^>]*>(.)</text>', layer)
    assert "".join(date_chars) == "西暦年月日"


def test_run_build_reports_user_errors(cfg, fake_tools, tmp_path):
    ok, files, msg = run_build([f"--config={cfg.source}", "--awards=nope",
                                f"--out={tmp_path}"])
    assert (ok, files) == (False, [])
    assert msg.startswith("unknown award: nope")


def test_run_build_reports_a_failing_tool(cfg, fake_tools, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_INKSCAPE_FAIL", "pdf")
    ok, files, msg = run_build(argv(cfg, folder=str(tmp_path / "out")))
    assert (ok, files) == (False, [])
    assert "inkscape failed." in msg and "simulated pdf export failure" in msg


def test_run_build_reports_a_missing_tool(cfg, no_tools, tmp_path):
    ok, files, msg = run_build(argv(cfg, folder=str(tmp_path / "out")))
    assert (ok, files) == (False, [])
    assert msg.startswith("inkscape was not found.")
