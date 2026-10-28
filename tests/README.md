# Tests

```sh
uv run pytest                       # everything; render tests skip without Inkscape
uv run pytest -m "not slow"         # without building and installing the wheel
scripts/test-docker.sh              # in the Docker test image, with real renders
scripts/test-docker.sh -k render    # arguments go to pytest
```

## Layout

| path | what |
|---|---|
| `regression/` | the behaviour as of `d96c08d`, the last commit before packaging |
| `acceptance/` | one test per acceptance criterion (`test_ac<N>_…`), see `docs/work/<slug>/acceptance.md` |
| `fakes/fake_tool.py` | stand-ins for `inkscape` and `gs`, so the CLI runs end to end without them |
| `data/` | test configurations: placeholder data only |
| `docker/` | the test image: Debian bookworm, Inkscape, Ghostscript, poppler, Noto CJK, uv |
| `conftest.py`, `support.py` | isolation, fixtures, helpers |

Markers:

- `render`: needs Inkscape, plus Ghostscript and poppler. These tests skip
  when Inkscape is missing. Under `REQUIRE_RENDER=1` (the Docker image and
  the release workflow) they **fail** instead, so a broken image cannot pass
  by skipping.
- `slow`: builds the wheel with `uv build` and installs it into a throwaway
  virtualenv.

## Personal data

A real `dojo.toml` may sit in the repository root and in the per-user
folder. No test may read either. `conftest.py` moves HOME and
XDG_CONFIG_HOME before `menkyo` is imported. For every test it also points
`menkyo.config.USER_CONFIG`, `LOCAL_CONFIG` and `save()`'s default into the
test's tmp directory, and it fails the test if anything still resolves to a
real file. Subprocesses get the same through `support.isolated_env()` and
always pass `-c`. Use `src/menkyo/example.toml` or a configuration the test
writes itself.

## Golden output

`regression/test_golden.py` runs every case in `regression/golden_cases.py`
and compares the result with `regression/golden/manifest.json`. Each case
runs the generator's `main()` through `golden_driver.py`, with the stand-in
`inkscape` and `gs` on PATH. The comparison covers:

- every SVG, byte for byte, and the text layer handed to Inkscape;
- every call to Inkscape and Ghostscript, with paths normalised;
- stdout, the set of files written, and the `--list` output.

`golden/svg/` stores each SVG for diffing on failure. The 800 kB drawn border
is replaced by a one-line hash there; the byte-for-byte comparison still
covers it.

The goldens were generated from `d96c08d`, which proves the move into a
package changed nothing. After an **intentional** change to the layout or
the output, regenerate them from the working tree, review the diff of
`golden/svg/` and explain it in the commit:

```sh
uv run python tests/regression/make_golden.py --current     # from the working tree
uv run python tests/regression/make_golden.py               # from d96c08d again
uv run python tests/regression/make_golden.py --ref v0.2.0  # from another commit
```

A `--ref` is extracted with `git archive` into a temporary directory; the
checkout is never switched. Every rendering case passes `--date`, because the
example's `[sample]` date is `today`.
