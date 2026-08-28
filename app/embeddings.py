from app.reliability import retry_async


class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str, batch_size: int = 32, timeout_seconds: float = 60.0, retry_attempts: int = 3, retry_base_delay: float = 0.5):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout_seconds)
        self.model = model
        self.batch_size = batch_size
        self.retry_attempts = retry_attempts
        self.retry_base_delay = retry_base_delay

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for offset in range(0, len(texts), self.batch_size):
            async def request():
                return await self.client.embeddings.create(model=self.model, input=texts[offset : offset + self.batch_size])
            response = await retry_async(request, attempts=self.retry_attempts, base_delay=self.retry_base_delay)
            vectors.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))
        return vectors
