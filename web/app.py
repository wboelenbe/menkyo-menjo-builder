"""Web front end: one page, three endpoints, no stored certificates.

    GET  /               the form
    GET  /api/state      awards, settings and options for the form
    PUT  /api/settings   save the dōjō's details
    POST /api/generate   render, return the PDF (or a zip of several)

Run:  uvicorn app:app --app-dir web --host 127.0.0.1 --port 8000
Authentication is not done here; put it in the reverse proxy (see deploy/).
"""

import datetime
import io
import os
import sys
import tempfile
import threading
import zipfile
from typing import Optional
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
# An installed menkyo (the deploy image) is used as installed; a bare checkout
# without one finds the package in ../src.
try:
    import menkyo  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.join(HERE, "..", "src"))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse, Response  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from menkyo import config as config_mod  # noqa: E402
from menkyo.service import GRADES, OUTPUTS, FormError, make_argv, run_build  # noqa: E402

app = FastAPI(title="Menkyo", docs_url=None, redoc_url=None, openapi_url=None)

# build_diploma keeps its state in module globals, and a render can take a
# couple of GB of RAM: one at a time, the rest wait their turn.
_build_lock = threading.Lock()
LOCK_WAIT_SECONDS = 180

SETTINGS = ["art", "dojo", "crest_ring", "signer_title", "signer_name",
            "motto", "honorific"]
SETTING_MAX = 40


class Settings(BaseModel):
    art: str = ""
    dojo: str = ""
    crest_ring: str = ""
    signer_title: str = ""
    signer_name: str = ""
    motto: str = ""
    honorific: str = ""


class Generate(BaseModel):
    award: str
    name: str = ""
    grade: str = ""
    date: str = ""            # ISO, or '' for a blank slot
    output: str
    press: bool = False


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "index.html"))


@app.get("/api/state")
def state():
    cfg = config_mod.load()
    return {
        "configured": os.path.exists(config_mod.USER_CONFIG),
        "settings": {k: getattr(cfg, k) for k in SETTINGS},
        "awards": [{"slug": a.slug, "heading": a.heading,
                    "grade_column": a.grade_column} for a in cfg.awards],
        "outputs": [{"label": k, "value": v} for k, v in OUTPUTS.items()],
        "grades": GRADES,
        "today": datetime.date.today().isoformat(),
    }


@app.put("/api/settings")
def save_settings(s: Settings):
    values = {k: getattr(s, k).strip() for k in SETTINGS}
    if any(len(v) > SETTING_MAX for v in values.values()):
        raise HTTPException(400, f"Each field is at most {SETTING_MAX} characters.")
    if len(values["crest_ring"]) > 5:
        raise HTTPException(
            400, "The crest holds at most five characters (four looks best).")
    cfg = config_mod.load()
    for k, v in values.items():
        setattr(cfg, k, v)
    config_mod.save(cfg)
    return {"ok": True}


def _content_disposition(filename):
    ascii_name = "".join(c if c.isascii() and c not in '"\\' else "_" for c in filename)
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'


@app.post("/api/generate")
def generate(req: Generate):
    cfg = config_mod.load()
    with tempfile.TemporaryDirectory(prefix="menkyo-") as out:
        try:
            argv = make_argv(cfg, award=req.award, name=req.name, grade=req.grade,
                             date=req.date, output=req.output, folder=out,
                             press=req.press)
        except FormError as e:
            raise HTTPException(400, str(e))

        if not _build_lock.acquire(timeout=LOCK_WAIT_SECONDS):
            raise HTTPException(503, "The server is busy making another "
                                     "certificate. Please try again in a minute.")
        try:
            ok, files, msg = run_build(argv)
        finally:
            _build_lock.release()
        if not ok:
            raise HTTPException(500, msg or "The certificate could not be made.")
        files = [f for f in files if f.endswith(".pdf") and os.path.dirname(f) == out]
        if not files:
            raise HTTPException(500, "No certificate was produced.")

        if len(files) == 1:
            with open(files[0], "rb") as fh:
                data = fh.read()
            return Response(data, media_type="application/pdf", headers={
                "Content-Disposition": _content_disposition(os.path.basename(files[0])),
                "Cache-Control": "no-store"})

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:   # PDFs: already packed
            for f in files:
                z.write(f, os.path.basename(f))
        return Response(buf.getvalue(), media_type="application/zip", headers={
            "Content-Disposition": _content_disposition("certificates.zip"),
            "Cache-Control": "no-store"})
