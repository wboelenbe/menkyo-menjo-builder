#!/bin/bash
# The crest-mincho candidates (Q-1), pinned by tag/commit and sha256.
#   fetch_fonts.sh DIR       (then SPIKE_FONTS=DIR for render_candidate.py)
# Each file lands in DIR; nothing is executed from it.
#   NotoSerifJP-SemiBold.otf      noto-cjk Serif2.003, SubsetOTF/JP (the default)
#   NotoSerifCJKjp-SemiBold.otf   noto-cjk Serif2.003, OTF/Japanese (whole CJK)
#   NotoSerifJP[wght].ttf         google/fonts, variable; instanced to
#   NotoSerifJP-wght600.ttf       by fontTools' instancer, below
set -eu
d="$1"; mkdir -p "$d"; cd "$d"
get() { [ -f "$1" ] || curl -sSL -o "$1" "$2"; echo "$3  $1" | shasum -a 256 -c - >/dev/null || { echo "sha256 mismatch: $1"; exit 1; }; }
N=https://github.com/notofonts/noto-cjk/raw/Serif2.003/Serif
G=https://github.com/google/fonts/raw/8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5/ofl/notoserifjp
get NotoSerifJP-SemiBold.otf   $N/SubsetOTF/JP/NotoSerifJP-SemiBold.otf     116d06c2b11ceba33ccb3f8c9eb1c86aba3d5761a1199fd37f74e83365e7a53d
get NotoSerifCJKjp-SemiBold.otf $N/OTF/Japanese/NotoSerifCJKjp-SemiBold.otf 14618550f2b4c1696b82c1a7bb7735102195bdbe00bad0b0f0aa8e6c8d8e020c
get LICENSE-noto-cjk.txt       $N/LICENSE                                    6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2
get 'NotoSerifJP[wght].ttf'    "$G/NotoSerifJP%5Bwght%5D.ttf"                2fd527ba12b6a44ec30d796d633360da0aeba6c5d4af1304ce12bb4dc15a7dfc
get OFL-notoserifjp.txt        $G/OFL.txt                                    5e0da210fb04058a8c0087985d2d456b931c2579811a49655721d3cf0c36b6d6
[ -f NotoSerifJP-wght600.ttf ] || python -m fontTools.varLib.instancer -q 'NotoSerifJP[wght].ttf' wght=600 -o NotoSerifJP-wght600.ttf
ls -l
