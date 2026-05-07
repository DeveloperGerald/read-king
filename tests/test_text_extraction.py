from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    import langchain_core  # noqa: F401
except Exception:
    langchain_core = None

from app.services.text_extraction import extract_text


class TestTextExtraction(unittest.TestCase):
    @unittest.skipIf(langchain_core is None, "langchain_core is not installed")
    def test_extract_txt_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.txt"
            p.write_text("你好\n\n\n世界  ", encoding="utf-8")
            out = extract_text(p)
            self.assertEqual(out.file_type, "txt")
            self.assertEqual(out.text, "你好\n\n世界")
            self.assertGreater(out.char_count, 0)

    @unittest.skipIf(langchain_core is None, "langchain_core is not installed")
    def test_extract_txt_gb18030(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "b.txt"
            p.write_bytes("\u4f60\u597d".encode("gb18030"))
            out = extract_text(p)
            self.assertEqual(out.text, "你好")


if __name__ == "__main__":
    unittest.main()
