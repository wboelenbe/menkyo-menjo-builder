# CLAUDE.md

Generator for Japanese dan-grade, kyū-grade and menkyo certificates (dan and
licences: A3 or A4 landscape, vertical text; kyū: A4 portrait, horizontal),
shipped as the Python package `menkyo` with a `menkyo` CLI.
Read [README.md](README.md) for usage and [DECISIONS.md](DECISIONS.md) for
why things are the way they are; its `## Open` section is the todo list.

## Context & working with the user

- Owner: Wouter, who teaches Hakko Ryu jujutsu (dōjō in Vorselaar). The
  certificates are printed and issued for real.
- Consumer: `~/dev/dojo-portal` (Django), the only front end. It builds the
  wheel from this checkout with `uv build --wheel` and runs
  `menkyo … --json` in a subprocess. Keep the CLI flags and the `--json`
  events (README, "As a package") backwards compatible; changing them is a
  decision for the user.
- When something is unclear, **ask questions one at a time** (requirements
  first, then design, then details). Recommend an option rather than listing
  every alternative.
- Build work runs through the `/feature` skill: tester, developer, docs,
  reviewer ([.claude/agents/](.claude/agents/)).
- Prose (README, DECISIONS, docs) follows the user's house style in
  `~/dev/house-style` (`principles/` and `writing/`): British English,
  sentence-case headings, single quotes, spaced en dash, no serial comma.
  The `docs` agent applies it.
- **Commits:** the orchestrator makes exactly two per `/feature` run (a
  snapshot before, the validated result after). Never push, tag, amend,
  stash, reset, rebase or switch branches; the user pushes.
  Subagents never change git state.

## Personal data (non-negotiable)

- `dojo.toml` in the repository root and
  `~/Library/Application Support/Menkyo/dojo.toml` hold a real dōjō's
  identity, and a run without `-c` picks them up. **Every render in tests,
  checks and docs pins `-c src/menkyo/example.toml`** (or a config written
  by the test). Tests must also isolate `HOME` / `XDG_CONFIG_HOME` so the
  per-user file is never read.
- Never commit `dojo.toml`, `crest/`, `ref/`, `build/` or any rendered
  certificate carrying a real name.

## Layout & rules

- `src/menkyo/` is the package (everything the wheel ships) and the
  `menkyo` command is the product; there is no other front end here.
- The generator keeps its state in module globals (`CFG`, `BUILD`,
  `PROGRESS`); one run at a time per process.
- Rendering is pure Python (fontTools outlines, an own PDF writer, pypdfium2
  for the rasters; fonts bundled in `src/menkyo/fonts/`), so it runs on the
  Mac too. No system tool or system font is used. The Docker test image is
  the Linux check.
- Python 3.11+ (`tomllib`). Match the surrounding code: its comment density,
  docstring tone and naming. No formatter is applied to existing code.
- The version lives only in `pyproject.toml`.

## Commands

```sh
uv run menkyo -c src/menkyo/example.toml --list   # what a build would write
uv run pytest                                      # the full suite, real renders
scripts/test-docker.sh                             # the same suite on Linux (slim image)
uv build --wheel                                   # the wheel into dist/
```

**Run both test commands locally before every hand-off and every commit.**
`origin` is the NAS (`wouter@datastore:/volume1/git/menkyo-menjo-builder`)
and `github` is a secondary remote, so GitHub CI does not run on normal
pushes; the local runs are the check.

Releases: bump the version in `pyproject.toml` and commit; the portal builds
its wheel from the checkout with `uv build --wheel`. Nothing is published.
`.github/workflows/package.yml` runs the same suite and a wheel smoke test
when `main` is pushed to the `github` remote.
