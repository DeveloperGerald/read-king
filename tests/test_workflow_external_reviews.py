from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from app.core.config import Settings
    from app.agents.workflow import build_report_graph
except Exception:
    Settings = None
    build_report_graph = None


class TestWorkflowExternalReviews(unittest.TestCase):
    @unittest.skipIf(Settings is None or build_report_graph is None, "dependencies are not installed")
    def test_external_reviews_injected(self) -> None:
        settings = Settings()
        app = build_report_graph(settings=settings)

        class DummyModel:
            def invoke(self, messages):
                return type("R", (), {"content": "ok"})()

        with patch("app.agents.workflow.find_uploaded_file", return_value=__import__("pathlib").Path(__file__)):
            with patch("app.agents.workflow.extract_text") as mock_extract:
                mock_extract.return_value = type("E", (), {"text": "第一章 测试\n\n内容" * 200, "file_type": "txt"})()
                with patch("app.agents.workflow.get_book_meta") as mock_meta:
                    mock_meta.return_value = type("M", (), {"title": "金字塔原理", "author": "巴巴拉"})()
                    with patch("app.agents.workflow.get_external_book_info") as mock_info:
                        mock_info.return_value = type(
                            "X",
                            (),
                            {
                                "title": "金字塔原理",
                                "author": "巴巴拉",
                                "description": "简介",
                                "tavily_answer": None,
                                "tavily_results": [
                                    {"title": "金字塔原理 书评", "url": "https://example.com/review", "content": "这是一篇很长的书评内容" * 20},
                                ],
                                "sources": ["tavily"],
                            },
                        )()
                        with patch("app.llm.chat_model.get_chat_model", return_value=DummyModel()):
                            out = app.invoke({"book_id": "b1", "user_requirements": "", "user_feelings": ""})
                            self.assertEqual(out.get("status"), "completed")
                            self.assertIn("优质书评", out.get("external_info", ""))


if __name__ == "__main__":
    unittest.main()
