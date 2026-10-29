# The test image: the whole suite, real renders included, on Linux.
#
#   scripts/test-docker.sh            builds this and runs the suite in it
#
# Nothing but Python: the package renders with fontTools and pypdfium2 and
# needs no program, font or library from the system, so no system package
# is installed here, and a suite that passes in this image shows it.
#
# Built from the repository root with tests/docker/Dockerfile.dockerignore,
# which keeps dojo.toml, crest/, ref/, build/, dist/ and .venv out of the
# context; the guard below fails the build if any of them got in anyway.
FROM python:3.13-slim-bookworm

RUN pip install --no-cache-dir --root-user-action=ignore uv==0.13.1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /src
# Dependencies first, so a source change does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN test ! -e dojo.toml && test ! -e crest && test ! -e ref \
 && test ! -e build && test ! -e dist && test ! -e .venv \
 && ! find . -name dojo.toml | grep -q .
# The second build warms uv's cache with the build backend, for the wheel tests.
RUN uv sync --frozen \
 && uv build --out-dir /tmp/prebuild && rm -rf /tmp/prebuild

CMD ["uv", "run", "--frozen", "pytest"]
