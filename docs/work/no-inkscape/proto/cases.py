"""The spike's cases (acceptance.md, "Cases"): argv after -c example.toml.

C-2, C-6 and C-7 are removed by the contract. C-9 is C-4 with 𠮷 (U+20BB7),
which Yuji Boku lacks (it covers every JIS X 0208 kanji; see spike.md G-4).
C-4b is added by the spike (see below).
"""

CASES = {
    "C-1": ["-a", "dan", "-v", "overlay", "-n", "ヤン・ヤンセン", "-r", "2",
            "-d", "2024-07-01", "-f", "pdf,png"],
    "C-3": ["-a", "shihan", "-v", "overlay", "-n", "ジョン・ドウ", "-r", "",
            "-d", "2024-07-01", "-f", "pdf,png"],
    "C-4": ["-a", "dan", "-v", "overlay-flat", "-n",
            "アレクサンドル・ファン・デル・フェルデン", "-r", "10",
            "-d", "2020-10-20", "-f", "pdf,png"],
    # Added by the spike: C-4's name has no ー, so G-2's rotated long vowel
    # mark would go untested. Same flags as C-4, a name with ー in it.
    "C-4b": ["-a", "dan", "-v", "overlay-flat", "-n",
             "ピーター・ファン・デル・フェルデン", "-r", "10",
             "-d", "2020-10-20", "-f", "pdf,png"],
    "C-5": ["-a", "dan", "-v", "proof", "-n", "", "-r", "", "-d", "",
            "-f", "pdf,png"],
    "C-8": ["-a", "dan", "-v", "overlay", "-n", "ヤン・ヤンセン", "-r", "2",
            "-d", "2024-07-01", "-f", "png", "--dpi", "150"],
    "C-9": ["-a", "dan", "-v", "overlay-flat", "-n",
            "𠮷田・ファン・デル・フェルデン", "-r", "10",
            "-d", "2020-10-20", "-f", "pdf,png"],
}
# V-3: the text layer at --supersample 4 (pixmap size and peak memory).
CASES["C-1-ss4"] = CASES["C-1"] + ["--supersample", "4"]

# The three stand-in names, for the G-4 coverage listing.
NAMES = ["ヤン・ヤンセン", "ジョン・ドウ", "アレクサンドル・ファン・デル・フェルデン"]
