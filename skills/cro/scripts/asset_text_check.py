#!/usr/bin/env python3
"""Asset text check: the text images carry in their metadata. Python 3 stdlib only.

    asset_text_check.py --dir DIR [--forbid FILE]

Reads every image under DIR (.png .jpg .jpeg .webp .avif .gif .ico) and searches only the text it carries as metadata, never
its pixels: PNG tEXt, zTXt and iTXt chunks; JPEG COM and APP1 (EXIF, XMP) segments; WebP EXIF and XMP chunks; GIF comment
extensions; and any XMP packet in any image. A placeholder word there is ASSET_TEXT; a word or phrase from the --forbid file
(one per line, `#` lines ignored) is FORBIDDEN. Lines are `<FAIL|SKIPPED> <path under DIR> <RULE>: <detail>`, then
`asset_text_check: <f> FAIL, <w> WARN`. Exit 1 on any FAIL, 2 on bad input.
"""
import re
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_check import PLACEHOLDER, BadInput, Parser, finish, forbid_pattern, read_forbid  # noqa: E402

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".ico"}
XMP = re.compile(rb"<x:xmpmeta.*?</x:xmpmeta>", re.DOTALL)


def latin(data):
    return data.decode("latin-1")


def png_text(data):
    pos = 8
    while pos + 8 <= len(data):
        size, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + size]
        pos += 12 + size
        try:
            if kind == b"tEXt":
                yield latin(body.replace(b"\x00", b" "))
            elif kind == b"zTXt":
                key, rest = body.split(b"\x00", 1)
                yield latin(key) + " " + latin(zlib.decompress(rest[1:]))
            elif kind == b"iTXt":
                key, rest = body.split(b"\x00", 1)
                flag, rest = rest[0], rest[2:]
                _language, rest = rest.split(b"\x00", 1)
                translated, text = rest.split(b"\x00", 1)
                if flag:
                    text = zlib.decompress(text)
                yield " ".join([latin(key), latin(translated), text.decode("utf-8", "replace")])
        except (ValueError, zlib.error):
            continue
        if kind == b"IEND":
            break


def jpeg_text(data):
    pos = 2
    while pos + 4 <= len(data) and data[pos] == 0xFF:
        marker = data[pos + 1]
        if marker == 0xFF:
            pos += 1
            continue
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        if marker in (0xD9, 0xDA):
            break
        size = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        if marker in (0xFE, 0xE1):
            yield latin(data[pos + 4:pos + 2 + size].replace(b"\x00", b" "))
        pos += 2 + size


def webp_text(data):
    pos = 12
    while pos + 8 <= len(data):
        kind, size = struct.unpack("<4sI", data[pos:pos + 8])
        if kind in (b"EXIF", b"XMP "):
            yield latin(data[pos + 8:pos + 8 + size].replace(b"\x00", b" "))
        pos += 8 + size + (size & 1)


def gif_text(data):
    if len(data) < 13:
        return
    pos = 13
    if data[10] & 0x80:
        pos += 3 * (2 << (data[10] & 7))
    while pos < len(data):
        block = data[pos]
        if block == 0x21 and pos + 1 < len(data):
            label = data[pos + 1]
            pos += 2
            text = b""
            while pos < len(data) and data[pos]:
                text += data[pos + 1:pos + 1 + data[pos]]
                pos += 1 + data[pos]
            pos += 1
            if label == 0xFE:
                yield latin(text)
        elif block == 0x2C and pos + 10 <= len(data):
            pos += 10
            if data[pos - 1] & 0x80:
                pos += 3 * (2 << (data[pos - 1] & 7))
            pos += 1
            while pos < len(data) and data[pos]:
                pos += 1 + data[pos]
            pos += 1
        else:
            break


def carried_text(data):
    """The metadata text parts of one image file's bytes."""
    parts = []
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        parts += png_text(data)
    elif data[:2] == b"\xff\xd8":
        parts += jpeg_text(data)
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        parts += webp_text(data)
    elif data[:3] == b"GIF":
        parts += gif_text(data)
    parts += [latin(m) for m in XMP.findall(data)]
    return parts


def main(argv=None):
    parser = Parser(prog="asset_text_check", description="Search the text metadata inside image files.")
    parser.add_argument("--dir", required=True, metavar="DIR")
    parser.add_argument("--forbid", metavar="FILE")
    args = parser.parse_args(argv)
    try:
        root = Path(args.dir)
        if not root.is_dir():
            raise BadInput("%s is not a folder" % args.dir)
        pattern = forbid_pattern(read_forbid(args.forbid)) if args.forbid else None
    except BadInput as error:
        print("asset_text_check: %s" % error, file=sys.stderr)
        return 2
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS)
    rows = []
    for path in files:
        key = path.relative_to(root).as_posix()
        try:
            text = " ".join(carried_text(path.read_bytes()))
        except OSError as error:
            print("asset_text_check: cannot read %s: %s" % (path, error.strerror or error), file=sys.stderr)
            return 2
        for found in sorted({m.group(0) for m in PLACEHOLDER.finditer(text)}):
            rows.append(("FAIL", key, "ASSET_TEXT", "the image's metadata holds %r" % found))
        for found in sorted({m.group(0).lower() for m in pattern.finditer(text)}) if pattern else []:
            rows.append(("FAIL", key, "FORBIDDEN", "the image's metadata holds %r" % found))
    if not files:
        rows.append(("SKIPPED", "-", "ASSET_TEXT", "no image files under %s" % args.dir))
    return finish("asset_text_check", rows)


if __name__ == "__main__":
    sys.exit(main())
