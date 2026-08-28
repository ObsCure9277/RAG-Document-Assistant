from collections.abc import AsyncIterator

from openai import AsyncOpenAI
from app.reliability import retry_async


class OpenAIChatModel:
    def __init__(self, api_key: str, model: str, max_tokens: int = 800, timeout_seconds: float = 60.0, retry_attempts: int = 3, retry_base_delay: float = 0.5):
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout_seconds)
        self.model = model
        self.max_tokens = max_tokens
        self.retry_attempts = retry_attempts
        self.retry_base_delay = retry_base_delay

    async def rewrite(self, question: str, history: list[dict[str, str]]) -> str:
        if not history:
            return question
        async def request():
            return await self.client.chat.completions.create(model=self.model, temperature=0, max_tokens=120, messages=[{"role": "system", "content": "Rewrite the final user question as a standalone retrieval query. Return only the query."}, *history[-10:], {"role": "user", "content": question}])
        response = await retry_async(request, attempts=self.retry_attempts, base_delay=self.retry_base_delay)
        return response.choices[0].message.content or question

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        response = await self.client.chat.completions.create(model=self.model, temperature=0, max_tokens=self.max_tokens, messages=messages, stream=True)
        async for part in response:
            token = part.choices[0].delta.content if part.choices else None
            if token:
                yield token
