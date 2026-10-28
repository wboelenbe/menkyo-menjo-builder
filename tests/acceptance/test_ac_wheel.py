"""AC-2 and AC-3: what the wheel holds, and the wheel installed and run from
outside the checkout.  Builds with `uv build` and installs into a throwaway
virtualenv, once per session."""

import sys
import tarfile
import zipfile

import pytest

import support

pytestmark = pytest.mark.slow

MODULES = ["__init__", "__main__", "border", "build_diploma", "config", "ink",
           "paths", "service"]


def _names(dist):
    with zipfile.ZipFile(dist["wheel"]) as z:
        return z.namelist(), z


def _dist_info(names, leaf):
    hits = [n for n in names if n.endswith(".dist-info/" + leaf)]
    assert len(hits) == 1, (leaf, hits)
    return hits[0]


# ------------------------------------------------------------------ AC-2 ----
def test_ac2_wheel_name_and_version(dist):
    v = support.project_version()
    assert dist["wheel"].name == f"menkyo-{v}-py3-none-any.whl"
    assert dist["sdist"].name == f"menkyo-{v}.tar.gz"


def test_ac2_wheel_holds_the_package_and_its_data(dist):
    names, _ = _names(dist)
    for m in MODULES:
        assert f"menkyo/{m}.py" in names
    for data in ("menkyo/example.toml", "menkyo/fonts/YujiBoku-Regular.ttf",
                 "menkyo/fonts/OFL.txt"):
        assert data in names
    with zipfile.ZipFile(dist["wheel"]) as z:
        assert z.read("menkyo/example.toml") == support.EXAMPLE.read_bytes()
        assert z.read("menkyo/fonts/YujiBoku-Regular.ttf") == \
            (support.PACKAGE / "fonts" / "YujiBoku-Regular.ttf").read_bytes()


def test_ac2_wheel_holds_nothing_else(dist):
    names, _ = _names(dist)
    payload = [n for n in names if ".dist-info/" not in n]
    assert all(n.startswith("menkyo/") for n in payload), payload
    for n in names:
        assert "__pycache__" not in n and not n.endswith(".pyc"), n
        leaf = n.rsplit("/", 1)[-1]
        assert leaf not in ("gui.py", "app.py", "dojo.toml", "index.html"), n
        assert not any(part in n.split("/") for part in
                       ("web", "packaging", "deploy", "tests", "crest", "ref", "build")), n


def test_ac2_metadata(dist):
    names, _ = _names(dist)
    with zipfile.ZipFile(dist["wheel"]) as z:
        meta = z.read(_dist_info(names, "METADATA")).decode()
        entry = z.read(_dist_info(names, "entry_points.txt")).decode()
    assert f"Version: {support.project_version()}" in meta
    assert "Requires-Python: >=3.11" in meta
    for dep in ("pillow", "numpy", "scipy"):
        assert f"Requires-Dist: {dep}" in meta
    assert "[console_scripts]" in entry
    assert "menkyo = menkyo.build_diploma:cli" in entry
    licences = [n for n in names if "/licenses/" in n]
    assert {n.rsplit("/", 1)[-1] for n in licences} >= {"LICENSE", "NOTICE", "OFL.txt"}


def test_ac2_sdist_holds_no_personal_data(dist):
    with tarfile.open(dist["sdist"]) as t:
        names = [n.split("/", 1)[1] for n in t.getnames() if "/" in n]
    assert "src/menkyo/build_diploma.py" in names and "pyproject.toml" in names
    assert "src/menkyo/fonts/YujiBoku-Regular.ttf" in names
    for n in names:
        top = n.split("/")[0]
        assert top not in ("dojo.toml", "crest", "ref", "build", "dist", ".venv",
                           "web", "deploy", "packaging"), n
        assert not n.endswith("dojo.toml"), n


# ------------------------------------------------------------------ AC-3 ----
def test_ac3_version_from_metadata(installed, home, tmp_path):
    env = support.isolated_env(home)
    for exe in ([str(installed["menkyo"])], [str(installed["python"]), "-m", "menkyo"]):
        r = support.run_menkyo(["--version"], env, tmp_path, exe=exe)
        assert (r.returncode, r.stdout) == (0, f"menkyo {support.project_version()}\n")


def test_ac3_example_config(installed, home, tmp_path):
    r = support.run_menkyo(["--example-config"], support.isolated_env(home), tmp_path,
                           exe=[str(installed["menkyo"])])
    assert r.returncode == 0
    assert r.stdout.encode("utf-8") == support.EXAMPLE.read_bytes()


def test_ac3_runs_from_outside_the_checkout(installed, fake_tools, home, tmp_path):
    """With a trap dojo.toml in the cwd: an installed copy never reads it."""
    (tmp_path / "dojo.toml").write_text(
        'schema = 1\n[[awards]]\nslug = "trap"\nheading = "免許状"\nformula = "右免許ス"\n',
        encoding="utf-8")
    exe = [str(installed["menkyo"])]
    r = support.run_menkyo(["--list", "-v", "overlay"], fake_tools.env(home), tmp_path, exe=exe)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == ["dan-overlay-sample.pdf", "shihan-overlay-sample.pdf",
                                     "renshi-overlay-sample.pdf"]

    r = support.run_menkyo(["-a", "dan", "-v", "overlay,overlay-flat", "--press", "-d", "",
                            "--json"], fake_tools.env(home), tmp_path, exe=exe)
    assert r.returncode == 0, r.stderr
    ev = support.events(r.stdout)
    docs = home / "Documents" / "Menkyo"
    assert ev[-1] == {"event": "done", "out": str(docs), "files": [
        str(docs / "dan-overlay-sample.pdf"), str(docs / "dan-overlay-sample-K.pdf"),
        str(docs / "dan-overlay-flat-sample.pdf"), str(docs / "dan-overlay-flat-sample-K.pdf")]}
    site = next(installed["venv"].glob("lib/python*/site-packages"))
    fonts = site / "menkyo" / "fonts"
    for call in fake_tools.calls("inkscape"):
        assert call["fontconfig"] and call["font_dirs"][0] == str(fonts)
    assert (fonts / "YujiBoku-Regular.ttf").is_file()


@pytest.mark.render
def test_ac3_installed_wheel_renders_with_the_font(installed, inkscape, ghostscript,
                                                   home, tmp_path):
    """The release workflow's smoke test: a font missing from the wheel fails here."""
    from conftest import require_program
    pdffonts = require_program("pdffonts")
    exe = [str(installed["menkyo"])]
    env = support.isolated_env(home)
    ex = support.run_menkyo(["--example-config"], env, tmp_path, exe=exe)
    (tmp_path / "example.toml").write_text(ex.stdout, encoding="utf-8")
    r = support.run_menkyo(["-c", "example.toml", "-a", "dan", "-v", "overlay,overlay-flat",
                            "--press", "--json", "--out", "out"], env, tmp_path, exe=exe)
    assert r.returncode == 0, r.stdout + r.stderr
    assert support.events(r.stdout)[-1]["event"] == "done"
    import subprocess
    fonts = subprocess.run([pdffonts, str(tmp_path / "out" / "dan-overlay-flat-sample.pdf")],
                           capture_output=True, text=True).stdout
    assert "yuji" in fonts.lower(), fonts
