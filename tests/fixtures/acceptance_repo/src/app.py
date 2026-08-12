import openai

PRIMARY_MODEL = "gpt-4-turbo-2024-04-09"
FALLBACK_MODEL = "claude-3-5-sonnet-20241022"


def call(prompt: str) -> str:
    return openai.chat.completions.create(model=PRIMARY_MODEL, messages=[{"role": "user", "content": prompt}])
