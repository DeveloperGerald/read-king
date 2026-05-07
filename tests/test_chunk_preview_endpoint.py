from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:
    TestClient = None

try:
    from app.main import app
except Exception:
    app = None


class TestChunkPreviewEndpoint(unittest.TestCase):
    @unittest.skipIf(TestClient is None or app is None, "fastapi is not installed")
    def test_chunks_preview_without_langchain(self) -> None:
        client = TestClient(app)

        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.txt"
            p.write_text("hello world", encoding="utf-8")

            with patch("app.api.endpoints.find_uploaded_file", return_value=p):
                with patch("app.api.endpoints.extract_text") as mock_extract:
                    mock_extract.return_value = type(
                        "E", (), {"file_type": "txt", "text": "abcdef" * 400, "char_count": 2400, "line_count": 1}
                    )()
                    with patch("app.api.endpoints.chunk_text") as mock_chunk:
                        mock_chunk.return_value = [
                            type("C", (), {"chunk_id": "1", "text": "aaa" * 100, "index": 0})(),
                            type("C", (), {"chunk_id": "2", "text": "bbb" * 100, "index": 1})(),
                        ]

                        r = client.get("/api/books/book123/chunks?limit=1")
                        self.assertEqual(r.status_code, 200)
                        body = r.json()
                        self.assertEqual(body["book_id"], "book123")
                        self.assertEqual(body["total_chunks"], 2)
                        self.assertEqual(len(body["items"]), 1)


if __name__ == "__main__":
    unittest.main()
