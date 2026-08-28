from collections.abc import AsyncIterator

from openai import AsyncOpenAI


class OpenAIChatModel:
    def __init__(self, api_key: str, model: str, max_tokens: int = 800):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    async def rewrite(self, question: str, history: list[dict[str, str]]) -> str:
        if not history:
            return question
        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            max_tokens=120,
            messages=[
                {"role": "system", "content": "Rewrite the final user question as a standalone retrieval query. Return only the query."},
                *history[-10:],
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content or question

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        response = await self.client.chat.completions.create(model=self.model, temperature=0, max_tokens=self.max_tokens, messages=messages, stream=True)
        async for part in response:
            token = part.choices[0].delta.content if part.choices else None
            if token:
                yield token
