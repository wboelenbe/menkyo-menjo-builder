"""Q-1: size of each crest-font option, raw and deflated as in a wheel.

    python fontsizes.py FONTDIR

Also writes FONTDIR/NotoSerifJP-SemiBold-jis0208.otf, a subset to JIS X 0208
(level 1 and 2 kanji, kana, symbols) plus the JIS X 0213 kanji, to show what a
subset would save, and reports its coverage of Yuji Boku's own cmap.
"""
import io, os, sys, zipfile
from fontTools import subset
from fontTools.ttLib import TTFont

d = sys.argv[1]
jis = set()
for hi in range(0xA1, 0xFF):
    for lo in range(0xA1, 0xFF):
        for codec in ("euc_jp", "euc_jis_2004"):
            try:
                jis.add(ord(bytes([hi, lo]).decode(codec)))
            except Exception:
                pass
src = os.path.join(d, "NotoSerifJP-SemiBold.otf")
sub = os.path.join(d, "NotoSerifJP-SemiBold-jis0208.otf")
if not os.path.exists(sub):
    f = TTFont(src)
    opts = subset.Options(); opts.layout_features = ["*"]; opts.name_IDs = ["*"]; opts.notdef_outline = True
    s = subset.Subsetter(opts); s.populate(unicodes=sorted(jis & set(f.getBestCmap()))); s.subset(f)
    f.save(sub)
yb = set(TTFont(os.path.join(os.environ["MENKYO_SRC"], "menkyo", "fonts", "YujiBoku-Regular.ttf")).getBestCmap())
for name in ("NotoSerifJP-SemiBold.otf", "NotoSerifCJKjp-SemiBold.otf", "NotoSerifJP-wght600.ttf",
             "NotoSerifJP-SemiBold-jis0208.otf"):
    p = os.path.join(d, name)
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(p, name)
    cm = set(TTFont(p, lazy=True).getBestCmap())
    print(f"{name:36s} raw {os.path.getsize(p)/1e6:6.2f} MB  in wheel {len(b.getvalue())/1e6:6.2f} MB  "
          f"cmap {len(cm):6d}  covers Yuji Boku's cmap: {len(yb & cm)}/{len(yb)}  has U+20BB7: {0x20BB7 in cm}")
