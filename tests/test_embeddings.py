from __future__ import annotations

import unittest

try:
    import langchain_community  # noqa: F401
except ImportError:
    langchain_community = None

try:
    from app.core.config import Settings
    from app.rag.embeddings import get_embeddings
except Exception:
    Settings = None
    get_embeddings = None


class TestEmbeddings(unittest.TestCase):
    @unittest.skipIf(langchain_community is None or Settings is None or get_embeddings is None, "dependencies are not installed")
    def test_get_embeddings(self) -> None:
        settings = Settings(embedding_provider="ollama", embedding_model="nomic-embed-text")
        embedder = get_embeddings(settings)
        self.assertIsNotNone(embedder)
        self.assertTrue(hasattr(embedder, "embed_query"))


if __name__ == "__main__":
    unittest.main()
