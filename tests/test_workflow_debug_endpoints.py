from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:
    TestClient = None

try:
    from app.main import app
except Exception:
    app = None


class TestWorkflowDebugEndpoints(unittest.TestCase):
    @unittest.skipIf(TestClient is None or app is None, "fastapi is not installed")
    def test_preview_context_endpoint(self) -> None:
        client = TestClient(app)
        with patch("app.api.endpoints.run_report_workflow") as mock_run:
            mock_run.return_value = {"status": "context_ready", "context": "内容1"}
            r = client.post("/api/books/b1/workflow/context", json={"user_requirements": "", "user_feelings": ""})
            self.assertEqual(r.status_code, 200)
            self.assertIn("内容1", r.text)

    @unittest.skipIf(TestClient is None or app is None, "fastapi is not installed")
    def test_preview_prompt_endpoint(self) -> None:
        client = TestClient(app)
        with patch("app.api.endpoints.build_prompt_preview") as mock_preview:
            mock_preview.return_value = {"prompt": "PROMPT"}
            r = client.post("/api/books/b1/workflow/prompt", json={"user_requirements": "", "user_feelings": ""})
            self.assertEqual(r.status_code, 200)
            self.assertIn("PROMPT", r.text)


if __name__ == "__main__":
    unittest.main()

