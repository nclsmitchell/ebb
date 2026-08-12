import openai

CHAT_MODEL = "gpt-4o"
FAST_MODEL = "gpt-4o-mini"
LEGACY_MODEL = "gpt-3.5-turbo"


def embed(text: str) -> list[float]:
    return openai.embeddings.create(model="text-embedding-3-large", input=text)
