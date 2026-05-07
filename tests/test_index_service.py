from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from app.core.config import Settings
    from app.services.index_service import build_book_index
    from app.services.index_service import get_index_status
except Exception:
    Settings = None
    build_book_index = None
    get_index_status = None


class TestIndexService(unittest.TestCase):
    @unittest.skipIf(Settings is None or build_book_index is None or get_index_status is None, "dependencies are not installed")
    def test_status_default_uploaded(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            s = Settings(index_status_dir=Path(d))
            st = get_index_status(s, "book")
            self.assertEqual(st.status, "uploaded")

    @unittest.skipIf(Settings is None or build_book_index is None or get_index_status is None, "dependencies are not installed")
    def test_build_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            s = Settings(index_status_dir=Path(d), upload_dir=Path(d) / "uploads")
            st = build_book_index(s, book_id="missing")
            self.assertEqual(st.status, "not_found")

    @unittest.skipIf(Settings is None or build_book_index is None, "dependencies are not installed")
    def test_build_happy_path_with_mocks(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            uploads = base / "uploads"
            uploads.mkdir(parents=True, exist_ok=True)
            f = uploads / "book.txt"
            f.write_text("hello", encoding="utf-8")

            s = Settings(index_status_dir=base / "status", upload_dir=uploads)

            class E:
                file_type = "txt"
                text = "abcdef" * 300
                char_count = len(text)

            class C:
                def __init__(self, i: int) -> None:
                    self.index = i
                    self.text = f"t{i}" * 100

            class VS:
                def add_texts(self, *, texts, metadatas, ids):
                    self._n = len(texts)

            with patch("app.services.index_service.find_uploaded_file", return_value=f):
                with patch("app.services.index_service.extract_text", return_value=E()):
                    with patch("app.services.index_service.chunk_text", return_value=[C(0), C(1)]):
                        with patch("app.services.index_service.get_vector_store", return_value=VS()):
                            st = build_book_index(s, book_id="book")
                            self.assertEqual(st.status, "completed")
                            self.assertEqual(st.total_chunks, 2)


if __name__ == "__main__":
    unittest.main()

