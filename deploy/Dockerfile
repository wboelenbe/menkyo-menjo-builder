FROM python:3.13-slim-bookworm

# Inkscape and Ghostscript do the rendering; the Noto CJK fonts supply the
# crest lettering (FONT_CREST), which the vendored Yuji Boku does not cover.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        inkscape ghostscript fontconfig fonts-noto-cjk fonts-noto-cjk-extra \
 && rm -rf /var/lib/apt/lists/* \
 && inkscape --version \
 && (fc-list | grep -qi "Noto Serif CJK JP" \
     || echo "WARNING: Noto Serif CJK JP not found - crest lettering will fall back")

WORKDIR /app
COPY requirements.txt /app/requirements.txt
COPY web/requirements.txt /app/web/requirements.txt
RUN pip install --no-cache-dir -r web/requirements.txt

COPY src /app/src
COPY fonts /app/fonts
COPY config /app/config
COPY web /app/web
COPY LICENSE NOTICE /app/

# Unprivileged user. Inkscape wants a writable HOME; the dojo's settings live
# in /data (paths.user_data_dir() honours XDG_CONFIG_HOME), which is a volume.
RUN useradd -m -u 1000 app && mkdir /data && chown app /data
ENV HOME=/home/app XDG_CONFIG_HOME=/data PYTHONUNBUFFERED=1
VOLUME /data
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/state')"

# One worker: builds are serialised anyway, and each can use a couple of GB.
CMD ["uvicorn", "app:app", "--app-dir", "web", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
