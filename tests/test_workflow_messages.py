from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from langchain_core.messages import HumanMessage
    from langchain_core.messages import SystemMessage
except Exception:
    HumanMessage = None
    SystemMessage = None

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


class TestWorkflowMessages(unittest.TestCase):
    @unittest.skipIf(langgraph is None or HumanMessage is None or SystemMessage is None or Settings is None or run_report_workflow is None, "dependencies are not installed")
    def test_system_and_human_messages(self) -> None:
        class DummyModel:
            def __init__(self) -> None:
                self.seen = None

            def invoke(self, messages):
                self.seen = messages
                return type("R", (), {"content": "ok"})()

        dummy = DummyModel()

        with patch("app.agents.workflow.find_uploaded_file", return_value=__import__("pathlib").Path(__file__)):
            with patch("app.agents.workflow.extract_text") as mock_extract:
                mock_extract.return_value = type("E", (), {"text": "你好。" * 500, "file_type": "txt"})()
                with patch("app.llm.chat_model.get_chat_model", return_value=dummy):
                    out = run_report_workflow(settings=Settings(), book_id="b1", user_requirements="", user_feelings="")
                    self.assertEqual(out.get("status"), "completed")
                    self.assertIsNotNone(dummy.seen)
                    self.assertTrue(isinstance(dummy.seen[0], SystemMessage))
                    self.assertTrue(isinstance(dummy.seen[1], HumanMessage))

    @unittest.skipIf(Settings is None or run_report_workflow is None, "dependencies are not installed")
    def test_context_mode_does_not_require_llm(self) -> None:
        with patch("app.agents.workflow.find_uploaded_file", return_value=__import__("pathlib").Path(__file__)):
            with patch("app.agents.workflow.extract_text") as mock_extract:
                mock_extract.return_value = type("E", (), {"text": "目录\n\n第一章 测试\n\n内容" * 50, "file_type": "txt"})()
                with patch("app.agents.workflow.build_context", return_value="[目录]\n第一章"):
                    out = run_report_workflow(settings=Settings(), book_id="b1", mode="context")
                    self.assertEqual(out.get("status"), "context_ready")
                    self.assertTrue(out.get("context", "").startswith("[目录]"))


if __name__ == "__main__":
    unittest.main()
