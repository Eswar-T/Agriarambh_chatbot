from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict

from app.config import CHAT_MODEL, EMBED_MODEL, INDEX_PATH, MAX_HISTORY, MIN_SCORE, TOP_K
from app.corpus import Chunk, load_chunks
from app.ollama_client import chat, embed_texts

SYSTEM_PROMPT = """You are the GreenPlot in-app guide. You help farmers and land owners use the GreenPlot mobile app.

Rules:
- Answer only from the context blocks. If the context does not contain the steps, say you do not have that in the guide.
- If the context says a feature is not built, proposed, placeholder, mock, or coming soon, say it is not available in the app yet.
- Explain with short numbered steps a first-time user can follow on the phone.
- Use everyday words: sign-up screen, home screen, settings. Never mention code, screen component names, file names, databases, passwords, API keys, or security weaknesses.
- Do not invent buttons, prices, or screens.
- Write reply in simple English. Put the same English text in replyEnglish.
- suggestions must be three short English follow-up questions.

Return only JSON with this shape:
{"reply":"...","replyEnglish":"...","suggestions":["...","...","..."]}
"""


def ensure_index() -> dict:
    chunks = load_chunks()
    digest = _chunk_digest(chunks)
    if INDEX_PATH.exists():
        saved = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if saved.get("embed_model") == EMBED_MODEL and saved.get("digest") == digest:
            return saved
    vectors = embed_texts([_embed_input(chunk) for chunk in chunks])
    payload = {
        "embed_model": EMBED_MODEL,
        "chat_model": CHAT_MODEL,
        "digest": digest,
        "chunk_count": len(chunks),
        "chunks": [
            {**asdict(chunk), "embedding": vector}
            for chunk, vector in zip(chunks, vectors)
        ],
    }
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def retrieve(question: str, index: dict | None = None) -> list[dict]:
    index = index or json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    query = embed_texts([question])[0]
    scored = []
    for chunk in index["chunks"]:
        score = _cosine(query, chunk["embedding"])
        scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored or scored[0][0] < MIN_SCORE:
        return []
    cutoff = scored[0][0] - 0.04
    return [
        {
            "score": round(score, 3),
            "source": chunk["source"],
            "title": chunk["title"],
            "section": chunk["section"],
            "text": chunk["text"],
        }
        for score, chunk in scored[:TOP_K]
        if score >= cutoff
    ]


