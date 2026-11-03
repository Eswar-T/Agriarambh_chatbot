from __future__ import annotations

import httpx

from app.config import CHAT_MODEL, EMBED_MODEL, OLLAMA_HOST


class OllamaError(RuntimeError):
    pass


def _client() -> httpx.Client:
    return httpx.Client(base_url=OLLAMA_HOST, timeout=httpx.Timeout(180.0, connect=5.0))


def list_models() -> list[str]:
    try:
        with _client() as client:
            response = client.get("/api/tags")
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OllamaError(
            "Ollama is not running. Start it with `ollama serve`, then pull the models."
        ) from exc
    models = response.json().get("models") or []
    return [item.get("name", "") for item in models]


def model_ready(installed: list[str], wanted: str) -> bool:
    return any(name == wanted or name.startswith(wanted + ":") for name in installed)


def embed_texts(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    try:
        with _client() as client:
            for start in range(0, len(texts), 16):
                batch = texts[start : start + 16]
                response = client.post("/api/embed", json={"model": EMBED_MODEL, "input": batch})
                if response.status_code == 404:
                    vectors.extend(_embed_one_by_one(client, batch))
                    continue
                response.raise_for_status()
                vectors.extend(response.json()["embeddings"])
    except httpx.HTTPError as exc:
        raise OllamaError(
            f"Could not embed with {EMBED_MODEL}. Run `ollama pull {EMBED_MODEL}`."
        ) from exc
    return vectors


def _embed_one_by_one(client: httpx.Client, texts: list[str]) -> list[list[float]]:
    vectors = []
    for text in texts:
        response = client.post("/api/embeddings", json={"model": EMBED_MODEL, "prompt": text})
        response.raise_for_status()
        vectors.append(response.json()["embedding"])
    return vectors


def chat(messages: list[dict[str, str]], *, json_mode: bool = True, num_predict: int = 400) -> str:
    payload = {
        "model": CHAT_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": num_predict},
    }
    if json_mode:
        payload["format"] = "json"
    try:
        with _client() as client:
            response = client.post("/api/chat", json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OllamaError(
            f"Could not generate an answer with {CHAT_MODEL}. Run `ollama pull {CHAT_MODEL}`."
        ) from exc
    return response.json()["message"]["content"]
