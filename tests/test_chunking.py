from __future__ import annotations

import unittest

try:
    import langchain_text_splitters  # noqa: F401
except Exception:
    langchain_text_splitters = None

from app.rag.chunking import chunk_text


class TestChunking(unittest.TestCase):
    @unittest.skipIf(langchain_text_splitters is None, "langchain_text_splitters is not installed")
    def test_empty(self) -> None:
        self.assertEqual(chunk_text("   "), [])

    @unittest.skipIf(langchain_text_splitters is None, "langchain_text_splitters is not installed")
    def test_heading_split_and_overlap(self) -> None:
        text = "\n".join(
            [
                "前言",
                "这是一段前言。" * 30,
                "",
                "第一章 为什么选择金字塔结构",
                "这是第一章内容。" * 120,
                "",
                "第二章 思考的逻辑",
                "这是第二章内容。" * 120,
            ]
        )
        chunks = chunk_text(text, max_chars=500, overlap_chars=50)
        self.assertGreaterEqual(len(chunks), 3)
        overlap_hits = 0
        for i in range(1, len(chunks)):
            tail = chunks[i - 1].text[-50:]
            head_window = chunks[i].text[:200]
            if tail and tail in head_window:
                overlap_hits += 1
        self.assertGreaterEqual(overlap_hits, 1)

    @unittest.skipIf(langchain_text_splitters is None, "langchain_text_splitters is not installed")
    def test_long_paragraph_split(self) -> None:
        text = "A" * 2500
        chunks = chunk_text(text, max_chars=600, overlap_chars=100)
        self.assertGreaterEqual(len(chunks), 4)
        self.assertTrue(all(len(c.text) <= 600 for c in chunks))


if __name__ == "__main__":
    unittest.main()
