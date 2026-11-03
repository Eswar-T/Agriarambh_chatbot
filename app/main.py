from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import CHAT_MODEL, EMBED_MODEL, STATIC_DIR
from app.history import HistoryError, add_message, configured, ensure_session, list_messages, status, update_translation, valid_session
from app.ollama_client import OllamaError, list_models, model_ready
from app.rag import answer, ensure_index, translate_items, translation_available

app = FastAPI(title="GreenPlot Guide")


class Turn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    language: str = "kn"
    history: list[Turn] = Field(default_factory=list)
    sessionId: str = ""


class TranslateItem(BaseModel):
    id: str
    text: str = ""
    suggestions: list[str] = Field(default_factory=list)


class TranslateRequest(BaseModel):
    target: str
    sessionId: str = ""
    items: list[TranslateItem] = Field(default_factory=list)


@app.get("/api/health")
def health():
    try:
        installed = list_models()
    except OllamaError as exc:
        history = status()
        return {
            "ok": False,
            "ollama": False,
            "detail": str(exc),
            "chatModel": CHAT_MODEL,
            "embedModel": EMBED_MODEL,
            "history": history["ok"],
            "historyDetail": history["detail"],
        }
    chat_ok = model_ready(installed, CHAT_MODEL)
    embed_ok = model_ready(installed, EMBED_MODEL)
    history = status()
    return {
        "ok": chat_ok and embed_ok,
        "ollama": True,
        "chatModel": CHAT_MODEL,
        "embedModel": EMBED_MODEL,
        "chatReady": chat_ok,
        "embedReady": embed_ok,
        "history": history["ok"],
        "historyDetail": history["detail"],
    }


@app.get("/api/history")
def history(sessionId: str):
    if not valid_session(sessionId):
        return {"language": "kn", "messages": [], "error": "Session id is not valid."}
    if not configured():
        return {"language": "kn", "messages": [], "configured": False}
    try:
        ensure_session(sessionId)
        payload = list_messages(sessionId)
        payload["configured"] = True
        return payload
    except HistoryError as exc:
        return {"language": "kn", "messages": [], "configured": True, "error": str(exc)}


@app.post("/api/translate")
def translate(body: TranslateRequest):
    if not translation_available():
        return {
            "items": [],
            "error": f"{CHAT_MODEL} cannot translate Kannada and English reliably. Pull qwen2.5:7b and set OLLAMA_CHAT_MODEL.",
        }
    target = "kn" if body.target == "kn" else "en"
    items = [item.model_dump() for item in body.items if item.text.strip()]
    if configured() and valid_session(body.sessionId):
        try:
            ensure_session(body.sessionId, target)
        except HistoryError as exc:
            return {"items": [], "error": str(exc)}
    try:
        translated = translate_items(items, target)
    except OllamaError as exc:
        return {"items": [], "error": str(exc)}
    if configured() and valid_session(body.sessionId):
        for item in translated:
            if not item["text"] or not valid_session(str(item["id"])):
                continue
            try:
                update_translation(body.sessionId, str(item["id"]), target, item["text"], item["suggestions"])
            except HistoryError:
                item["saved"] = False
            else:
                item["saved"] = True
    return {"items": translated}


@app.post("/api/chat")
def chat(body: ChatRequest):
    language = "kn" if body.language == "kn" else "en"
    try:
        ensure_index()
        result = answer(
            body.message.strip(),
            language,
            [turn.model_dump() for turn in body.history],
        )
    except OllamaError as exc:
        return {
            "reply": str(exc),
            "replyEnglish": str(exc),
            "suggestions": [],
            "sources": [],
            "error": True,
        }
    if configured() and valid_session(body.sessionId):
        try:
            ensure_session(body.sessionId, language)
            user = add_message(
                body.sessionId,
                "user",
                text_kn=body.message.strip() if language == "kn" else None,
                text_en=body.message.strip() if language == "en" else None,
            )
            kannada_reply = result["reply"] if result.get("answerLanguage") == "kn" else None
            result["userMessage"] = user
            result["assistantMessage"] = add_message(
                body.sessionId,
                "assistant",
                text_kn=kannada_reply,
                text_en=result.get("replyEnglish") or result.get("reply"),
                sources=result.get("sources") or [],
                suggestions_kn=result.get("suggestions") if kannada_reply else [],
                suggestions_en=result.get("suggestions") if not kannada_reply else [],
            )
        except HistoryError as exc:
            result["historyError"] = str(exc)
    return result


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
