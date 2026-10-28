"""web/app.py through FastAPI's TestClient, with the stand-in inkscape / gs.

The per-user configuration it reads and writes is the test's own (see
conftest.isolate_user_files).
"""

import importlib.util
import io
import zipfile

import pytest

import support

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from menkyo import config as config_mod  # noqa: E402
from menkyo.service import GRADES  # noqa: E402


@pytest.fixture(scope="module")
def web_app():
    spec = importlib.util.spec_from_file_location("menkyo_web_app", support.REPO / "web" / "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def client(web_app):
    return TestClient(web_app.app)


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200 and "<html" in r.text.lower()


def test_state_unconfigured(client):
    s = client.get("/api/state").json()
    assert s["configured"] is False
    assert s["settings"]["art"] == "〇〇流柔術" and s["settings"]["dojo"] == "〇〇道場"
    assert [a["slug"] for a in s["awards"]] == ["dan", "shihan", "renshi"]
    assert [a["grade_column"] for a in s["awards"]] == [True, False, False]
    assert s["grades"] == GRADES
    assert {o["value"] for o in s["outputs"]} == {"overlay", "full-cream", "overlay,full-cream"}


def test_settings_saved_to_the_user_config(client):
    body = {"art": "〇〇流", "dojo": "〇〇館", "crest_ring": "〇〇館", "signer_title": "宗家",
            "signer_name": "", "motto": "", "honorific": "様"}
    r = client.put("/api/settings", json=body)
    assert r.status_code == 200 and r.json() == {"ok": True}
    saved = config_mod.load(config_mod.USER_CONFIG)
    assert (saved.art, saved.dojo, saved.honorific) == ("〇〇流", "〇〇館", "様")
    s = client.get("/api/state").json()
    assert s["configured"] is True and s["settings"]["art"] == "〇〇流"


@pytest.mark.parametrize("body, status", [
    ({"crest_ring": "一二三四五六"}, 400),
    ({"art": "ア" * 41}, 400),
])
def test_settings_rejected(client, body, status):
    assert client.put("/api/settings", json=body).status_code == status


def test_generate_one_pdf(client, fake_tools):
    r = client.post("/api/generate", json={"award": "dan", "name": "ヤン・ヤンセン",
                                           "grade": "二段", "date": "2026-09-05",
                                           "output": "overlay"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    cd = r.headers["content-disposition"]
    assert cd.startswith('attachment; filename="dan-overlay-')
    assert "filename*=UTF-8''dan-overlay-%E4%BA%8C%E6%AE%B5-" in cd


def test_generate_two_as_a_zip(client, fake_tools):
    r = client.post("/api/generate", json={"award": "shihan", "output": "overlay,full-cream",
                                           "press": True})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    # the blank form: no [sample] tag, and the press files ride along
    assert sorted(names) == sorted(["shihan-overlay.pdf", "shihan-overlay-K.pdf",
                                    "shihan-full-cream.pdf", "shihan-full-cream-CMYK.pdf"])


@pytest.mark.parametrize("body, detail", [
    ({"award": "dan", "grade": "11段", "output": "overlay"}, "Unknown grade."),
    ({"award": "nope", "output": "overlay"}, "Unknown certificate type."),
    ({"award": "dan", "output": "proof"}, "Unknown output kind."),
    ({"award": "dan", "date": "2026-02-30", "output": "overlay"}, "That date does not exist."),
])
def test_generate_form_errors(client, fake_tools, body, detail):
    r = client.post("/api/generate", json=body)
    assert r.status_code == 400 and detail in r.json()["detail"]


def test_generate_tool_failure(client, fake_tools, monkeypatch):
    monkeypatch.setenv("FAKE_INKSCAPE_FAIL", "pdf")
    r = client.post("/api/generate", json={"award": "dan", "output": "overlay"})
    assert r.status_code == 500 and "inkscape failed." in r.json()["detail"]
