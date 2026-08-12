export const CHAT_MODEL = "gpt-4o-mini";

export async function chat(prompt: string): Promise<string> {
  return fetch("/api/chat", { method: "POST", body: JSON.stringify({ model: CHAT_MODEL, prompt }) }).then((r) => r.text());
}
