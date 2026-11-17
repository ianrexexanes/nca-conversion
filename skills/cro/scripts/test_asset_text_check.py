import re
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "asset_text_check.py"
SUMMARY_0 = "asset_text_check: 0 FAIL, 0 WARN"


def run(*args):
    done = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def png(texts=(), itxt=None, extra=()):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    for key, value in texts:
        out += chunk(b"tEXt", key.encode("latin-1") + b"\x00" + value.encode("latin-1"))
    if itxt:
        out += chunk(b"iTXt", b"Description\x00\x01\x00\x00\x00" + zlib.compress(itxt.encode("utf-8")))
    for kind, data in extra:
        out += chunk(kind, data)
    return out + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff")) + chunk(b"IEND", b"")


def xmp(text):
    return ('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            '<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:description>%s</dc:description>'
            "</rdf:Description></rdf:RDF></x:xmpmeta>" % text).encode("utf-8")


def jpeg(com=None, app1=None):
    out = b"\xff\xd8"
    if com is not None:
        data = com.encode("utf-8")
        out += b"\xff\xfe" + struct.pack(">H", len(data) + 2) + data
    if app1 is not None:
        data = b"http://ns.adobe.com/xap/1.0/\x00" + xmp(app1)
        out += b"\xff\xe1" + struct.pack(">H", len(data) + 2) + data
    return out + b"\xff\xd9"


def webp(xmp_text=None, exif_text=None):
    def chunk(fourcc, data):
        return fourcc + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) % 2 else b"")
    body = b"WEBP" + chunk(b"VP8X", bytes([0, 0, 0, 0]) + b"\x00" * 6)
    if exif_text:
        text = exif_text.encode("ascii") + b"\x00"
        body += chunk(b"EXIF", b"II*\x00" + struct.pack("<IH", 8, 1) + struct.pack("<HHII", 0x010E, 2, len(text), 26) + struct.pack("<I", 0) + text)
    if xmp_text:
        body += chunk(b"XMP ", xmp(xmp_text))
    return b"RIFF" + struct.pack("<I", len(body)) + body


def exif(ifd0=(), sub=(), thumb=b"", big=False):
    """A TIFF block as an EXIF APP1 holds it. Entries are (tag, type, payload); a payload over four bytes goes in a data area.
    IFD0 points at the Exif sub-directory and, with a thumbnail, at a second directory whose thumbnail bytes come last."""
    e = ">" if big else "<"

    def layout(entries, start, extra, next_ifd):
        entries = list(entries) + list(extra)
        data_at = start + 2 + 12 * len(entries) + 4
        table, data = b"", b""
        for tag, kind, payload in entries:
            count = len(payload) // {3: 2, 4: 4}.get(kind, 1)
            if len(payload) <= 4:
                value = payload.ljust(4, b"\x00")
            else:
                value = struct.pack(e + "I", data_at + len(data))
                data += payload + (b"\x00" if len(payload) % 2 else b"")
            table += struct.pack(e + "HHI", tag, kind, count) + value
        return struct.pack(e + "H", len(entries)) + table + struct.pack(e + "I", next_ifd) + data

    sub_at = 8 + len(layout(ifd0, 8, [(0x8769, 4, b"\x00" * 4)], 0))
    thumb_ifd = 0
    if thumb:
        thumb_ifd = sub_at + len(layout(sub, sub_at, [], 0))
    block0 = layout(ifd0, 8, [(0x8769, 4, struct.pack(e + "I", sub_at))], thumb_ifd)
    block1 = layout(sub, sub_at, [], 0)
    out = (b"MM\x00*" if big else b"II*\x00") + struct.pack(e + "I", 8) + block0 + block1
    if thumb:
        out += layout([], len(out), [(0x0201, 4, struct.pack(e + "I", len(out) + 2 + 12 + 4))], 0) + thumb
    return out


def tiff(entries, data=b"", count=None, big=False):
    """A TIFF block with one directory: entries are (tag, type, items, value), the value four bytes or an absolute offset.
    The data area starts at tiff_base(len(entries))."""
    e = ">" if big else "<"
    table = b""
    for tag, kind, items, value in entries:
        table += struct.pack(e + "HHI", tag, kind, items) + (value if isinstance(value, bytes) else struct.pack(e + "I", value))
    head = (b"MM\x00*" if big else b"II*\x00") + struct.pack(e + "I", 8)
    return head + struct.pack(e + "H", len(entries) if count is None else count) + table + struct.pack(e + "I", 0) + data


def tiff_base(n):
    return 10 + 12 * n + 4


def exif_texts(block):
    sys.path.insert(0, str(HERE))
    try:
        import asset_text_check
        return asset_text_check.exif_text(block)
    finally:
        sys.path.remove(str(HERE))


