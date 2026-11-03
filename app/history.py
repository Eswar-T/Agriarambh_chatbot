"""Save guide chats in Supabase. The browser only sends a session id."""

from __future__ import annotations

import re
from uuid import UUID

import httpx

from app.config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

_SESSION = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class HistoryError(RuntimeError):
    pass


def configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def valid_session(session_id: str) -> bool:
    return bool(_SESSION.match(session_id or ""))


def status() -> dict:
    if not configured():
        return {
            "configured": False,
            "ok": False,
            "detail": "Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to .env.",
        }
    try:
        _request("GET", "guide_sessions", params={"select": "id", "limit": "1"})
    except HistoryError as exc:
        return {"configured": True, "ok": False, "detail": str(exc)}
    return {"configured": True, "ok": True, "detail": ""}


def ensure_session(session_id: str, language: str | None = None) -> None:
    _check_session(session_id)
    if language is not None:
        language = "kn" if language == "kn" else "en"
    existing = _request(
        "GET",
        "guide_sessions",
        params={"id": f"eq.{session_id}", "select": "id,language"},
    )
    if not existing:
        _request(
            "POST",
            "guide_sessions",
            json={"id": session_id, "language": language or "kn"},
            prefer="return=minimal",
        )
        return
    if language and existing[0].get("language") != language:
        _request(
            "PATCH",
            "guide_sessions",
            params={"id": f"eq.{session_id}"},
            json={"language": language},
            prefer="return=minimal",
        )


def list_messages(session_id: str) -> dict:
    _check_session(session_id)
    sessions = _request(
        "GET",
        "guide_sessions",
        params={"id": f"eq.{session_id}", "select": "language"},
    )
    messages = _request(
        "GET",
        "guide_messages",
        params={
            "session_id": f"eq.{session_id}",
            "select": "id,role,text_kn,text_en,sources,suggestions_kn,suggestions_en,created_at",
            "order": "created_at.asc",
        },
    )
    language = "kn"
    if isinstance(sessions, list) and sessions:
        language = sessions[0].get("language") or "kn"
    return {
        "language": language,
        "messages": [_message(row) for row in messages or []],
    }


def add_message(
    session_id: str,
    role: str,
    *,
    text_kn: str | None = None,
    text_en: str | None = None,
    sources: list | None = None,
    suggestions_kn: list | None = None,
    suggestions_en: list | None = None,
) -> dict:
    _check_session(session_id)
    rows = _request(
        "POST",
        "guide_messages",
        json={
            "session_id": session_id,
            "role": role,
            "text_kn": text_kn or None,
            "text_en": text_en or None,
            "sources": sources or [],
            "suggestions_kn": suggestions_kn or [],
            "suggestions_en": suggestions_en or [],
        },
        prefer="return=representation",
    )
    return _message(rows[0])


def update_translation(session_id: str, message_id: str, target: str, text: str, suggestions: list[str]) -> dict:
    _check_session(session_id)
    _check_session(message_id)
    column = "text_kn" if target == "kn" else "text_en"
    suggestion_column = "suggestions_kn" if target == "kn" else "suggestions_en"
    payload = {column: text}
    if suggestions:
        payload[suggestion_column] = suggestions
    rows = _request(
        "PATCH",
        "guide_messages",
        params={"id": f"eq.{message_id}", "session_id": f"eq.{session_id}"},
        json=payload,
        prefer="return=representation",
    )
    if not rows:
        raise HistoryError("Message was not found for this chat.")
    return _message(rows[0])


def _message(row: dict) -> dict:
    return {
        "id": row["id"],
        "role": row["role"],
        "textKn": row.get("text_kn") or "",
        "textEn": row.get("text_en") or "",
        "sources": row.get("sources") or [],
        "suggestionsKn": row.get("suggestions_kn") or [],
        "suggestionsEn": row.get("suggestions_en") or [],
    }


def _check_session(value: str) -> None:
    try:
        UUID(value)
    except (TypeError, ValueError) as exc:
        raise HistoryError("Session id is not valid.") from exc


def _request(method: str, table: str, *, params: dict | None = None, json=None, prefer: str = "return=minimal"):
    if not configured():
        raise HistoryError("Supabase is not configured.")
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Accept": "application/json",
        "Prefer": prefer,
    }
    if json is not None:
        headers["Content-Type"] = "application/json"
    try:
        response = httpx.request(
            method,
            f"{SUPABASE_URL}/rest/v1/{table}",
            params=params,
            json=json,
            headers=headers,
            timeout=20.0,
        )
    except httpx.HTTPError as exc:
        raise HistoryError("Could not reach Supabase.") from exc
    if response.status_code >= 400:
        detail = response.text[:240]
        if response.status_code == 404 or "guide_" in detail and "schema cache" in detail:
            raise HistoryError("Run supabase/guide_chat.sql in the Supabase SQL editor.")
        raise HistoryError(f"Supabase returned {response.status_code}.")
    if not response.content:
        return []
    return response.json()
