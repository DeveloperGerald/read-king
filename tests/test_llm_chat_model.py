from __future__ import annotations

import unittest

try:
    import langchain_community  # noqa: F401
except Exception:
    langchain_community = None

try:
    from app.core.config import Settings
    from app.llm.chat_model import get_chat_model
except Exception:
    Settings = None
    get_chat_model = None


class TestChatModel(unittest.TestCase):
    @unittest.skipIf(langchain_community is None or Settings is None or get_chat_model is None, "dependencies are not installed")
    def test_get_chat_model_ollama(self) -> None:
        s = Settings(llm_provider="ollama")
        m = get_chat_model(s)
        self.assertIsNotNone(m)


if __name__ == "__main__":
    unittest.main()

