"""AC-4 and AC-16: where a checkout and an installed copy look for things.

An "installed copy" here is src/menkyo copied somewhere with no pyproject.toml
two levels up -- what site-packages looks like -- so it runs without building
anything.  test_ac_wheel.py repeats the important parts with the real wheel.
All configurations involved are written by the tests.
"""

import json
import subprocess
import sys

import pytest

import support
from menkyo import build_diploma as bd
from menkyo import config as config_mod
from menkyo import paths

PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from menkyo import config, paths
print(json.dumps({
    "checkout_root": paths.checkout_root(),
    "default_output_dir": paths.default_output_dir(),
    "user_data_dir": paths.user_data_dir(),
    "local_config": config.LOCAL_CONFIG,
    "user_config": config.USER_CONFIG,
    "default_path": config.default_path(),
    "example": config.EXAMPLE_CONFIG,
    "fonts": paths.resource("fonts"),
}))
"""


def probe(site, home):
    r = subprocess.run([sys.executable, "-I", "-c", PROBE, str(site)],
                       env=support.isolated_env(home), cwd=str(home),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def user_dir(home):
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Menkyo"
    return home / ".config" / "Menkyo"


def award_config(slug):
    return (f'schema = 1\n[[awards]]\nslug = "{slug}"\nheading = "免許状"\n'
            f'formula = "右免許ス"\n')


def list_awards(site, home, cwd):
    """`menkyo --list -n ''` from the copy at `site`; the slugs it would write."""
    r = subprocess.run(
        [sys.executable, "-I", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); "
         "from menkyo.build_diploma import cli; cli(sys.argv[2:])",
         str(site), "--list", "-n", "", "-r", "", "-v", "overlay"],
        env=support.isolated_env(home), cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return [line.split("-overlay")[0] for line in r.stdout.splitlines()]


# ------------------------------------------------------------------ AC-4 ----
def test_ac4_checkout(tmp_path):
    """The real checkout: repository root, ./build, ./dojo.toml (path only --
    the file itself is never opened here)."""
    got = probe(support.SRC, tmp_path)
    assert got["checkout_root"] == str(support.REPO)
    assert got["default_output_dir"] == str(support.REPO / "build")
    assert got["local_config"] == str(support.REPO / "dojo.toml")
    assert got["example"] == str(support.EXAMPLE)
    assert got["user_config"] == str(user_dir(tmp_path) / "dojo.toml")


def test_ac4_installed_copy_looks_only_at_itself(tmp_path):
    home, site = tmp_path / "home", tmp_path / "lib" / "site"
    home.mkdir(exist_ok=True)
    pkg = support.copy_package(site)
    # Traps: a dojo.toml beside the package, above it, and in the cwd.
    for d in (site, site.parent, tmp_path, home):
        (d / "dojo.toml").write_text(award_config("trap"), encoding="utf-8")

    got = probe(site, home)
    assert got["checkout_root"] is None
    assert got["local_config"] is None
    assert got["default_output_dir"] == str(home / "Documents" / "Menkyo")
    assert got["user_data_dir"] == str(user_dir(home))
    assert got["default_path"] == str(pkg / "example.toml")
    assert got["fonts"] == str(pkg / "fonts")
    # kyu-grades (its OQ-5) appended a fourth award, kyu, to the example
    assert list_awards(site, home, cwd=home) == ["dan", "shihan", "renshi", "kyu"]

    # the per-user configuration is the one an installed copy honours
    user_dir(home).mkdir(parents=True)
    (user_dir(home) / "dojo.toml").write_text(award_config("mine"), encoding="utf-8")
    assert probe(site, home)["default_path"] == str(user_dir(home) / "dojo.toml")
    assert list_awards(site, home, cwd=home) == ["mine"]


def test_ac4_checkout_copy_uses_its_root_dojo_toml(tmp_path):
    """Search order in a checkout: per-user, then the root dojo.toml, then the example."""
    home, root = tmp_path / "home", tmp_path / "repo"
    home.mkdir(exist_ok=True)
    support.copy_package(root / "src")
    (root / "pyproject.toml").write_text('[project]\nname = "menkyo"\nversion = "9.9.9"\n')
    got = probe(root / "src", home)
    assert got["checkout_root"] == str(root)
    assert got["default_output_dir"] == str(root / "build")
    assert got["default_path"] == str(root / "src" / "menkyo" / "example.toml")

    (root / "dojo.toml").write_text(award_config("root"), encoding="utf-8")
    assert list_awards(root / "src", home, cwd=tmp_path) == ["root"]
    user_dir(home).mkdir(parents=True)
    (user_dir(home) / "dojo.toml").write_text(award_config("mine"), encoding="utf-8")
    assert list_awards(root / "src", home, cwd=tmp_path) == ["mine"]


def test_ac4_another_projects_pyproject_is_not_a_checkout(tmp_path):
    """Agreement 5: a copy vendored under another project's pyproject.toml
    behaves as installed."""
    home, root = tmp_path / "home", tmp_path / "portal"
    home.mkdir(exist_ok=True)
    support.copy_package(root / "vendor")
    (root / "pyproject.toml").write_text('[project]\nname = "dojo-portal"\nversion = "1.0"\n')
    (root / "dojo.toml").write_text(award_config("trap"), encoding="utf-8")
    got = probe(root / "vendor", home)
    assert got["checkout_root"] is None and got["local_config"] is None
    assert got["default_output_dir"] == str(home / "Documents" / "Menkyo")
    assert list_awards(root / "vendor", home, cwd=root) == ["dan", "shihan", "renshi", "kyu"]


@pytest.mark.render
def test_ac4_installed_copy_writes_to_documents(tmp_path):
    home, site = tmp_path / "home", tmp_path / "site"
    home.mkdir(exist_ok=True)
    support.copy_package(site)
    r = subprocess.run(
        [sys.executable, "-I", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); "
         "from menkyo.build_diploma import cli; cli(sys.argv[2:])",
         str(site), "-c", str(support.EXAMPLE), "-a", "dan", "-v", "overlay-flat",
         "-d", ""],
        env=support.isolated_env(home), cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    target = home / "Documents" / "Menkyo" / "dan-overlay-flat-a3-sample.pdf"
    assert r.stdout.splitlines()[0] == f"wrote {target}"
    assert target.exists()
    # That the copy reads its own fonts is render-without-inkscape's AC-10:
    # remove one from a copy and the run fails, naming the copy's file.


def test_ac4_fonts_and_example_are_package_resources():
    assert paths.resource("fonts", "YujiBoku-Regular.ttf") == \
        str(support.PACKAGE / "fonts" / "YujiBoku-Regular.ttf")
    assert (support.PACKAGE / "fonts" / "YujiBoku-Regular.ttf").is_file()
    assert (support.PACKAGE / "fonts" / "OFL.txt").is_file()
    assert config_mod.EXAMPLE_CONFIG == str(support.EXAMPLE)
    assert bd.FONT_DIR == str(support.PACKAGE / "fonts")


# ----------------------------------------------------------------- AC-16 ----
GLYPH = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 120">'
         '<path d="M1 2 L30 40 Z"/></svg>')


def test_ac16_traced_glyphs_beside_the_config(tmp_path, monkeypatch):
    (tmp_path / "crest").mkdir()
    (tmp_path / "crest" / "〇.svg").write_text(GLYPH, encoding="utf-8")
    cfg = tmp_path / "traced.toml"
    cfg.write_text('schema = 1\n[dojo]\ncrest_ring = "〇〇道場"\ntraced_glyphs = true\n'
                   + award_config("x").split("\n", 1)[1], encoding="utf-8")
    monkeypatch.setattr(bd, "CFG", config_mod.load(str(cfg)))
    svg = bd.document("右免許ス", "免許状", crest_kind="bottom", layer="chrome")
    assert svg.count('<path d="M1 2 L30 40 Z"') == 2      # 〇〇 traced
    assert ">道</text>" in svg and ">場</text>" in svg     # no trace: the font


def test_ac16_traced_glyphs_off_uses_the_font(tmp_path, monkeypatch):
    (tmp_path / "crest").mkdir()
    (tmp_path / "crest" / "〇.svg").write_text(GLYPH, encoding="utf-8")
    cfg = tmp_path / "plain.toml"
    cfg.write_text('schema = 1\n[dojo]\ncrest_ring = "〇〇道場"\n'
                   + award_config("x").split("\n", 1)[1], encoding="utf-8")
    monkeypatch.setattr(bd, "CFG", config_mod.load(str(cfg)))
    svg = bd.document("右免許ス", "免許状", crest_kind="bottom", layer="chrome")
    assert "M1 2 L30 40" not in svg and svg.count(">〇</text>") == 2