def answer(question: str, language: str, history: list[dict] | None = None) -> dict:
    language = "kn" if language == "kn" else "en"
    lookup = _search_query(question, language)
    hits = retrieve(lookup)
    sources = [
        {"title": hit["title"], "section": hit["section"], "source": hit["source"]}
        for hit in hits
    ]
    if not hits:
        return _unknown(language, sources)

    context = "\n\n".join(
        f"[{hit['title']} — {hit['section']}]\n{hit['text']}" for hit in hits
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in (history or [])[-MAX_HISTORY:]:
        role = "assistant" if turn.get("role") == "assistant" else "user"
        content = str(turn.get("content") or "").strip()
        if content:
            messages.append({"role": role, "content": content})
    messages.append(
        {
            "role": "user",
            "content": f"Language: English\n\nContext:\n{context}\n\nQuestion: {lookup}",
        }
    )
    parsed = _parse_json(chat(messages))
    reply_en = _plain_language(str(parsed.get("reply") or parsed.get("replyEnglish") or ""))
    suggestions = _suggestions(parsed.get("suggestions"), "en")
    if not reply_en or _repetitive(reply_en):
        return _unknown(language, sources)
    answer_language = "en"
    reply = reply_en
    if language == "kn" and _kannada_supported():
        translated, kannada_suggestions = _to_kannada(reply_en, suggestions)
        if translated != reply_en:
            reply = translated
            suggestions = kannada_suggestions
            answer_language = "kn"
    return {
        "reply": reply,
        "replyEnglish": reply_en,
        "suggestions": suggestions,
        "sources": _unique_sources(sources),
        "answerLanguage": answer_language,
    }


def _chunk_digest(chunks: list[Chunk]) -> str:
    payload = "\n".join(f"{chunk.id}\n{chunk.text}" for chunk in chunks)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


KN_TERMS = (
    ("ಜಮೀನುದಾರ", "land owner"),
    ("ಜಮೀನ", "add land plot"),
    ("ಗುತ್ತಿಗ", "lease agreement"),
    ("ಖಾತ", "create account"),
    ("ತೆರೆಯ", "sign up or login"),
    ("ಬೆಳೆ", "crop plan"),
    ("ಭಾಷ", "change language settings"),
    ("ರೈತ", "farmer"),
    ("ಮಾಲೀಕ", "land owner"),
    ("ಮಾರುಕಟ್ಟ", "market price"),
    ("ಹವಾಮಾನ", "weather"),
    ("ಮಣ್ಣ", "soil"),
    ("ಪಾವತ", "payment"),
    ("ಸೆಟ್ಟಿಂಗ", "settings"),
    ("ಅಧಿಸೂಚನ", "notification"),
    ("ಕೊಯ್ಲ", "harvest"),
    ("ಯಂತ್ರ", "machinery"),
    ("ಕೂಲಿ", "labor"),
    ("ಸಮುದಾಯ", "community"),
    ("ಲಾಗಿನ", "login"),
)


def _search_query(question: str, language: str) -> str:
    del language
    if not re.search(r"[\u0c80-\u0cff]", question):
        return question
    english = [phrase for word, phrase in KN_TERMS if word in question]
    if not english:
        return "How do I use the GreenPlot app?"
    return "How do I " + " and ".join(english) + "?"


def _kannada_supported() -> bool:
    return not any(tag in CHAT_MODEL for tag in (":0.5b", ":1b", ":1.5b", ":3b"))


def translation_available() -> bool:
    return _kannada_supported()


def _to_kannada(reply_en: str, suggestions: list[str]) -> tuple[str, list[str]]:
    raw = chat(
        [
            {
                "role": "system",
                "content": "Translate the JSON into simple spoken Kannada. Keep the same steps. Return only JSON {\"reply\",\"suggestions\"}. suggestions must be three short Kannada questions.",
            },
            {
                "role": "user",
                "content": json.dumps({"reply": reply_en, "suggestions": suggestions}, ensure_ascii=False),
            },
        ],
        num_predict=500,
    )
    parsed = _parse_json(raw)
    reply = _plain_language(str(parsed.get("reply") or ""))
    translated = _suggestions(parsed.get("suggestions"), "kn")
    if not reply or _repetitive(reply) or not re.search(r"[\u0c80-\u0cff]", reply):
        return reply_en, suggestions
    return reply, translated


def translate_items(items: list[dict], target: str) -> list[dict]:
    target = "kn" if target == "kn" else "en"
    texts = _translate_many([str(item.get("text") or "") for item in items], target)
    translated = []
    for item, text in zip(items, texts):
        suggestions = []
        source_suggestions = [str(line) for line in item.get("suggestions") or [] if str(line).strip()]
        if text and source_suggestions:
            suggestions = _translate_many(source_suggestions, target)
            if any(not line for line in suggestions):
                suggestions = []
        translated.append({"id": item.get("id"), "text": text, "suggestions": suggestions})
    return translated


def _translate_many(texts: list[str], target: str) -> list[str]:
    if not texts:
        return []
    language = "Kannada" if target == "kn" else "English"
    raw = chat(
        [
            {
                "role": "system",
                "content": (
                    f"Translate each string into simple {language}. "
                    "Keep the same number of steps and the same meaning. "
                    'Return only JSON {"items":["..."]} with one string per input, in the same order.'
                ),
            },
            {"role": "user", "content": json.dumps({"items": texts}, ensure_ascii=False)},
        ],
        num_predict=min(900, 160 * len(texts)),
    )
    parsed = _parse_json(raw)
    values = parsed.get("items")
    if not isinstance(values, list) or len(values) != len(texts):
        return [_translate_one(text, target) for text in texts]
    return [
        _accept_translation(source, str(value or "").strip(), target)
        for source, value in zip(texts, values)
    ]


def _translate_one(text: str, target: str) -> str:
    language = "Kannada" if target == "kn" else "English"
    raw = chat(
        [
            {
                "role": "system",
                "content": f"Translate into simple {language}. Return only JSON {{\"text\":\"...\"}}.",
            },
            {"role": "user", "content": text},
        ],
        num_predict=300,
    )
    parsed = _parse_json(raw)
    return _accept_translation(text, str(parsed.get("text") or "").strip(), target)


def _accept_translation(source: str, translated: str, target: str) -> str:
    if not translated or translated.strip() == source.strip():
        return ""
    if _repetitive(translated):
        return ""
    has_kannada = bool(re.search(r"[\u0c80-\u0cff]", translated))
    has_latin = bool(re.search(r"[A-Za-z]", translated))
    if target == "kn" and not has_kannada:
        return ""
    if target == "kn":
        leftover = re.findall(r"[A-Za-z]{4,}", translated)
        allowed = {"greenplot", "whatsapp", "gps"}
        if any(word.lower() not in allowed for word in leftover):
            return ""
    if target == "en" and (not has_latin or has_kannada):
        return ""
    return translated.strip()


def _repetitive(text: str) -> bool:
    words = re.findall(r"\w+", text.lower())
    if len(words) < 30:
        return False
    return len(set(words)) / len(words) < 0.45


def _embed_input(chunk: Chunk) -> str:
    return f"{chunk.title}\n{chunk.section}\n{chunk.text}"


def _cosine(left: list[float], right: list[float]) -> float:
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for a, b in zip(left, right):
        dot += a * b
        left_norm += a * a
        right_norm += b * b
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (math.sqrt(left_norm) * math.sqrt(right_norm))


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return {"reply": raw, "replyEnglish": raw, "suggestions": []}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"reply": raw, "replyEnglish": raw, "suggestions": []}


