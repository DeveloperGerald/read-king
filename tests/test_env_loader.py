from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


class TestEnvLoader(unittest.TestCase):
    def test_load_env_file_tolerant(self) -> None:
        try:
            from app.core.config import load_env_file
        except Exception:
            self.skipTest("dependencies are not installed")

        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text(
                "\n".join(
                    [
                        "- OLLAMA_MODEL=qwen2.5:7b",
                        "export CHROMA_SERVER_PORT=8002",
                        "# comment",
                        "TAVILY_TOPIC='general'",
                    ]
                ),
                encoding="utf-8",
            )

            for k in ["OLLAMA_MODEL", "CHROMA_SERVER_PORT", "TAVILY_TOPIC"]:
                os.environ.pop(k, None)

            load_env_file(p)
            self.assertEqual(os.environ.get("OLLAMA_MODEL"), "qwen2.5:7b")
            self.assertEqual(os.environ.get("CHROMA_SERVER_PORT"), "8002")
            self.assertEqual(os.environ.get("TAVILY_TOPIC"), "general")


if __name__ == "__main__":
    unittest.main()
