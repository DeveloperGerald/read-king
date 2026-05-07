from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from app.core.config import Settings
    from app.services.external_info_service import get_external_book_info
except Exception:
    Settings = None
    get_external_book_info = None


class TestExternalInfoService(unittest.TestCase):
    @unittest.skipIf(Settings is None or get_external_book_info is None, "dependencies are not installed")
    def test_cached(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            s = Settings(external_meta_dir=base)

            def fake_get(*args, **kwargs):
                raise AssertionError("should not call network")

            cache = base / "b1.json"
            cache.write_text(
                '{"title":"t","author":"a","description":null,"tavily_answer":null,"tavily_results":[],"sources":[],"fetched_at":"2999-01-01T00:00:00+00:00"}',
                encoding="utf-8",
            )

            with patch("httpx.get", fake_get):
                info = get_external_book_info(s, book_id="b1", title="t", author="a")
                self.assertEqual(info.title, "t")


if __name__ == "__main__":
    unittest.main()
