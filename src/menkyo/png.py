"""
Streaming PNG, for the rasters this package writes and reads back.

8 bits a channel, grey with alpha (LA) or RGBA, never interlaced, and every
row unfiltered (filter type 0): on text and line work that deflates about
as well as PNG's adaptive filters, and it lets a file be written as its rows
are drawn and read back a band at a time.  Nothing is held whole, which
matters at 600 dpi: an A3 text layer is 27 Mpx, and Pillow keeps LA and
RGBA alike at four bytes a pixel, 109 MB a copy.

A file this module cannot stream (another writer's filters or modes) is
read through Pillow instead, whole, as before.
"""

import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
_COLOUR = {"LA": 4, "RGBA": 6}
_MODE = {v: k for k, v in _COLOUR.items()}
_BPP = {"LA": 2, "RGBA": 4}

# Bytes of decompressed rows held at a time, and of compressed data
# gathered into one IDAT chunk.
BAND_BYTES = 2 ** 18


def _chunk(fh, kind, data):
    fh.write(struct.pack(">I", len(data)) + kind + data
             + struct.pack(">I", zlib.crc32(kind + data)))


def write(path, size, mode, bands, dpi=None):
    """Write a PNG as `bands` (lists of raw rows, bytes-like) arrive.

    `mode` is "LA" or "RGBA".  With `dpi`, a pHYs chunk gives it in whole
    pixels per metre, as every PNG writer does.  Returns `path`.
    """
    W, H = size
    z = zlib.compressobj(6)
    with open(path, "wb") as fh:
        fh.write(SIGNATURE)
        _chunk(fh, b"IHDR", struct.pack(">IIBBBBB", W, H, 8, _COLOUR[mode], 0, 0, 0))
        if dpi:
            ppm = round(dpi / 0.0254)
            _chunk(fh, b"pHYs", struct.pack(">IIB", ppm, ppm, 1))
        pending, held = [], 0
        for rows in bands:
            for r in rows:
                data = z.compress(b"\x00") + z.compress(r)
                if data:
                    pending.append(data)
                    held += len(data)
            if held >= BAND_BYTES:
                _chunk(fh, b"IDAT", b"".join(pending))
                pending, held = [], 0
        pending.append(z.flush())
        _chunk(fh, b"IDAT", b"".join(pending))
        _chunk(fh, b"IEND", b"")
    return path


class NotStreamable(Exception):
    """The file is not one this module reads: use Pillow."""


def _chunks(fh):
    if fh.read(8) != SIGNATURE:
        raise NotStreamable("not a PNG")
    while True:
        head = fh.read(8)
        if len(head) < 8:
            raise NotStreamable("truncated")
        n, kind = struct.unpack(">I4s", head)
        data = fh.read(n)
        crc = fh.read(4)
        if len(data) < n or struct.unpack(">I", crc)[0] != zlib.crc32(kind + data):
            raise NotStreamable(f"bad {kind!r} chunk")
        yield kind, data
        if kind == b"IEND":
            return


def header(path):
    """(width, height, mode) of a PNG this module can stream; or raises
    NotStreamable."""
    with open(path, "rb") as fh:
        for kind, data in _chunks(fh):
            if kind != b"IHDR":
                break
            w, h, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", data)
            if depth != 8 or colour not in _MODE or interlace:
                break
            return w, h, _MODE[colour]
    raise NotStreamable("not 8-bit LA or RGBA")


def bands(path):
    """The rows of a PNG this module can stream, a band at a time: lists of
    raw rows, each `width * channels` bytes.  Raises NotStreamable (before
    or during) for anything else, filtered rows included."""
    w, h, mode = header(path)
    rowlen = 1 + w * _BPP[mode]
    per = max(1, BAND_BYTES // rowlen)
    d = zlib.decompressobj()
    buf, out, seen = bytearray(), [], 0
    with open(path, "rb") as fh:
        for kind, data in _chunks(fh):
            if kind != b"IDAT":
                continue
            while data:
                buf += d.decompress(data, BAND_BYTES)
                data = d.unconsumed_tail
                at = 0
                while len(buf) - at >= rowlen:
                    if buf[at] != 0:
                        raise NotStreamable("filtered rows")
                    out.append(bytes(buf[at + 1:at + rowlen]))
                    at += rowlen
                    seen += 1
                    if len(out) == per:
                        yield out
                        out = []
                del buf[:at]
    if seen != h or buf:
        raise NotStreamable("the rows do not add up")
    if out:
        yield out


def alpha(path):
    """The alpha of the PNG at `path`, as an L image: read a band at a time
    when this module can stream the file, else through Pillow."""
    from PIL import Image
    try:
        w, h, mode = header(path)
        bpp = _BPP[mode]
        out, y = Image.new("L", (w, h)), 0
        for rows in bands(path):
            out.paste(Image.frombytes("L", (w, len(rows)),
                                      b"".join(r[bpp - 1::bpp] for r in rows)), (0, y))
            y += len(rows)
        return out
    except NotStreamable:
        with Image.open(path) as im:
            im.load()
            if im.mode not in ("RGBA", "LA"):
                im = im.convert("RGBA")
            return im.getchannel("A")
