from openai import AsyncOpenAI


class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str, batch_size: int = 32):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.batch_size = batch_size

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for offset in range(0, len(texts), self.batch_size):
            response = await self.client.embeddings.create(model=self.model, input=texts[offset : offset + self.batch_size])
            vectors.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))
        return vectors