def ascii_entry(tag, text):
    return (tag, 2, text.encode("utf-8") + b"\x00")


def jpeg_exif(block):
    data = b"Exif\x00\x00" + block
    return b"\xff\xd8\xff\xe1" + struct.pack(">H", len(data) + 2) + data + b"\xff\xd9"


def webp_exif(block):
    def chunk(fourcc, data):
        return fourcc + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) % 2 else b"")
    body = b"WEBP" + chunk(b"VP8X", bytes([0, 0, 0, 0]) + b"\x00" * 6) + chunk(b"EXIF", block)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def gif(comment=None):
    out = b"GIF89a" + struct.pack("<HHBBB", 1, 1, 0, 0, 0)
    if comment is not None:
        data = comment.encode("ascii")
        out += b"\x21\xfe" + bytes([len(data)]) + data + b"\x00"
    return out + b"\x2c" + struct.pack("<HHHHB", 0, 0, 1, 1, 0) + b"\x02\x02\x44\x01\x00" + b"\x3b"


class AssetTextCheckTests(unittest.TestCase):
    def folder(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "img"
        for name, data in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_bytes(data)
        return tmp.name, root

    def test_metadata_text_found_per_format(self):
        words = "TODO swap this picture"
        marked = {"a.png": png([("Comment", words)]), "b.jpg": jpeg(com=words), "c.jpg": jpeg(app1=words), "d.webp": webp(xmp_text=words),
                  "e.webp": webp(exif_text=words), "f.gif": gif(words), "g.png": png(itxt=words)}
        tmp, root = self.folder(marked)
        code, out = run("--dir", str(root))
        self.assertEqual(code, 1, out)
        for name in marked:
            self.assertRegex(out, r"(?m)^FAIL %s ASSET_TEXT: " % re.escape(name), name)
        self.assertTrue(out.rstrip().endswith("asset_text_check: %d FAIL, 0 WARN" % len(marked)), out)

    def test_ztxt_text_is_found(self):
        ztxt = b"Comment\x00\x00" + zlib.compress(b"TODO swap this picture")
        tmp, root = self.folder({"z.png": png(extra=[(b"zTXt", ztxt)])})
        code, out = run("--dir", str(root))
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^FAIL z\.png ASSET_TEXT: ")

    def test_a_malformed_itxt_chunk_does_not_crash(self):
        bad = {"short.png": png(extra=[(b"iTXt", b"Description\x00")]), "cut.png": png(extra=[(b"iTXt", b"Description\x00\x01\x00")])}
        tmp, root = self.folder(bad)
        code, out = run("--dir", str(root))
        self.assertNotIn("Traceback", out)
        self.assertEqual(code, 0, out)
        self.assertTrue(out.rstrip().endswith(SUMMARY_0), out)

    def test_clean_images_pass_and_pixel_bytes_never_match(self):
        files = {"a.png": png([("Software", "Example editor")]), "b.jpg": jpeg(), "d.webp": webp(), "f.gif": gif(),
                 "sub/h.png": png()}
        # a pixel stream that happens to spell a placeholder word is not metadata
        files["i.png"] = png()[:-12] + b"xTBDx" + png()[-12:]
        tmp, root = self.folder(files)
        code, out = run("--dir", str(root))
        self.assertEqual(code, 0, out)
        self.assertTrue(out.rstrip().endswith(SUMMARY_0), out)

    def test_the_key_is_the_path_under_dir(self):
        tmp, root = self.folder({"sub/deep.png": png([("Comment", "lorem ipsum")])})
        code, out = run("--dir", str(root))
        self.assertRegex(out, r"(?m)^FAIL sub/deep\.png ASSET_TEXT: ")

    def test_forbid_file_words_fail(self):
        tmp, root = self.folder({"logo.png": png([("Comment", "Zorblat logo, final")])})
        forbid = Path(tmp) / "forbid.txt"
        forbid.write_text("# one per line\n\nzorblat\n", encoding="utf-8")
        code, out = run("--dir", str(root), "--forbid", str(forbid))
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^FAIL logo\.png FORBIDDEN: ")
        code, out = run("--dir", str(root))
        self.assertEqual(code, 0, out)  # without the list the same file is clean

    def forbidden(self, files, words):
        tmp, root = self.folder(files)
        forbid = Path(tmp) / "forbid.txt"
        forbid.write_text("\n".join(words) + "\n", encoding="utf-8")
        return run("--dir", str(root), "--forbid", str(forbid))

    def test_xmp_and_other_utf8_text_is_read_as_utf8(self):
        words = "Die günstigste Lösung"
        gif_utf8 = gif()[:13] + b"\x21\xfe" + bytes([len(words.encode())]) + words.encode() + b"\x00" + gif()[13:]
        itxt = b"Description\x00\x00\x00de\x00" + "Lösung".encode() + b"\x00" + b"plain"
        marked = {"a.jpg": jpeg(app1=words), "b.webp": webp(xmp_text=words), "c.jpg": jpeg(com=words), "d.gif": gif_utf8,
                  "e.png": png(extra=[(b"iTXt", itxt)])}
        code, out = self.forbidden(marked, ["günstigste", "lösung"])
        self.assertEqual(code, 1, out)
        for name in ("a.jpg", "b.webp", "c.jpg", "d.gif"):
            self.assertRegex(out, r"(?m)^FAIL %s FORBIDDEN: .*günstigste" % re.escape(name), name)
        for name in ("a.jpg", "b.webp", "c.jpg", "d.gif", "e.png"):
            self.assertRegex(out, r"(?m)^FAIL %s FORBIDDEN: .*lösung" % re.escape(name), name)

    def test_text_that_is_not_utf8_is_still_read_as_latin1(self):
        raw = "Zürich Lösung".encode("latin-1")  # valid Latin-1, not valid UTF-8
        with self.assertRaises(UnicodeDecodeError):
            raw.decode("utf-8")
        data = b"\xff\xd8\xff\xfe" + struct.pack(">H", len(raw) + 2) + raw + b"\xff\xd9"
        code, out = self.forbidden({"a.jpg": data}, ["zürich", "lösung"])
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^FAIL a\.jpg FORBIDDEN: .*zürich")
        self.assertRegex(out, r"(?m)^FAIL a\.jpg FORBIDDEN: .*lösung")

    def test_exif_thumbnail_bytes_are_never_read(self):
        block = exif([ascii_entry(0x010E, "a pump hall")], thumb=b"\xff\xd8\xff\xe0 AI \x00KI ")
        code, out = self.forbidden({"a.jpg": jpeg_exif(block), "b.webp": webp_exif(block)}, ["AI", "KI"])
        self.assertEqual(code, 0, out)
        self.assertNotIn("FORBIDDEN", out)

    def test_exif_image_description_is_reported(self):
        block = exif([ascii_entry(0x010E, "lorem ipsum TODO")], thumb=b"\xff\xd8\xff\xe0")
        tmp, root = self.folder({"a.jpg": jpeg_exif(block), "b.webp": webp_exif(block)})
        code, out = run("--dir", str(root))
        self.assertEqual(code, 1, out)
        for name in ("a.jpg", "b.webp"):
            self.assertRegex(out, r"(?m)^FAIL %s ASSET_TEXT: " % re.escape(name), name)

    def test_exif_windows_xp_tag_is_read_as_utf16(self):
        xp = ("lorem ipsum TODO".encode("utf-16-le") + b"\x00\x00")
        block = exif([(0x9C9C, 1, xp)])
        tmp, root = self.folder({"a.jpg": jpeg_exif(block), "b.webp": webp_exif(block)})
        code, out = run("--dir", str(root))
        self.assertEqual(code, 1, out)
        for name in ("a.jpg", "b.webp"):
            self.assertRegex(out, r"(?m)^FAIL %s ASSET_TEXT: " % re.escape(name), name)

    def test_exif_user_comment_is_read_by_its_character_code(self):
        for big in (False, True):
            unicode_comment = b"UNICODE\x00" + "lorem ipsum TODO".encode("utf-16-be" if big else "utf-16-le")
            ascii_comment = b"ASCII\x00\x00\x00" + b"lorem ipsum TODO"
            tmp, root = self.folder({"a.jpg": jpeg_exif(exif(sub=[(0x9286, 7, unicode_comment)], big=big)),
                                     "b.jpg": jpeg_exif(exif(sub=[(0x9286, 7, ascii_comment)], big=big))})
            code, out = run("--dir", str(root))
            self.assertEqual(code, 1, (big, out))
            for name in ("a.jpg", "b.jpg"):
                self.assertRegex(out, r"(?m)^FAIL %s ASSET_TEXT: " % re.escape(name), (big, name))

    def test_exif_artist_in_utf8_is_found_by_a_forbid_word_with_an_umlaut(self):
        block = exif([ascii_entry(0x013B, "Käse Werbung")], thumb=b"\xff\xd8\xff\xe0")
        code, out = self.forbidden({"a.jpg": jpeg_exif(block), "b.webp": webp_exif(block)}, ["käse"])
        self.assertEqual(code, 1, out)
        for name in ("a.jpg", "b.webp"):
            self.assertRegex(out, r"(?m)^FAIL %s FORBIDDEN: .*käse" % re.escape(name), name)

    def test_a_jpeg_comment_and_an_xmp_packet_are_still_found(self):
        code, out = self.forbidden({"a.jpg": jpeg(com="Zorblat hall"), "b.jpg": jpeg(app1="Zorblat hall")}, ["zorblat"])
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^FAIL a\.jpg FORBIDDEN: ")
        self.assertRegex(out, r"(?m)^FAIL b\.jpg FORBIDDEN: ")

    def test_an_exif_block_that_cannot_be_parsed_gives_no_row_and_no_traceback(self):
        import random
        noise = random.Random(7).randbytes(300)
        blocks = [noise, b"II*\x00" + struct.pack("<I", 9999), b"MM\x00*" + struct.pack(">I", 8) + b"\xff\xff" + noise[:20],
                  b"II*\x00" + struct.pack("<IH", 8, 1) + struct.pack("<HHII", 0x010E, 2, 4000000000, 26)]
        files = {}
        for i, block in enumerate(blocks):
            files["j%d.jpg" % i] = jpeg_exif(block)
            files["w%d.webp" % i] = webp_exif(block)
        code, out = self.forbidden(files, ["lorem"])
        self.assertNotIn("Traceback", out)
        self.assertEqual(code, 0, out)
        self.assertEqual(out.strip(), SUMMARY_0)

    def test_a_readable_description_survives_a_binary_entry_that_runs_past_the_block(self):
        base = tiff_base(2)
        block = tiff([(0x010E, 2, 6, base), (0x927C, 7, 1000, 99999)], b"lorem\x00")
        self.assertIn("lorem", " ".join(exif_texts(block)))

    def test_a_text_entry_that_runs_past_the_block_is_skipped_between_two_readable_ones(self):
        base = tiff_base(3)
        block = tiff([(0x010E, 2, 6, base), (0x010F, 2, 500, 99999), (0x0110, 2, 6, base + 6)], b"one11\x00two22\x00")
        text = " ".join(exif_texts(block))
        self.assertIn("one", text)
        self.assertIn("two", text)

    def test_a_directory_count_past_the_block_still_returns_the_entries_that_are_there(self):
        block = tiff([(0x010E, 2, 6, tiff_base(2)), (0x010F, 2, 6, tiff_base(2))], b"one11\x00", count=10)
        self.assertIn("one", " ".join(exif_texts(block)))

    def test_three_exif_pointers_to_one_directory_return_its_comment_once(self):
        base = tiff_base(3)
        sub = struct.pack("<H", 1) + struct.pack("<HHII", 0x9286, 7, 13, base + 18) + struct.pack("<I", 0)
        block = tiff([(0x8769, 4, 1, base)] * 3, sub + b"ASCII\x00\x00\x00MARK\x00")
        self.assertEqual(" ".join(exif_texts(block)).count("MARK"), 1)

    def test_many_entries_naming_one_large_field_are_capped_by_the_block_length(self):
        base = tiff_base(300)
        block = tiff([(0x010E, 2, 2000, base)] * 300, b"MARK" + b"x" * 1995 + b"\x00")
        self.assertLessEqual(" ".join(exif_texts(block)).count("MARK"), len(block) // 2000)

    def test_a_unicode_user_comment_is_found_in_either_byte_order(self):
        for big in (False, True):
            wrong = "utf-16-le" if big else "utf-16-be"
            block = exif(sub=[(0x9286, 7, b"UNICODE\x00" + "lorem TODO".encode(wrong))], big=big)
            self.assertIn("TODO", " ".join(exif_texts(block)), big)

    def test_a_placeholder_beside_a_bad_binary_entry_is_a_fail_row(self):
        base = tiff_base(2)
        block = tiff([(0x010E, 2, 17, base), (0x927C, 7, 1000, 99999)], b"lorem ipsum TODO\x00")
        tmp, root = self.folder({"a.jpg": jpeg_exif(block)})
        code, out = run("--dir", str(root))
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^FAIL a\.jpg ASSET_TEXT: ")

    def test_no_images_is_skipped_and_bad_input_exits_2(self):
        tmp, root = self.folder({"readme.txt": b"hello"})
        code, out = run("--dir", str(root))
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"(?m)^SKIPPED - ASSET_TEXT: no image files")
        self.assertEqual(run("--dir", str(Path(tmp) / "absent"))[0], 2)
        self.assertEqual(run()[0], 2)
        self.assertEqual(run("--dir", str(root), "--forbid", str(Path(tmp) / "absent.txt"))[0], 2)

    def test_an_unreadable_image_exits_2_without_a_traceback(self):
        tmp, root = self.folder({"a.png": png()})
        (root / "a.png").chmod(0)
        self.addCleanup((root / "a.png").chmod, 0o644)
        code, out = run("--dir", str(root))
        self.assertEqual(code, 2, out)
        self.assertNotIn("Traceback", out)
        self.assertTrue(out.startswith("asset_text_check: "), out)


if __name__ == "__main__":
    unittest.main()
