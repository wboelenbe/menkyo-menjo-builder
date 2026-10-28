"""AC-14 and AC-15: the CI workflow runs the suite, and the test image never
sees personal data.  Static checks on the files; the Docker image's own build
re-checks the context (tests/docker/Dockerfile).

AC-14 was rewritten for the cli-only item (its AC-13): there is no release
job any more.  The workflow tests every push and pull request, with real
renders, and smoke-tests the installed wheel; nothing is published.
"""

import re

import support

WORKFLOW = support.REPO / ".github" / "workflows" / "package.yml"
DOCKERFILE = support.TESTS / "docker" / "Dockerfile"
DOCKERIGNORE = support.TESTS / "docker" / "Dockerfile.dockerignore"


def test_ac14_workflow_tests_every_push_with_renders():
    wf = WORKFLOW.read_text(encoding="utf-8")
    on = wf.split("\non:", 1)[1].split("\njobs:", 1)[0]
    assert re.search(r"^  push:", on, re.M) and re.search(r"^  pull_request:", on, re.M)
    assert re.search(r"REQUIRE_RENDER[:=]\s*\"?1", wf), "the suite must run with REQUIRE_RENDER=1"
    assert re.search(r"uv run[^\n]*pytest", wf)
    assert "Smoke test the installed wheel" in wf
    build = re.search(r"^\s*-?\s*run: uv build\b", wf, re.M)
    assert build, "the smoke test installs a wheel the workflow built"
    assert build.start() < wf.index("Smoke test the installed wheel")


def test_ac14_workflow_publishes_nothing():
    wf = WORKFLOW.read_text(encoding="utf-8")
    jobs = re.findall(r"^  ([\w-]+):\s*$", wf.split("\njobs:", 1)[1], re.M)
    assert len(jobs) == 1, jobs
    for gone in (r"\btags:", r"refs/tags", r"GITHUB_REF_NAME", r"gh\s+release",
                 r"upload-artifact", r"download-artifact", r"contents:\s*write",
                 r"^  release:"):
        assert not re.search(gone, wf, re.M), gone


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
