from __future__ import annotations

from typing import List


MAX_MESSAGE_LENGTH = 1200
MAX_LOG_LINES = 16
MAX_STATUS_LINES = 40
MAX_RANK_LINES = 15


def truncate_lines(text: str, max_lines: int, suffix: str = "") -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text

    remain = len(lines) - max_lines
    result = lines[:max_lines]
    tail = suffix or f"...（另有 {remain} 行已省略）"
    result.append(tail)
    return "\n".join(result)


def split_long_text(text: str, limit: int = MAX_MESSAGE_LENGTH) -> List[str]:
    if len(text) <= limit:
        return [text]

    lines = text.splitlines(keepends=True)
    chunks: List[str] = []
    current = ""

    for line in lines:
        if len(current) + len(line) <= limit:
            current += line
            continue

        if current:
            chunks.append(current.rstrip("\n"))
            current = ""

        while len(line) > limit:
            chunks.append(line[:limit])
            line = line[limit:]

        current = line

    if current:
        chunks.append(current.rstrip("\n"))

    return chunks


def smart_compose(
    header: str | None = None,
    body: str | None = None,
    footer: str | None = None,
    body_max_lines: int | None = None,
    limit: int = MAX_MESSAGE_LENGTH,
) -> List[str]:
    body = body or ""
    if body_max_lines is not None:
        body = truncate_lines(body, body_max_lines)

    parts = []
    if header:
        parts.append(header.strip())
    if body:
        parts.append(body.strip())
    if footer:
        parts.append(footer.strip())

    text = "\n\n".join(parts).strip()
    return split_long_text(text, limit=limit)
