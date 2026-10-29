# Tests

```sh
uv run pytest                       # everything, real renders included
uv run pytest -m "not render"       # the quick run: no rendering
uv run pytest -m "not slow"         # without building and installing the wheel
scripts/test-docker.sh              # the same suite in the Docker test image (Linux)
scripts/test-docker.sh -k render    # arguments go to pytest
```

## Layout

| path | what |
|---|---|
| `regression/` | the behaviour as of `823af58`, the last commit before plain-white (overlay, overlay-flat, proof) |
| `acceptance/` | one test per acceptance criterion (`test_ac<N>_…`), see `docs/work/<slug>/acceptance.md` |
| `acceptance/render_without_inkscape/` | the reference for the renderer: Inkscape's output at `8509b85`, reduced to small fixtures in `reference/`, and the kit (`refkit.py`) that scores both sides with the same code; `measure.sh` measures a run's peak memory and time in Docker |
| `data/` | test configurations: placeholder data only |
| `docker/` | the test image: Python 3.13 on Debian bookworm, uv and the package's dependencies; no `apt-get` |
| `conftest.py`, `support.py` | isolation, fixtures, helpers |

The package draws with fontTools and pypdfium2 and needs no program, font or
library from the system. Every test renders for real, on the Mac as in the
Docker image, and nothing skips for want of a tool. The Docker image is the
Linux run: it has nothing installed besides Python, so a pass there also
shows that nothing on the host is used.

Markers:

- `render`: does a real render, seconds each. `-m "not render"` leaves them
  out for a quick run.
- `slow`: builds the wheel with `uv build` and installs it into a throwaway
  virtualenv.

`acceptance/render_without_inkscape/make_reference.sh` remakes `reference/`
from `8509b85` in `Dockerfile.ref`, the one image that still has Inkscape;
it needs Docker only, and is not part of the suite.

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
runs the generator's `main()` through `golden_driver.py`, with only
`/usr/bin:/bin` on PATH, and renders for real. The comparison covers:

- every SVG, byte for byte, except the four numbers of an inked SVG's
  text-layer `<image x=… y=… width=… height=…>`, which are the real outline
  box (render-without-inkscape's AC-21 checks them against Inkscape's);
- the text layers drawn (`document(…, layer="text")`, captured by the
  driver), as a set of sha256 values;
- stdout, the set of files written and the `--list` output.

The manifest still holds the Inkscape calls the baseline made, under
`tools`, as history; they are not compared, since there are none any more.
The flat and proof PDFs are compared by sha256 against
`regression/golden/pdf_sha256.json`. They depend on our PDF writer and on
fontTools' glyph outlines, so a fontTools bump may change them: look at the
PDFs, then regenerate the hashes with `make_golden.py --pdf-hashes`. The PNGs
and the inked overlay's PDF are not pinned here: how they look is what
`acceptance/test_ac_render_without_inkscape.py` compares.

`golden/svg/` stores each SVG for diffing on failure.

The goldens were first generated from `d96c08d`, which proved the move into
a package changed nothing. They are now generated from `823af58`, the last
commit with the coloured variants, which proves that removing those left
overlay, overlay-flat and proof byte for byte as they were. Every case
therefore names its variants explicitly; what `--all`, `-v all` and the
defaults mean is pinned in `acceptance/test_ac_plain_white.py`. After an
**intentional** change to the layout or the output, regenerate them from the
working tree, review the diff of `golden/svg/` and explain it in the commit:

```sh
uv run python tests/regression/make_golden.py --current     # from the working tree
uv run python tests/regression/make_golden.py               # from 823af58 again
uv run python tests/regression/make_golden.py --ref v0.3.0  # from another commit
uv run python tests/regression/make_golden.py --pdf-hashes  # the flat and proof PDF hashes only
```

A `--ref` is extracted with `git archive` into a temporary directory; the
checkout is never switched. Every case renders for real, so a `--ref` older
than render-without-inkscape (anything before 0.3.0, `823af58` included)
needs a real Inkscape on `/usr/bin:/bin`: run it in an image that has one.
A commit from render-without-inkscape onwards renders anywhere. Every rendering
case passes `--date`, because the example's `[sample]` date is `today`.
