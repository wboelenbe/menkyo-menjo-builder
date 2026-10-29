"""The sheet: document()'s root and scale per size, the names, and the
[paper] size key.  No renders; the acceptance tests draw the pages."""

import math
import re

import pytest

import support
from menkyo import build_diploma as bd
from menkyo import config as config_mod

EX = str(support.EXAMPLE)


@pytest.fixture
def example_cfg(monkeypatch):
    monkeypatch.setattr(bd, "CFG", config_mod.load(EX))


@pytest.mark.parametrize("layer", ["all", "chrome", "text"])
def test_a3_has_no_wrapper_and_is_the_default(layer, example_cfg):
    a3 = bd.document("右授与ス", "段位免状", layer=layer, sheet="a3")
    assert a3 == bd.document("右授与ス", "段位免状", layer=layer)
    assert 'width="420.0mm" height="297.0mm" viewBox="0 0 420.0 297.0"' in a3
    assert not a3.split("\n")[1].startswith('<g transform="scale')
    assert a3.endswith("</svg>")


@pytest.mark.parametrize("layer", ["all", "chrome", "text"])
def test_a4_wraps_the_a3_layout_in_one_scale(layer, example_cfg):
    a3 = bd.document("右授与ス", "段位免状", layer=layer)
    a4 = bd.document("右授与ス", "段位免状", layer=layer, sheet="a4")
    assert re.match(r'<svg [^>]*width="297.0mm" height="210.0mm" '
                    r'viewBox="0 0 297.0 210.0">\n<g transform="scale\(0.7071067812\)">', a4)
    assert a4.endswith("</g>\n</svg>")
    # inside the wrapper, the A3 layout as it is
    body3 = a3.split("\n", 1)[1][:-len("</svg>")]
    body4 = a4.split("\n", 2)[2][:-len("</g>\n</svg>")]
    assert body3 == body4


def test_scale_is_one_over_root_two():
    assert bd.SCALE["a4"] == pytest.approx(1 / math.sqrt(2))
    w, h = bd.PAPERS["a4"]
    assert abs(bd.PAGE_W * bd.SCALE["a4"] - w) < 0.03
    assert abs(bd.PAGE_H * bd.SCALE["a4"] - h) < 0.03
    assert set(bd.PAPERS) == set(bd.SCALE) == set(config_mod.PAPER_SIZES)
    assert bd.DEFAULT_PAPER == config_mod.Config.paper_size == config_mod.DEFAULT_PAPER


@pytest.mark.parametrize("sheet, suffix, stem", [
    ("a3", "", "dan-overlay-a3"),
    ("a4", "sample", "dan-overlay-a4-sample"),
    ("a3", "a4", "dan-overlay-a3-a4"),          # OQ-7: allowed, the size is first
])
def test_stem(sheet, suffix, stem):
    assert bd._stem("dan", "overlay", sheet, suffix) == stem


def _cfg(tmp_path, line):
    text = support.EXAMPLE.read_text(encoding="utf-8").replace(
        'size = "a3"\n', line, 1)
    p = tmp_path / "c.toml"
    p.write_text(text, encoding="utf-8")
    return str(p)


@pytest.mark.parametrize("line, size", [('size = "a4"\n', "a4"), ('size = "A4"\n', "a4"),
                                        ("", "a3")])
def test_config_size(line, size, tmp_path):
    cfg = config_mod.load(_cfg(tmp_path, line))
    assert cfg.paper_size == size
    assert cfg.paper_size_set == bool(line)       # what --help says about it


@pytest.mark.parametrize("value", ['"a5"', "4", '""', "true", '["a4"]'])
def test_config_size_refused(value, tmp_path):
    path = _cfg(tmp_path, f"size = {value}\n")
    with pytest.raises(SystemExit) as e:
        config_mod.load(path)
    msg = str(e.value.code)
    assert path in msg and "[paper] size" in msg and '"a3" or "a4"' in msg, msg


def test_save_writes_the_size(tmp_path):
    cfg = config_mod.load(_cfg(tmp_path, 'size = "A4"\n'))
    out = config_mod.save(cfg, str(tmp_path / "saved" / "dojo.toml"))
    assert 'size = "a4"' in open(out, encoding="utf-8").read().splitlines()
    assert config_mod.load(out).paper_size == "a4"
