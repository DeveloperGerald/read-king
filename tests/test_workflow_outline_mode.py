from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    import langgraph  # noqa: F401
except Exception:
    langgraph = None

try:
    from app.core.config import Settings
    from app.agents.workflow import run_report_workflow
except Exception:
    Settings = None
    run_report_workflow = None


class TestWorkflowOutlineMode(unittest.TestCase):
    @unittest.skipIf(langgraph is None or Settings is None or run_report_workflow is None, "dependencies are not installed")
    def test_outline_mode_stops_after_outline(self) -> None:
        class DummyModel:
            def __init__(self) -> None:
                self.calls = 0

            def invoke(self, messages):
                self.calls += 1
                return type("R", (), {"content": '{"title":"大纲","sections":[{"heading":"章节","bullets":["要点"]}]}'})()

        dummy = DummyModel()
        with patch("app.agents.workflow.find_uploaded_file", return_value=__import__("pathlib").Path(__file__)):
            with patch("app.agents.workflow.extract_text") as mock_extract:
                mock_extract.return_value = type("E", (), {"text": "第一章 测试\n\n内容" * 200, "file_type": "txt"})()
                with patch("app.agents.workflow.get_book_meta") as mock_meta:
                    mock_meta.return_value = type("M", (), {"title": "t", "author": "a"})()
                    with patch("app.agents.workflow.get_external_book_info") as mock_info:
                        mock_info.return_value = type(
                            "X",
                            (),
                            {"title": "t", "author": "a", "description": "", "tavily_answer": None, "tavily_results": [], "sources": []},
                        )()
                        with patch("app.llm.chat_model.get_chat_model", return_value=dummy):
                            out = run_report_workflow(settings=Settings(), book_id="b1", mode="outline")
                            self.assertEqual(out.get("status"), "outlined")
                            self.assertIn("outline_markdown", out)
                            self.assertEqual(dummy.calls, 1)


if __name__ == "__main__":
    unittest.main()
