"""大模型统一适配层（当前 DeepSeek，可切换）。

所有业务代码只允许通过本层调用 LLM，禁止直接拼 API。
"""
import time

from openai import OpenAI

from app.config import settings


class LLMClient:
    """DeepSeek 封装：统一参数、超时、重试。"""

    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY or "sk-empty",
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=settings.LLM_TIMEOUT,
        )
        self.model = settings.DEEPSEEK_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_retries = settings.LLM_MAX_RETRIES

    def chat(self, system: str, user: str) -> str:
        """调用对话模型，返回纯文本回答。失败自动重试。"""
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=self.temperature,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:  # noqa: BLE001
                last_error = e
                time.sleep(1)
        raise RuntimeError(f"LLM调用失败: {last_error}")


llm = LLMClient()