def _plain_language(text: str) -> str:
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\b(?!WhatsApp\b)[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+\b", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +([.,])", r"\1", text)
    return text.strip()


def _suggestions(value, language: str) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        if len(items) >= 3:
            return items[:3]
    if language == "kn":
        return [
            "ರೈತ ಮತ್ತು ಜಮೀನುದಾರರ ನಡುವೆ ವ್ಯತ್ಯಾಸವೇನು?",
            "ಭಾಷೆಯನ್ನು ಹೇಗೆ ಬದಲಾಯಿಸುವುದು?",
            "ಸಹಾಯ ಬೇಕಾದರೆ ಎಲ್ಲಿಗೆ ಹೋಗಬೇಕು?",
        ]
    return [
        "What is the difference between a farmer and a land owner?",
        "How do I change the language?",
        "Where do I edit my profile?",
    ]


def _unique_sources(sources: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for source in sources:
        key = (source["source"], source["section"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return unique


def _unknown(language: str, sources: list[dict]) -> dict:
    if language == "kn":
        reply = "ಈ ಪ್ರಶ್ನೆಗೆ ಮಾರ್ಗದರ್ಶಿಯಲ್ಲಿ ಉತ್ತರವಿಲ್ಲ. ಖಾತೆ, ಜಮೀನು, ಗುತ್ತಿಗೆ, ಬೆಳೆ, ಮಾರುಕಟ್ಟೆ ಅಥವಾ ಸೆಟ್ಟಿಂಗ್‌ಗಳ ಬಗ್ಗೆ ಕೇಳಿ."
        reply_en = "The guide does not cover that. Ask about your account, land, a lease, crops, the market, or settings."
        suggestions = [
            "ಖಾತೆ ಹೇಗೆ ತೆರೆಯುವುದು?",
            "ಜಮೀನನ್ನು ಹೇಗೆ ಸೇರಿಸುವುದು?",
            "ಗುತ್ತಿಗೆಗೆ ಹೇಗೆ ಅರ್ಜಿ ಹಾಕುವುದು?",
        ]
    else:
        reply = "The guide does not cover that. Ask about your account, land, a lease, crops, the market, or settings."
        reply_en = reply
        suggestions = [
            "How do I create an account?",
            "How do I add my land?",
            "How do I apply for a lease?",
        ]
    return {
        "reply": reply,
        "replyEnglish": reply_en,
        "suggestions": suggestions,
        "sources": _unique_sources(sources),
        "answerLanguage": "en" if language == "kn" and reply == reply_en else language,
    }
