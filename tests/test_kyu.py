"""Kyū grades: rank_kanji() in either unit, an award's grade_column, crest,
body and watermark keys, and what horizontal_document() draws.  No renders;
the acceptance tests draw the pages."""

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
    assert (a.grade_column, a.unit, a.crest) == (column, unit, True)
    assert a.horizontal == (unit == "kyu")


@pytest.mark.parametrize("line", ['grade_column = "belt"', "grade_column = 1",
                                  'grade_column = "yes"', 'grade_column = ""'])
def test_grade_column_refused(line, tmp_path):
    path = _config(tmp_path, line)
    with pytest.raises(SystemExit) as e:
        config_mod.load(path)
    assert e.value.code.startswith(f"{path}: [[awards]] 'k': grade_column = ")
    assert '"dan" or "kyu"' in e.value.code


def test_crest_is_a_boolean(tmp_path):
    with pytest.raises(SystemExit) as e:
        config_mod.load(_config(tmp_path, 'crest = "no"'))
    assert "[[awards]] 'k': crest = \"no\" should be true or false" in e.value.code


@pytest.mark.parametrize("line", ["motto = false", "motto = true", "motto = 0"])
def test_motto_is_removed(line, tmp_path):
    path = _config(tmp_path, line)
    with pytest.raises(SystemExit) as e:
        config_mod.load(path)
    assert e.value.code.startswith(f"{path}: [[awards]] 'k': {line}: the key was removed")


def test_body_and_watermark_defaults(tmp_path):
    kyu = config_mod.load(_config(tmp_path, 'grade_column = "kyu"')).award("k")
    assert kyu.body == config_mod.DEFAULT_BODY
    assert kyu.watermark == config_mod.DEFAULT_WATERMARK == 0.08
    # on a vertical award they are checked, then not kept
    dan = config_mod.load(_config(tmp_path, 'body = ["一"]\nwatermark = 0.5')).award("k")
    assert (dan.body, dan.watermark) == ((), config_mod.DEFAULT_WATERMARK)


@pytest.mark.parametrize("line, body", [
    ('body = ["一"]', ("一",)), ('body = ["一", "二", "三"]', ("一", "二", "三")),
    ('body = [" 一 "]', (" 一 ",)),
])
def test_body_kept_as_given(line, body, tmp_path):
    a = config_mod.load(_config(tmp_path, f'grade_column = "kyu"\n{line}')).award("k")
    assert a.body == body


@pytest.mark.parametrize("value, kept", [("1", 1.0), ("0.2", 0.2), ("1e-3", 0.001)])
def test_watermark_kept(value, kept, tmp_path):
    a = config_mod.load(_config(tmp_path, f'grade_column = "kyu"\nwatermark = {value}'))
    assert a.award("k").watermark == kept


@pytest.mark.parametrize("value", ["nan", "inf", "false", "[0.08]"])
def test_watermark_refused(value, tmp_path):
    path = _config(tmp_path, f"watermark = {value}")
    with pytest.raises(SystemExit) as e:
        config_mod.load(path)
    assert e.value.code.startswith(f"{path}: [[awards]] 'k': watermark = ")


