"""Kyū grades: rank_kanji() in either unit, an award's grade_column, crest
and motto keys, and what document() draws without crest or precept.  No
renders; the acceptance tests draw the pages."""

import re

import pytest

import support
from menkyo import build_diploma as bd
from menkyo import config as config_mod

EX = str(support.EXAMPLE)


@pytest.fixture
def example_cfg(monkeypatch):
    monkeypatch.setattr(bd, "CFG", config_mod.load(EX))


# ------------------------------------------------------------------ rank ----
@pytest.mark.parametrize("value, kanji", [
    ("1", "一級"), ("10", "十級"), (5, "五級"), (" 5 ", "五級"),
    ("gokyu", "五級"), ("GoKyū", "五級"), ("gokyuu", "五級"), ("hakkyu", "八級"),
    ("yellow", "五級"), ("BROWN", "一級"), ("white", "六級"),
    ("white-yellow", "準五級"), ("orange-green", "準三級"),
    ("jun5", "準五級"), ("JUN-4", "準四級"),
    ("三級", "三級"), ("準五級", "準五級"), (" 弐級 ", "弐級"),
])
def test_kyu_forms(value, kanji):
    assert bd.rank_kanji(value, "kyu") == kanji


@pytest.mark.parametrize("value", ["0", "11", "-1", "purple", "white-orange", "jun6",
                                   "jun2", "jun", "kyu", "5kyu", "nidan", "Shihan"])
def test_kyu_refuses_the_rest(value):
    with pytest.raises(SystemExit) as e:
        bd.rank_kanji(value, "kyu", "--rank", "kyu")
    msg = e.value.code
    assert msg.startswith(f"--rank {value}: ") and "[[awards]] 'kyu'" in msg
    assert all(form in msg for form in (*bd.BELTS, *bd.JUN_STEPS, "jun5", "10"))


@pytest.mark.parametrize("value, kanji", [
    ("jūdan", "十段"), ("JUUDAN", "十段"), ("kyūdan", "九段"), ("kyudan", "九段"),
    ("Shihan", "Shihan"), ("-1", "-1"),
])
def test_dan_folds_and_still_passes_through(value, kanji):
    assert bd.rank_kanji(value) == kanji


@pytest.mark.parametrize("value", ["yellow", "white-yellow", "jun5", "jun6", "gokyu",
                                   "5kyu"])
def test_dan_refuses_kyu_forms(value):
    with pytest.raises(SystemExit) as e:
        bd.rank_kanji(value, "dan", "[sample] rank", "dan")
    assert e.value.code.startswith(f"[sample] rank {value}: ")
    assert "[[awards]] 'dan'" in e.value.code


# ---------------------------------------------------------------- config ----
def _config(tmp_path, award):
    p = tmp_path / "c.toml"
    p.write_text('schema = 1\n[[awards]]\nslug = "k"\nheading = "級位認定証"\n'
                 f'formula = "右認定ス"\n{award}\n', encoding="utf-8")
    return str(p)


@pytest.mark.parametrize("line, column, unit", [
    ("", False, "dan"), ("grade_column = false", False, "dan"),
    ("grade_column = true", True, "dan"), ('grade_column = "dan"', True, "dan"),
    ('grade_column = "KYU"', True, "kyu"),
])
def test_grade_column(line, column, unit, tmp_path):
    a = config_mod.load(_config(tmp_path, line)).award("k")
    assert (a.grade_column, a.unit, a.crest, a.motto) == (column, unit, True, True)


@pytest.mark.parametrize("line", ['grade_column = "belt"', "grade_column = 1",
                                  'grade_column = "yes"', 'grade_column = ""'])
def test_grade_column_refused(line, tmp_path):
    path = _config(tmp_path, line)
    with pytest.raises(SystemExit) as e:
        config_mod.load(path)
    assert e.value.code.startswith(f"{path}: [[awards]] 'k': grade_column = ")
    assert '"dan" or "kyu"' in e.value.code


@pytest.mark.parametrize("line", ['crest = "no"', "motto = 0"])
def test_sheet_keys_are_booleans(line, tmp_path):
    with pytest.raises(SystemExit) as e:
        config_mod.load(_config(tmp_path, line))
    assert f"[[awards]] 'k': {line} should be true or false" in e.value.code


def test_save_round_trip(tmp_path):
    path = _config(tmp_path, 'grade_column = "kyu"\ncrest = false')
    c = config_mod.load(path)
    saved = config_mod.save(c, str(tmp_path / "saved" / "dojo.toml"))
    text = open(saved, encoding="utf-8").read()
    assert text.endswith('grade_column = "kyu"\ncrest = false\n')
    assert config_mod.load(saved).awards == c.awards


# -------------------------------------------------------------- document ----
def _xs(svg):
    """The x of every body column (the crest's lettering is not one)."""
    return sorted({float(x) for x in re.findall(
        rf'<text x="([\d.]+)" y="[\d.]+" font-family="{bd.FONT_BODY}"', svg)})


