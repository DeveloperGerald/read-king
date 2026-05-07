from __future__ import annotations

import unittest

try:
    import chromadb  # noqa: F401
except Exception:
    chromadb = None

try:
    import langchain_community  # noqa: F401
except Exception:
    langchain_community = None

try:
    from app.core.config import Settings
    from app.rag.vector_store import get_collection_name
except Exception:
    Settings = None
    get_collection_name = None


class TestVectorStore(unittest.TestCase):
    @unittest.skipIf(Settings is None or get_collection_name is None, "dependencies are not installed")
    def test_collection_name(self) -> None:
        s = Settings(chroma_collection_prefix="rk")
        self.assertEqual(get_collection_name(s, book_id="abc"), "rk_abc")

    @unittest.skipIf(Settings is None or get_collection_name is None, "dependencies are not installed")
    def test_collection_name_default_prefix(self) -> None:
        s = Settings(chroma_collection_prefix="")
        self.assertEqual(get_collection_name(s, book_id="abc"), "readking_abc")


if __name__ == "__main__":
    unittest.main()