def test_formula_optional_on_kyu_only(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('schema = 1\n[[awards]]\nslug = "k"\nheading = "級位認定証"\n'
                 'grade_column = "kyu"\n', encoding="utf-8")
    assert config_mod.load(str(p)).award("k").formula == ""
    p.write_text('schema = 1\n[[awards]]\nslug = "k"\nheading = "級位認定証"\n',
                 encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        config_mod.load(str(p))
    assert e.value.code == f"{p}: [[awards]] #1 is missing 'formula'"


def test_save_round_trip(tmp_path):
    path = _config(tmp_path, 'grade_column = "kyu"\ncrest = false')
    c = config_mod.load(path)
    saved = config_mod.save(c, str(tmp_path / "saved" / "dojo.toml"))
    text = open(saved, encoding="utf-8").read()
    assert text.endswith('grade_column = "kyu"\ncrest = false\n'
                         'body = ["上記の者は本会所定の審査に合格したので", "ここに認定します"]\n'
                         'watermark = 0.08\n')
    assert config_mod.load(saved).awards == c.awards


def test_save_leaves_out_an_empty_formula(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('schema = 1\n[[awards]]\nslug = "k"\nheading = "級位認定証"\n'
                 'grade_column = "kyu"\nbody = ["一"]\nwatermark = 1\n', encoding="utf-8")
    c = config_mod.load(str(p))
    saved = config_mod.save(c, str(tmp_path / "saved" / "dojo.toml"))
    text = open(saved, encoding="utf-8").read()
    assert "formula" not in text and 'body = ["一"]\nwatermark = 1.0\n' in text
    assert config_mod.load(saved).awards == c.awards


# -------------------------------------------------------------- document ----
def _xs(svg):
    """The x of every body column (the crest's lettering is not one)."""
    return sorted({float(x) for x in re.findall(
        rf'<text x="([\d.]+)" y="[\d.]+" font-family="{bd.FONT_BODY}"', svg)})


def test_the_precept_column_stays_where_it_was(example_cfg):
    """No award moves its columns any more: the precept is drawn whenever
    [motto] text has one, at X_MOTTO."""
    kw = dict(name="ヤン", rank="二段", date=bd.date_column("2026-09-05"))
    xs = _xs(bd.document("右授与ス", "段位免状", **kw))
    assert bd.X_MOTTO in xs and bd.X_SIGNER in xs and bd.X_HEADING in xs
    assert not hasattr(bd, "NO_MOTTO_SHIFT")


def _ink(svg):
    """(x, y, size, anchor, text) of every <text> in ink."""
    return [(float(x), float(y), float(sz), a, t) for x, y, sz, a, t in re.findall(
        r'<text x="([\d.]+)" y="([\d.]+)" font-family="[^"]+" font-weight="\d+" '
        r'font-size="([\d.]+)" fill="#111111" text-anchor="(\w+)">([^<]*)</text>', svg)]


def test_horizontal_document_draws_in_mincho(example_cfg):
    svg = bd.horizontal_document("級位認定証", config_mod.DEFAULT_BODY, name="ヤン",
                                 rank="五級", date=bd.date_column("2026-09-05"))
    assert bd.FONT_BODY not in svg and "transform=\"rotate" not in svg
    assert 'width="210.0mm" height="297.0mm" viewBox="0 0 210.0 297.0"' in svg
    assert "scale(" not in svg
    texts = [t[4] for t in _ink(svg)]
    assert texts[:5] == list("級位認定証") and "ヤン" in texts and "殿" in texts
    assert list(config_mod.DEFAULT_BODY) == [t for t in texts if t.startswith(("上", "こ"))]
    assert bd.CFG.motto not in "".join(texts)


def test_horizontal_document_a3_is_scaled(example_cfg):
    a4 = bd.horizontal_document("級位認定証", ("一",))
    a3 = bd.horizontal_document("級位認定証", ("一",), sheet="a3")
    assert a3.startswith('<svg xmlns="http://www.w3.org/2000/svg" width="297.0mm" '
                         'height="420.0mm" viewBox="0 0 297.0 420.0">\n'
                         '<g transform="scale(1.4142135624)">')
    assert a3.split("\n", 2)[2][:-len("</g>\n</svg>")] == a4.split("\n", 1)[1][:-len("</svg>")]


@pytest.mark.parametrize("fraction, grey", [(0.08, "#ebebeb"), (0.2, "#cccccc"),
                                            (1, "#000000"), (0.5, "#808080")])
def test_watermark_grey(fraction, grey):
    assert bd.watermark_grey(fraction) == grey


def test_no_watermark_draws_no_crest(example_cfg):
    svg = bd.horizontal_document("級位認定証", ("一",), watermark=None)
    assert "<circle" not in svg and "evenodd" not in svg


@pytest.mark.parametrize("n, ys", [(1, [186.5]), (2, [180.0, 193.0]),
                                   (3, [173.5, 186.5, 199.5])])
def test_body_block_centred_on_its_line(n, ys, example_cfg):
    body = tuple("一二三"[:n])
    got = [t for t in _ink(bd.horizontal_document("級位認定証", body)) if t[4] in body]
    assert [round(y - bd.BASELINE_DROP * sz, 3) for _, y, sz, _, _ in got] == ys
    assert len({x for x, *_ in got}) == 1


def test_spaced_tightens_before_it_shrinks():
    """Five glyphs fit at the mock's spacing; nine close up to solid but keep
    their size; twelve are set solid and smaller."""
    def span(s, width=156.0):
        els = bd._spaced(s, 0.0, 16.0, 24.0, width)
        xs = [float(re.search(r'x="([\d.]+)"', e)[1]) for e in els]
        size = float(re.search(r'font-size="([\d.]+)"', els[0])[1])
        return size, xs[1] - xs[0] if len(xs) > 1 else None
    assert span("一二三四五") == (16.0, 24.0)
    size, pitch = span("一" * 9)
    assert size == 16.0 and 16.0 <= pitch < 24.0
    size, pitch = span("一" * 12)
    assert size == pytest.approx(13.0) and pitch == pytest.approx(13.0)


def test_issuer_block_moves_left_then_shrinks(example_cfg, monkeypatch):
    def issuer(signer):
        monkeypatch.setattr(bd.CFG, "signer_name", signer)
        els = [t for t in _ink(bd.horizontal_document("級位認定証", ("一",)))
               if t[4] == bd.CFG.art]
        return els[0][0], els[0][2]
    assert issuer("山田太郎") == (bd.H_X_ISSUER, bd.H_SZ_ISSUER)
    x, size = issuer("ジョン・スミス")                # moved left, not shrunk
    x2, size2 = issuer("ジョン・スミス・ドウ・ジュニア")   # past the centre: shrunk
    assert x < bd.H_X_ISSUER and size == bd.H_SZ_ISSUER
    assert size2 < bd.H_SZ_ISSUER and x2 < x


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
    ("watermark = 10:00:00", "10:00:00"),
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
