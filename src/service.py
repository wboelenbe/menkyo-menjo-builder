"""What the desktop window and the web app share: form values in, files out.

Both front ends collect the same few fields.  This turns them into
build_diploma's command-line flags and runs it, so neither front end can
produce something the command line could not.
"""

import contextlib
import datetime
import io
import subprocess

import build_diploma

# Output kinds: label shown to the user -> the --variants value.
OUTPUTS = {
    "For pre-printed certificate paper (text only)": "overlay",
    "Complete certificate with border": "full-cream",
    "Both": "overlay,full-cream",
}

GRADES = ["", "初段", "二段", "三段", "四段", "五段",
          "六段", "七段", "八段", "九段", "十段"]

MAX_NAME = 40


class FormError(ValueError):
    """A problem with what the user typed; the message is meant for them."""


def make_argv(cfg, *, award, name="", grade="", date="", output, folder,
              press=False):
    """Form values -> build_diploma flags.

    `date` is ISO text or ''.  `output` is a value from OUTPUTS.
    Every slot is passed explicitly, '' included, so a [sample] left in the
    configuration can never reach a real certificate; and flags use the
    --flag=value form so a value that starts with '-' is never read as a flag.
    """
    try:
        aw = cfg.award(award)
    except KeyError:
        raise FormError("Unknown certificate type.")
    name, grade = name.strip(), grade.strip()
    if len(name) > MAX_NAME:
        raise FormError(f"The name is too long (at most {MAX_NAME} characters).")
    if grade and not aw.grade_column:
        grade = ""
    if grade and grade not in GRADES:
        raise FormError("Unknown grade.")
    if date:
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            raise FormError("That date does not exist. Please check the "
                            "year, month and day.")
    if output not in OUTPUTS.values():
        raise FormError("Unknown output kind.")
    if not folder:
        raise FormError("Please choose a folder to save the certificates in.")
    argv = [f"--config={cfg.source}", f"--awards={aw.slug}",
            f"--variants={output}", "--formats=pdf",
            f"--name={name}", f"--rank={grade}", f"--date={date}",
            f"--out={folder}"]
    if press:
        argv.append("--press")
    return argv


def run_build(argv):
    """Run the generator in-process; return (ok, files_written, message).

    build_diploma keeps its state in module globals and prints its results,
    so callers must not run two builds at once.
    """
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            build_diploma.main(argv)
    except SystemExit as e:
        # main() uses SystemExit("message") for user-facing errors.
        if e.code not in (None, 0):
            return False, [], str(e.code)
    except subprocess.CalledProcessError as e:
        detail = (e.stderr.decode("utf-8", "replace")
                  if isinstance(e.stderr, bytes) else (e.stderr or "")).strip()
        return False, [], f"{e.cmd[0]} failed.\n\n{detail[-800:]}"
    except Exception as e:  # keep the caller alive whatever happens
        return False, [], f"{type(e).__name__}: {e}"
    files = [ln[6:] for ln in out.getvalue().splitlines() if ln.startswith("wrote ")]
    return True, files, ""
