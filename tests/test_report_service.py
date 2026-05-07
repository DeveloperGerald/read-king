from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from app.core.config import Settings
    from app.services.report_service import generate_report
    from app.services.report_service import get_report_status
except Exception:
    Settings = None
    generate_report = None
    get_report_status = None


class TestReportService(unittest.TestCase):
    @unittest.skipIf(Settings is None or get_report_status is None, "dependencies are not installed")
    def test_status_default_none(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            s = Settings(report_status_dir=base / "status", report_dir=base / "reports")
            st = get_report_status(s, "book")
            self.assertEqual(st.status, "none")

    @unittest.skipIf(Settings is None or get_report_status is None, "dependencies are not installed")
    def test_status_reconcile_from_files(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            s = Settings(report_status_dir=base / "status", report_dir=base / "reports")
            (base / "reports").mkdir(parents=True, exist_ok=True)
            (base / "reports" / "book.md").write_text("# ok", encoding="utf-8")

            st = get_report_status(s, "book")
            self.assertEqual(st.status, "completed")
            self.assertIsNotNone(st.report_path)

    @unittest.skipIf(Settings is None or generate_report is None, "dependencies are not installed")
    def test_generate_report_happy_path_with_mock(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            s = Settings(report_status_dir=base / "status", report_dir=base / "reports")

            with patch("app.services.report_service.run_report_workflow") as mock_run:
                mock_run.return_value = {"status": "completed", "report_markdown": "# ok", "outline_markdown": "## outline"}
                st = generate_report(s, book_id="book")
                self.assertEqual(st.status, "completed")
                self.assertTrue((base / "reports" / "book.md").exists())
                self.assertTrue((base / "reports" / "book.outline.md").exists())

    @unittest.skipIf(Settings is None or generate_report is None or get_report_status is None, "dependencies are not installed")
    def test_regenerate_clears_old_files(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            s = Settings(report_status_dir=base / "status", report_dir=base / "reports")
            (base / "reports").mkdir(parents=True, exist_ok=True)
            (base / "status").mkdir(parents=True, exist_ok=True)
            (base / "reports" / "book.md").write_text("old", encoding="utf-8")
            (base / "reports" / "book.outline.md").write_text("old outline", encoding="utf-8")
            (base / "status" / "book.json").write_text(
                '{"book_id":"book","status":"completed","updated_at":"x","error":null,"report_path":null,"outline_path":null}',
                encoding="utf-8",
            )

            with patch("app.services.report_service.run_report_workflow") as mock_run:
                mock_run.return_value = {"status": "completed", "report_markdown": "# new", "outline_markdown": "## new outline"}
                st = generate_report(s, book_id="book", force=True)
                self.assertEqual(st.status, "completed")
                self.assertEqual((base / "reports" / "book.md").read_text("utf-8"), "# new")
                self.assertEqual((base / "reports" / "book.outline.md").read_text("utf-8"), "## new outline")

    @unittest.skipIf(Settings is None or generate_report is None, "dependencies are not installed")
    def test_generate_report_fallback_to_outline(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            s = Settings(report_status_dir=base / "status", report_dir=base / "reports")

            with patch("app.services.report_service.run_report_workflow") as mock_run:
                mock_run.return_value = {"status": "completed", "outline_markdown": "# outline"}
                st = generate_report(s, book_id="book")
                self.assertEqual(st.status, "failed")
                self.assertTrue((base / "reports" / "book.outline.md").exists())

    @unittest.skipIf(Settings is None or generate_report is None, "dependencies are not installed")
    def test_generate_report_retries_expand_when_empty(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            s = Settings(report_status_dir=base / "status", report_dir=base / "reports")

            with patch("app.services.report_service.run_report_workflow") as mock_run:
                mock_run.return_value = {
                    "status": "completed",
                    "outline_markdown": "## outline",
                    "report_markdown": "",
                    "prompt": "PROMPT",
                }
                with patch("app.services.report_service.expand_report_from_prompt") as mock_expand:
                    mock_expand.return_value = "# ok"
                    st = generate_report(s, book_id="book")
                    self.assertEqual(st.status, "completed")
                    self.assertTrue((base / "reports" / "book.md").exists())

    @unittest.skipIf(Settings is None or get_report_status is None, "dependencies are not installed")
    def test_reconcile_failed_empty_report_uses_outline(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            s = Settings(report_status_dir=base / "status", report_dir=base / "reports")
            (base / "status").mkdir(parents=True, exist_ok=True)
            (base / "reports").mkdir(parents=True, exist_ok=True)
            (base / "reports" / "book.outline.md").write_text("# outline", encoding="utf-8")
            (base / "status" / "book.json").write_text(
                '{"book_id":"book","status":"failed","updated_at":"x","error":"empty report_markdown","report_path":null,"outline_path":null}',
                encoding="utf-8",
            )

            st = get_report_status(s, "book")
            self.assertEqual(st.status, "failed")
            self.assertIsNone(st.report_path)


if __name__ == "__main__":
    unittest.main()
