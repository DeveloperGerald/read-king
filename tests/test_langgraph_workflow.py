from __future__ import annotations

import unittest

try:
    import langgraph  # noqa: F401
except Exception:
    langgraph = None

try:
    from app.core.config import Settings
    from app.agents.workflow import build_report_graph
except Exception:
    Settings = None
    build_report_graph = None


class TestLangGraphWorkflow(unittest.TestCase):
    @unittest.skipIf(langgraph is None or Settings is None or build_report_graph is None, "dependencies are not installed")
    def test_build_graph(self) -> None:
        app = build_report_graph(settings=Settings())
        self.assertTrue(hasattr(app, "invoke"))


if __name__ == "__main__":
    unittest.main()

