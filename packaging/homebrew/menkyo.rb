# Template for a Homebrew tap (github.com/<you>/homebrew-menkyo, Formula/menkyo.rb).
# Untested until it has a real release tarball: fill in url and sha256, then
#   brew install --build-from-source ./menkyo.rb && brew test menkyo
#
# Installs two commands:
#   menkyo       the command-line generator
#   menkyo-gui   the window
class Menkyo < Formula
  desc "Japanese dan-grade and menkyo certificate generator"
  homepage "https://github.com/OWNER/menkyo-menjo-builder"
  url "https://github.com/OWNER/menkyo-menjo-builder/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "FILL_IN"
  license "MIT"

  depends_on "ghostscript"
  depends_on "numpy"
  depends_on "pillow"
  depends_on "python-tk@3.13"
  depends_on "python@3.13"
  depends_on "scipy"
  depends_on cask: "inkscape"

  def install
    python = Formula["python@3.13"].opt_bin/"python3.13"

    # numpy, pillow and scipy come from their own formulae rather than being
    # rebuilt from PyPI; the venv just has to be able to see them.
    venv = libexec/"venv"
    system python, "-m", "venv", venv
    site = Language::Python.site_packages(python)
    (venv/site/"homebrew-deps.pth").write <<~EOS
      #{Formula["numpy"].opt_prefix/site}
      #{Formula["pillow"].opt_prefix/site}
      #{Formula["scipy"].opt_prefix/site}
      #{Formula["python-tk@3.13"].opt_prefix/site}
    EOS
    # The package itself goes into the venv like any wheel, metadata and all
    # (menkyo --version), with its console script; --no-deps, as the .pth
    # above already supplies them.  pip fetches the build backend (hatchling)
    # into an isolated build environment.
    system venv/"bin/python", "-m", "pip", "install", "--no-deps", buildpath
    libexec.install "src/gui.py", "LICENSE", "NOTICE"

    bin.install_symlink venv/"bin/menkyo"
    (bin/"menkyo-gui").write <<~SH
      #!/bin/bash
      exec "#{venv}/bin/python" "#{libexec}/gui.py" "$@"
    SH
  end

  test do
    assert_match "menkyo #{version}", shell_output("#{bin}/menkyo --version")
    assert_match "dan-overlay", shell_output("#{bin}/menkyo --list")
  end
end
