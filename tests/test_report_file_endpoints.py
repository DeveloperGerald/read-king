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


class TestReportFileEndpoints(unittest.TestCase):
    @unittest.skipIf(TestClient is None or app is None, "fastapi is not installed")
    def test_report_file_endpoint(self) -> None:
        client = TestClient(app)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.md"
            p.write_text("# report", encoding="utf-8")
            with patch("app.api.endpoints.get_report_status") as mock_status:
                mock_status.return_value = type(
                    "S", (), {"book_id": "b1", "status": "completed", "updated_at": "x", "error": None, "report_path": str(p), "outline_path": None}
                )()
                r = client.get("/api/books/b1/report/file")
                self.assertEqual(r.status_code, 200)
                self.assertIn("# report", r.text)


if __name__ == "__main__":
    unittest.main()

