"""menkyo.config: loading, validation, the search order, save -> load."""

import pytest

import support
from menkyo import config as config_mod
from menkyo.config import Award, Config


def write(tmp_path, text, name="dojo.toml"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


AWARD = '[[awards]]\nslug = "dan"\nheading = "段位免状"\nformula = "右授与ス"\n'


def test_defaults_name_nobody():
    c = Config()
    assert (c.art, c.dojo, c.crest_ring, c.signer_title, c.signer_name) == \
        ("〇〇流柔術", "〇〇道場", "", "師範", "")
    assert (c.honorific, c.motto, c.stock_border, c.safe_inset, c.text_drop) == \
        ("殿", "", 22.0, 38.0, 0.0)
    assert c.awards == [] and c.crest_traced is False
    assert (c.sample_name, c.sample_rank, c.sample_date, c.sample_suffix) == ("", "", "", "")


def test_example_loads():
    c = config_mod.load(str(support.EXAMPLE))
    assert c.slugs == ["dan", "shihan", "renshi"]
    assert (c.art, c.dojo, c.crest_ring, c.signer_name, c.motto) == \
        ("〇〇流柔術", "〇〇道場", "〇〇道場", "山田太郎", "柔能制剛")
    assert c.text_drop == 0.05
    assert c.award("dan") == Award("dan", "段位免状", "右授与ス", True, "#8a6a33")
    assert c.award("shihan") == Award("shihan", "師範免許状", "右免許ス", False, "#8a336f")
    assert (c.sample_name, c.sample_rank, c.sample_date, c.sample_suffix) == \
        ("ジョン・ドウ", "5", "today", "sample")
    assert c.source == str(support.EXAMPLE)


def test_minimal_file_takes_defaults(tmp_path):
    c = config_mod.load(write(tmp_path, AWARD))
    assert c.art == "〇〇流柔術" and c.honorific == "殿" and c.text_drop == 0.0
    assert c.award("dan").grade_column is False
    assert c.award("dan").colour == "#8a6a33"


def test_award_lookup_unknown():
    with pytest.raises(KeyError):
        config_mod.load(str(support.EXAMPLE)).award("nope")


@pytest.mark.parametrize("text, message", [
    ("schema = 2\n" + AWARD, "schema = 2, but this build understands 1"),
    ("", "no [[awards]] defined -- there is nothing to print"),
    ("[art]\nname = 'x'\n", "no [[awards]] defined"),
    ('[[awards]]\nslug = "dan"\nformula = "右授与ス"\n', "[[awards]] #1 is missing 'heading'"),
    ('[[awards]]\nheading = "h"\nformula = "f"\n', "[[awards]] #1 is missing 'slug'"),
    (AWARD + '[[awards]]\nslug = "x"\nheading = "h"\n', "[[awards]] #2 is missing 'formula'"),
    (AWARD + AWARD, "two awards share the slug 'dan'"),
    ('[dojo]\ncrest_ring = "一二三四五六"\n' + AWARD,
     "dojo.crest_ring is 6 characters. The lower arc holds four comfortably and five at a squeeze."),
    ('art = "x"\n' + AWARD, "[art] should be a table"),
    ('sample = 5\n' + AWARD, "[sample] should be a table"),
])
def test_invalid_configs(tmp_path, text, message):
    path = write(tmp_path, text)
    with pytest.raises(SystemExit) as e:
        config_mod.load(path)
    assert isinstance(e.value.code, str)
    assert e.value.code.startswith(path) or e.value.code.startswith("no configuration")
    assert message in e.value.code


def test_five_character_crest_ring_is_allowed(tmp_path):
    c = config_mod.load(write(tmp_path, '[dojo]\ncrest_ring = "一二三四五"\n' + AWARD))
    assert c.crest_ring == "一二三四五"


def test_missing_file(tmp_path):
    with pytest.raises(SystemExit) as e:
        config_mod.load(str(tmp_path / "nope.toml"))
    assert e.value.code.startswith(f"no configuration at {tmp_path / 'nope.toml'}")
    assert "--config" in e.value.code


def test_relative_path_is_made_absolute(tmp_path, monkeypatch):
    write(tmp_path, AWARD, "rel.toml")
    monkeypatch.chdir(tmp_path)
    assert config_mod.load("rel.toml").source == str(tmp_path / "rel.toml")


def test_sample_values_become_strings(tmp_path):
    c = config_mod.load(write(tmp_path, AWARD + '[sample]\nrank = 3\nname = "タロウ"\n'))
    assert c.sample_rank == "3" and c.sample_name == "タロウ"


# --------------------------------------------------------- search order ----
def test_search_order(tmp_path, monkeypatch):
    user, local = tmp_path / "user.toml", tmp_path / "local.toml"
    monkeypatch.setattr(config_mod, "USER_CONFIG", str(user))
    monkeypatch.setattr(config_mod, "LOCAL_CONFIG", str(local))
    assert config_mod.default_path() == config_mod.EXAMPLE_CONFIG
    local.write_text(AWARD, encoding="utf-8")
    assert config_mod.default_path() == str(local)
    user.write_text(AWARD, encoding="utf-8")
    assert config_mod.default_path() == str(user)
    assert config_mod.load().source == str(user)


def test_no_local_config_when_not_a_checkout(monkeypatch):
    monkeypatch.setattr(config_mod, "LOCAL_CONFIG", None)
    assert config_mod.default_path() == config_mod.EXAMPLE_CONFIG


# ------------------------------------------------------------ save/load ----
def test_save_load_round_trip(tmp_path):
    c = Config(art="〇〇流", dojo="〇〇館", crest_ring="〇〇〇館", crest_traced=True,
               signer_title="宗家", signer_name='山田 "花子"', honorific="様",
               motto="〇〇\\〇〇", stock_border=18.5, safe_inset=30.0, text_drop=0.12,
               awards=[Award("a", "教士免許状", "右免許ス", False, "#335a8a"),
                       Award("b", "段位免状", "右授与ス", True, "#8a6a33")],
               sample_name="タロウ", sample_rank="3")
    path = config_mod.save(c, str(tmp_path / "sub" / "dojo.toml"))
    assert path == str(tmp_path / "sub" / "dojo.toml")
    assert not (tmp_path / "sub" / "dojo.toml.tmp").exists()
    back = config_mod.load(path)
    for f in ("art", "dojo", "crest_ring", "crest_traced", "signer_title",
              "signer_name", "honorific", "motto", "stock_border", "safe_inset",
              "text_drop", "awards"):
        assert getattr(back, f) == getattr(c, f), f
    # [sample] is a specimen's, never a saved dōjō's
    assert back.sample_name == "" and back.sample_rank == ""


def test_save_defaults_to_the_user_config(home):
    c = config_mod.load(str(support.EXAMPLE))
    path = config_mod.save(c)
    assert path == config_mod.USER_CONFIG
    assert config_mod.load(path).slugs == ["dan", "shihan", "renshi"]
