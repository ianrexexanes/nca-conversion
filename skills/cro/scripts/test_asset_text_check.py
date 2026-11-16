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
