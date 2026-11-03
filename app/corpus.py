"""Turn the GreenPlot module docs into user-facing chunks.

Internal files (architecture, database, roadmap) are skipped. Sections about
known issues, implementation plans, and data models are dropped. Lines that
describe passwords, keys, or database policies are removed so a how-to answer
cannot repeat them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import DOCS_DIR

SKIP_FILES = {
    "01-architecture.md",
    "02-database-backend.md",
    "04-roadmap-known-issues.md",
}

DROP_SECTION = re.compile(
    r"known issues|implementation plan|test checklist|definition of done|"
    r"data model|services & state|state and api|tech debt|open questions|"
    r"ota updates|dependencies and known|dependencies$",
    re.IGNORECASE,
)

SENSITIVE_LINE = re.compile(
    r"password|phonetopassword|greenplot-|service role|\brls\b|"
    r"api[_ ]?key|deterministic|secret|anon key|keystore",
    re.IGNORECASE,
)

FENCE = re.compile(r"```[a-zA-Z]*\n?(.*?)```", re.DOTALL)
CODE_LINE = re.compile(
    r"\b(import |function |const |RPC |Api\.|use[A-Z]\w*\(|\.tsx?\b|=>)"
)
FILE_CODE = re.compile(r"`(?:src|supabase|android|ios)/[^`]+`")
BACKTICK_IDENT = re.compile(r"`[^`\n]+`")
HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")


@dataclass(frozen=True)
class Chunk:
    id: str
    source: str
    title: str
    section: str
    text: str


def load_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(DOCS_DIR.glob("M*.md")):
        if path.name in SKIP_FILES:
            continue
        chunks.extend(_chunk_file(path.name, path.read_text(encoding="utf-8")))
    return chunks


def _chunk_file(filename: str, raw: str) -> list[Chunk]:
    title = _doc_title(raw)
    body = _clean(raw)
    sections = _sections(body)
    chunks: list[Chunk] = []
    for section, text in sections:
        if DROP_SECTION.search(section):
            continue
        kept = _drop_sensitive_lines(text).strip()
        if len(kept) < 80:
            continue
        for index, piece in enumerate(_split(kept)):
            chunks.append(
                Chunk(
                    id=f"{filename}:{section}:{index}",
                    source=filename,
                    title=title,
                    section=section,
                    text=piece,
                )
            )
    return chunks


def _doc_title(raw: str) -> str:
    for line in raw.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "GreenPlot"


def _clean(raw: str) -> str:
    text = FENCE.sub(_unwrap_fence, raw)
    text = FILE_CODE.sub(" ", text)
    text = LINK.sub(r"\1", text)
    text = BACKTICK_IDENT.sub(" ", text)
    text = re.sub(r"\b\w+\(\)", " ", text)
    return text


def _unwrap_fence(match: re.Match) -> str:
    kept = [line for line in match.group(1).splitlines() if line.strip() and not CODE_LINE.search(line)]
    return "\n".join(kept)


def _sections(text: str) -> list[tuple[str, str]]:
    matches = [match for match in HEADING.finditer(text) if len(match.group(1)) <= 2]
    if not matches:
        return [("Overview", text)]
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        if len(match.group(1)) == 1:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(2).strip(), text[start:end]))
    return sections


def _drop_sensitive_lines(text: str) -> str:
    lines = [line for line in text.splitlines() if not SENSITIVE_LINE.search(line)]
    return "\n".join(lines)


def _split(text: str, limit: int = 1400) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > limit:
            if current:
                pieces.append(current.strip())
                current = ""
            for start in range(0, len(paragraph), limit):
                pieces.append(paragraph[start : start + limit].strip())
            continue
        if current and len(current) + len(paragraph) + 2 > limit:
            pieces.append(current.strip())
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        pieces.append(current.strip())
    return pieces
