import os
import sys
from pathlib import Path

# 将项目根目录添加到 sys.path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from app.core.config import get_settings
from app.llm.chat_model import get_chat_model

def test_deepseek_connection():
    settings = get_settings()
    if settings.llm_provider != "deepseek":
        print(f"Current LLM_PROVIDER is {settings.llm_provider}, not deepseek.")
        return

    print(f"Testing DeepSeek connection with model: {settings.deepseek_model}")
    try:
        model = get_chat_model(settings)
        response = model.invoke("Hello, are you DeepSeek?")
        print("Connection successful!")
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_deepseek_connection()
