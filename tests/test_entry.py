"""Gate checks for the news-image-20261117 entry.

Runs main.py twice into two temporary directories and asserts the two
entry.png files are byte-identical, then checks the PNG against the
competition gate: valid signature, IHDR dimensions within 1024x1024,
file size within 1 MiB, and IDAT data that zlib-decompresses.

Standard library only. Run with:  python3 tests/test_entry.py
"""

import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_BYTES = 1048576
MAX_DIM = 1024


def run_program(outdir):
    env = dict(os.environ)
    env["MAKEFUN_OUTPUT_DIR"] = outdir
    subprocess.run([sys.executable, os.path.join(REPO, "main.py")],
                   check=True, env=env, cwd=REPO,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with open(os.path.join(outdir, "entry.png"), "rb") as f:
        return f.read()


def parse_chunks(data):
    chunks = []
    pos = 8
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        typ = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length:
                                          pos + 12 + length])
        chunks.append((typ, payload, crc))
        pos += 12 + length
    return chunks


class EntryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d1, \
                tempfile.TemporaryDirectory() as d2:
            cls.first = run_program(d1)
            cls.second = run_program(d2)

    def test_runs_are_byte_identical(self):
        self.assertEqual(hashlib.sha256(self.first).hexdigest(),
                         hashlib.sha256(self.second).hexdigest())
        self.assertEqual(self.first, self.second)

    def test_png_signature(self):
        self.assertEqual(self.first[:8], b"\x89PNG\r\n\x1a\n")

    def test_dimensions_within_cap(self):
        chunks = parse_chunks(self.first)
        self.assertEqual(chunks[0][0], b"IHDR")
        width, height = struct.unpack(">II", chunks[0][1][:8])
        self.assertLessEqual(width, MAX_DIM)
        self.assertLessEqual(height, MAX_DIM)
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)

    def test_size_within_cap(self):
        self.assertLessEqual(len(self.first), MAX_BYTES)

    def test_chunk_crcs_and_idat_decompresses(self):
        idat = b""
        for typ, payload, crc in parse_chunks(self.first):
            self.assertEqual(zlib.crc32(typ + payload) & 0xFFFFFFFF, crc)
            if typ == b"IDAT":
                idat += payload
        raw = zlib.decompress(idat)
        width, height = struct.unpack(">II", self.first[16:24])
        self.assertEqual(len(raw), height * (1 + width * 3))


if __name__ == "__main__":
    unittest.main(verbosity=2)
