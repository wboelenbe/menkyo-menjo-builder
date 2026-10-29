"""The generator's small pure functions, as the baseline defined them."""

import datetime

import pytest

from menkyo import build_diploma as bd


# ------------------------------------------------------------------ rank ----
@pytest.mark.parametrize("value, kanji", [
    (1, "初段"), ("1", "初段"), ("shodan", "初段"),
    (2, "二段"), ("2", "二段"), ("nidan", "二段"), ("NiDan", "二段"), (" nidan ", "二段"),
    ("3", "三段"), ("sandan", "三段"), ("yondan", "四段"), ("godan", "五段"),
    ("rokudan", "六段"), ("nanadan", "七段"), ("shichidan", "七段"),
    ("hachidan", "八段"), ("kyudan", "九段"), ("kudan", "九段"),
    ("10", "十段"), ("judan", "十段"), ("juudan", "十段"),
])
def test_rank_kanji_dan_grades(value, kanji):
    assert bd.rank_kanji(value) == kanji


@pytest.mark.parametrize("literal", ["師範", "錬士", "弐段", "Shihan", "一段"])
def test_rank_kanji_passes_anything_else_through(literal):
    assert bd.rank_kanji(literal) == literal


def test_rank_kanji_first_dan_is_never_ichidan():
    assert bd.rank_kanji(1) != "一段"


@pytest.mark.parametrize("value", ["0", "11", "99"])
def test_rank_kanji_out_of_range(value):
    with pytest.raises(SystemExit) as e:
        bd.rank_kanji(value)
    assert e.value.code == f"--rank {value}: dan grades run from 1 to 10"


# ------------------------------------------------------------------ date ----
@pytest.mark.parametrize("iso, text", [
    ("2026-09-05", "西暦二〇二六年九月五日"),
    ("2024-12-31", "西暦二〇二四年十二月三十一日"),
    ("2020-10-20", "西暦二〇二〇年十月二十日"),
    ("2021-11-11", "西暦二〇二一年十一月十一日"),
    ("2000-01-10", "西暦二〇〇〇年一月十日"),
    ("1999-02-21", "西暦一九九九年二月二十一日"),
    (" 2026-09-05 ", "西暦二〇二六年九月五日"),
])
def test_date_column(iso, text):
    assert bd.date_column(iso) == list(text)


def test_date_column_today():
    d = datetime.date.today()
    assert bd.date_column("today") == bd.date_column(d.isoformat())
    assert bd.date_column("TODAY") == bd.date_column(d.isoformat())


@pytest.mark.parametrize("bad", ["2026-13-01", "2026-02-30", "05/09/2026", "tomorrow", ""])
def test_date_column_rejects(bad):
    with pytest.raises(SystemExit) as e:
        bd.date_column(bad)
    assert e.value.code == f"--date {bad}: use YYYY-MM-DD, or 'today'"


@pytest.mark.parametrize("n, text", [
    (1, "一"), (9, "九"), (10, "十"), (11, "十一"), (12, "十二"), (20, "二十"),
    (21, "二十一"), (30, "三十"), (31, "三十一"),
])
def test_kanji_count(n, text):
    assert bd._kanji_count(n) == text


def test_blank_date_has_three_day_slots():
    slots = bd.DATE_SLOTS
    assert "".join(c or "_" for c in slots) == "西暦____年__月___日"


# -------------------------------------------------------- fallback/suffix ---
@pytest.mark.parametrize("flag, sample, result", [
    (None, "ジョン・ドウ", "ジョン・ドウ"),   # absent: the config's sample
    (None, "", None),                       # absent, no sample: blank
    ("", "ジョン・ドウ", None),             # '' clears the sample
    ("ヤン", "ジョン・ドウ", "ヤン"),        # given: wins
    ("ヤン", "", "ヤン"),
])
def test_fallback(flag, sample, result):
    assert bd._fallback(flag, sample) == result


@pytest.mark.parametrize("name, suffix", [
    ("ヤン・ヤンセン", "ヤン-ヤンセン"),
    ("ヤン　ヤンセン", "ヤン-ヤンセン"),
    ("ヤン  ヤンセン", "ヤン-ヤンセン"),
    ('a/b\\c:d*e?f"g<h>i|j', "abcdefghij"),
    ("二段", "二段"),
    ("2", "2"),
])
def test_suffix_for(name, suffix):
    assert bd._suffix_for(name) == suffix


# -------------------------------------------------------------------- csv ---
def test_csv_all_and_spacing():
    allowed = ["a", "b", "c"]
    assert bd._csv("all", allowed, "x") == allowed
    assert bd._csv(" ALL ", allowed, "x") == allowed
    assert bd._csv("b, a,,", allowed, "x") == ["b", "a"]


def test_csv_rejects_unknown():
    with pytest.raises(SystemExit) as e:
        bd._csv("a,zz,yy", ["a", "b"], "variant")
    assert e.value.code == "unknown variant: zz, yy\nchoose from: a, b (or 'all')"


# --------------------------------------------------------------- constants --
def test_formats_and_page():
    # The variant set and the default variants are plain-white's contract:
    # tests/acceptance/test_ac_plain_white.py.
    assert bd.DEFAULT_FORMATS == ["pdf"]
    assert (bd.PAGE_W, bd.PAGE_H) == (420.0, 297.0)


def test_right_columns_close_up_without_a_grade():
    name_x, rank_x = bd.right_columns(True)
    assert rank_x is not None and name_x > rank_x
    name_only, none = bd.right_columns(False)
    assert none is None
    assert bd.X_VERB < rank_x < name_x < bd.X_HEADING
    assert bd.X_VERB < name_only < bd.X_HEADING


def test_long_name_shrinks_to_fit():
    name = "アレクサンドル・ファン・デル・フェルデン"
    svg = bd.document("右授与ス", "段位免状", name=name)
    size = min(bd.SZ_AWARDEE, bd.AWARDEE_MAX_H / (len(name) + 1))
    assert size < bd.SZ_AWARDEE
    assert f'font-size="{size:.3f}"' in svg


def test_document_layers():
    """chrome holds no printed columns; text holds no crest; all holds both."""
    chrome = bd.document("右授与ス", "段位免状", layer="chrome")
    text = bd.document("右授与ス", "段位免状", layer="text")
    whole = bd.document("右授与ス", "段位免状")
    assert "段" not in chrome and "<circle" in chrome
    assert "<circle" not in text and ">段<" in text
    assert "<circle" in whole and ">段<" in whole
    # plain white: nothing is drawn behind the sheet
    for svg in (chrome, text, whole):
        assert "clipPath" not in svg and "<rect" not in svg
