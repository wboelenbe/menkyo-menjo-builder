"""AC-14 and AC-15: the release workflow runs the suite, and the test image
never sees personal data.  Static checks on the files; the Docker image's own
build re-checks the context (tests/docker/Dockerfile)."""

import re

import support

WORKFLOW = support.REPO / ".github" / "workflows" / "package.yml"
DOCKERFILE = support.TESTS / "docker" / "Dockerfile"
DOCKERIGNORE = support.TESTS / "docker" / "Dockerfile.dockerignore"


def test_ac14_workflow_runs_the_suite_with_renders_before_releasing():
    wf = WORKFLOW.read_text(encoding="utf-8")
    build, release = wf.split("\n  release:", 1)
    assert re.search(r"REQUIRE_RENDER[:=]\s*\"?1", build), "the build job must set REQUIRE_RENDER=1"
    assert "pytest" in build
    assert "Smoke test the installed wheel" in build
    assert "needs: build" in release
    # the suite runs before the artifact the release job publishes is uploaded
    assert build.index("pytest") < build.index("actions/upload-artifact")


def test_ac15_docker_context_excludes_personal_data():
    ignored = {l.strip().strip("/") for l in DOCKERIGNORE.read_text().splitlines()
               if l.strip() and not l.startswith("#")}
    for entry in ("dojo.toml", "crest", "ref", "build", "dist", ".venv"):
        assert entry in ignored or f"**/{entry}" in ignored, entry
    df = DOCKERFILE.read_text(encoding="utf-8")
    assert "REQUIRE_RENDER=1" in df
    assert "test ! -e dojo.toml" in df


def test_ac15_tests_cannot_reach_a_real_configuration():
    """conftest has moved the per-user and repository-root dojo.toml out of reach."""
    import conftest
    from menkyo import config as config_mod
    assert config_mod.default_path() == config_mod.EXAMPLE_CONFIG
    assert not config_mod.USER_CONFIG.startswith(conftest.REAL_HOME + "/")