def test_no_motto_moves_every_column_left(example_cfg):
    kw = dict(name="ヤン", rank="五級", date=bd.date_column("2026-09-05"))
    full = bd.document("右認定ス", "級位認定証", **kw)
    plain = bd.document("右認定ス", "級位認定証", crest_kind=None, motto_column=False,
                        **kw)
    body = [x for x in _xs(full) if abs(x - bd.X_MOTTO) > 1]
    assert _xs(plain) == [round(x - bd.NO_MOTTO_SHIFT, 3) for x in body]
    assert "<circle" not in plain and "evenodd" not in plain


def test_motto_column_true_is_the_old_document(example_cfg):
    for kw in (dict(), dict(name="ヤン", rank="二段", guides=True)):
        assert bd.document("右授与ス", "段位免状", motto_column=True, **kw) == \
            bd.document("右授与ス", "段位免状", **kw)


def test_proof_guides_move_but_the_page_does_not(example_cfg):
    svg = bd.document("右認定ス", "級位認定証", guides=True, crest_kind=None,
                      motto_column=False)
    assert f'cx="{bd.SEAL_C[0] - bd.NO_MOTTO_SHIFT}"' in svg
    assert f'<rect x="{config_mod.Config.stock_border}"' in svg


@pytest.mark.parametrize("rank, size", [("五級", 30.0), ("準五級", 20.0), ("Shihan", 10.0)])
def test_a_long_grade_shrinks_from_the_same_top(rank, size, example_cfg):
    svg = bd.document("右認定ス", "級位認定証", rank=rank)
    got = [(float(y), float(s)) for y, s in re.findall(
        rf'<text x="{bd.X_RANK:.3f}" y="([\d.]+)" [^>]*font-size="([\d.]+)"', svg)]
    assert [s for _, s in got] == [size] * len(rank)
    top = got[0][0] - bd.BASELINE_DROP * size - size / 2
    y_rank = bd.Y_RANK + bd.CFG.text_drop * bd.PAGE_H
    assert top == pytest.approx(y_rank - bd.SZ_RANK / 2, abs=0.002)


# ------------------------------------------------------ review round 1 ----
NFD_U = "ū"           # ū as u + combining macron


@pytest.mark.parametrize("value, unit, kanji", [
    (f"goky{NFD_U}", "kyu", "五級"), (f"GOKY{NFD_U.upper()}", "kyu", "五級"),
    (f"j{NFD_U}dan", "dan", "十段"), (f"ky{NFD_U}dan", "dan", "九段"),
])
def test_combining_macron_folds_too(value, unit, kanji):
    assert bd.rank_kanji(value, unit) == kanji


@pytest.mark.parametrize("value, kanji", [("５", "五級"), ("１０", "十級"), (" ３ ", "三級")])
def test_full_width_digits_on_kyu(value, kanji):
    assert bd.rank_kanji(value, "kyu") == kanji


@pytest.mark.parametrize("value", ["０", "１１"])
def test_full_width_digits_out_of_range_on_kyu(value):
    with pytest.raises(SystemExit) as e:
        bd.rank_kanji(value, "kyu")
    assert e.value.code.startswith(f"--rank {value}: not a kyū grade")


def test_full_width_digits_on_dan_as_before():
    assert bd.rank_kanji("５") == "五段"


@pytest.mark.parametrize("line, shown", [
    ("grade_column = 2026-09-05", "2026-09-05"),
    ("crest = 2026-09-05T10:00:00", "2026-09-05 10:00:00"),
    ("motto = 10:00:00", "10:00:00"),
])
def test_a_toml_date_is_a_message_not_a_traceback(line, shown, tmp_path):
    path = _config(tmp_path, line)
    key = line.split(" =")[0]
    with pytest.raises(SystemExit) as e:
        config_mod.load(path)
    assert e.value.code.startswith(f"{path}: [[awards]] 'k': {key} = \"{shown}\"")


def test_a_toml_date_as_paper_size(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('schema = 1\n[paper]\nsize = 2026-09-05\n[[awards]]\nslug = "k"\n'
                 'heading = "級位認定証"\nformula = "右認定ス"\n', encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        config_mod.load(str(p))
    assert e.value.code.startswith(f"{p}: [paper] size = \"2026-09-05\" is not")


@pytest.mark.parametrize("name", [None, "ヤン"])
def test_a_rank_without_a_grade_column_is_still_drawn(name, example_cfg):
    """document() called directly, as build_one() never does: a grade with
    rank_column=False gets its column, as 0.4.0 drew it without a name."""
    svg = bd.document("右免許ス", "師範免許状", rank="五段", rank_column=False, name=name)
    assert svg == bd.document("右免許ス", "師範免許状", rank="五段", name=name)
    assert svg.count(">五<") == 1 and svg.count(">段<") == 1
