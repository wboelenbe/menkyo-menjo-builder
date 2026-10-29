#!/bin/sh
# Run the test suite in the Docker test image, where Inkscape is installed and
# REQUIRE_RENDER=1 turns a skipped render into a failure.
#
#   scripts/test-docker.sh                   the whole suite
#   scripts/test-docker.sh -k render -x      arguments go to pytest
#
# The image is built from tests/docker/Dockerfile; its context leaves out
# dojo.toml, crest/, ref/, build/, dist/ and .venv.
set -eu
cd "$(dirname "$0")/.."
docker build -f tests/docker/Dockerfile -t menkyo-test .
exec docker run --rm -e REQUIRE_RENDER=1 menkyo-test uv run --frozen pytest "$@"
