"""PDF and PNG properties for the no-inkscape spike: F-1, F-2, F-3, F-5, F-6
(the pikepdf half), N-1, N-2, R-1 and qpdf's check.

    python pdfcheck.py props TREE [TREE ...]          per case, as JSON lines
    python pdfcheck.py same A.pdf B.pdf               R-1: equal once normalised
    python pdfcheck.py samepng A.png B.png            R-1: byte-identical

R-1's normalisation: /CreationDate, /ModDate and /ID removed, XMP metadata
dropped, then the file re-saved by pikepdf with a fixed object order
(qdf off, deterministic_id, static_id) and the bytes compared.
"""
import hashlib, json, os, sys

import pikepdf
from PIL import Image


def walk_colours(content_ops, resources, seen, out, depth=0):
    """Colour operators and image colour spaces, through Form XObjects."""
    for operands, op in content_ops:
        op = str(op)
        if op in ("g", "G", "rg", "RG", "k", "K", "cs", "CS", "sc", "SC", "scn", "SCN"):
            key = op if op not in ("cs", "CS") else f"{op} {operands[0]}"
            out["ops"][key] = out["ops"].get(key, 0) + 1
            if op in ("g", "G") and any(float(v) not in (0.0,) for v in operands):
                out["grey_values"].add(round(float(operands[0]), 4))
        elif op == "Do":
            name = operands[0]
            xo = resources.get("/XObject", {}).get(name)
            if xo is None or xo.objgen in seen:
                continue
            seen.add(xo.objgen)
            st = xo.get("/Subtype")
            if st == "/Image":
                cs = str(xo.get("/ColorSpace"))
                sm = xo.get("/SMask")
                out["images"].append(dict(cs=cs, w=int(xo.Width), h=int(xo.Height),
                                          smask=str(sm.get("/ColorSpace")) if sm is not None else None))
            elif st == "/Form":
                if "/Group" in xo:
                    out["groups"].append(str(xo.Group.get("/CS")))
                walk_colours(pikepdf.parse_content_stream(xo), xo.get("/Resources", resources), seen, out, depth + 1)
        elif op == "gs":
            gs = resources.get("/ExtGState", {}).get(operands[0])
            if gs is not None and "/SMask" in gs and gs.SMask != pikepdf.Name.None_:
                out["softmask_gstate"] = True


def props(pdf_path):
    pdf = pikepdf.open(pdf_path)
    page = pdf.pages[0]
    mb = [float(v) for v in page.MediaBox]
    out = {"ops": {}, "grey_values": set(), "images": [], "groups": [], "softmask_gstate": False}
    if "/Group" in page.obj:
        out["groups"].append("page:" + str(page.obj.Group.get("/CS")))
    walk_colours(pikepdf.parse_content_stream(page), page.Resources, set(), out)
    fonts = []
    def fonts_in(res, seen):
        for n, f in res.get("/Font", {}).items():
            fonts.append(str(f.get("/BaseFont")) + " " + str(f.get("/Subtype")))
        for n, xo in res.get("/XObject", {}).items():
            if xo.get("/Subtype") == "/Form" and xo.objgen not in seen:
                seen.add(xo.objgen)
                fonts_in(xo.get("/Resources", {}), seen)
    fonts_in(page.Resources, set())
    problems = pdf.check_pdf_syntax()   # pikepdf 10: qpdf --check, formerly Pdf.check()
    return dict(
        pages=len(pdf.pages), mediabox=[round(v, 3) for v in mb], rotate=int(page.obj.get("/Rotate", 0)),
        images=out["images"], groups=out["groups"], softmask_gstate=out["softmask_gstate"],
        colour_ops=out["ops"], grey_values=sorted(out["grey_values"])[:6],
        fonts=fonts, qpdf_check=problems or "no problems", size=os.path.getsize(pdf_path),
        pdf_version=pdf.pdf_version)


def png_props(p):
    im = Image.open(p)
    a = im.getchannel("A") if im.mode == "RGBA" else None
    return dict(size=im.size, mode=im.mode, dpi=[round(v, 3) for v in im.info.get("dpi", (0, 0))],
                bytes=os.path.getsize(p), alpha_minmax=a.getextrema() if a else None)


def normalised(path):
    pdf = pikepdf.open(path)
    for k in ("/CreationDate", "/ModDate"):
        if k in pdf.trailer.get("/Info", {}):
            del pdf.trailer.Info[k]
    if "/Metadata" in pdf.Root:
        del pdf.Root.Metadata
    if "/ID" in pdf.trailer:
        del pdf.trailer.ID
    import io
    b = io.BytesIO()
    pdf.save(b, static_id=True, deterministic_id=False, compress_streams=True,
             object_stream_mode=pikepdf.ObjectStreamMode.preserve)
    return b.getvalue()


def main():
    cmd = sys.argv[1]
    if cmd == "props":
        for tree in sys.argv[2:]:
            for case in sorted(os.listdir(tree)):
                d = os.path.join(tree, case)
                if not os.path.isdir(d):
                    continue
                r = {"tree": os.path.basename(tree.rstrip("/")), "case": case}
                for f in sorted(os.listdir(d)):
                    if f.endswith(".pdf"):
                        r["pdf"] = props(os.path.join(d, f))
                    elif f.endswith(".png"):
                        r["png"] = png_props(os.path.join(d, f))
                print(json.dumps(r, ensure_ascii=False, default=str))
    elif cmd == "same":
        a, b = (normalised(p) for p in sys.argv[2:4])
        raw = open(sys.argv[2], "rb").read() == open(sys.argv[3], "rb").read()
        print(json.dumps(dict(raw_identical=raw, normalised_identical=a == b,
                              sha256=[hashlib.sha256(x).hexdigest()[:16] for x in (a, b)])))
    elif cmd == "samepng":
        a, b = (open(p, "rb").read() for p in sys.argv[2:4])
        print(json.dumps(dict(identical=a == b, sha256=[hashlib.sha256(x).hexdigest()[:16] for x in (a, b)])))


if __name__ == "__main__":
    main()
