#!/usr/bin/env python3
"""Update README reflection block deterministically by UTC day."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

START_MARKER = "<!-- REFLECTION_START -->"
END_MARKER = "<!-- REFLECTION_END -->"


class ReflectionError(Exception):
    """Raised for reflection update validation problems."""


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReflectionError(f"Missing file: {path}") from exc


def load_quotes(path: Path) -> list[str]:
    text = read_utf8(path)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReflectionError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, list):
        raise ReflectionError(f"Invalid reflections format in {path}: expected a JSON array.")
    if not data:
        raise ReflectionError(f"Invalid reflections format in {path}: collection is empty.")

    quotes: list[str] = []
    for index, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ReflectionError(
                f"Invalid reflection at index {index}: expected an object with a non-empty 'quote' string."
            )
        quote = entry.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            raise ReflectionError(
                f"Invalid reflection at index {index}: 'quote' must be a non-empty string."
            )
        quotes.append(quote)

    return quotes


def quote_for_today(quotes: list[str]) -> str:
    day_number = datetime.now(timezone.utc).date().toordinal()
    return quotes[day_number % len(quotes)]


def sanitize_quote(quote: str) -> str:
    collapsed = " ".join(quote.replace("\r\n", "\n").replace("\r", "\n").splitlines())
    collapsed = re.sub(r"\s+", " ", collapsed).strip()

    # Neutralize marker injection if marker-like text appears in a quote.
    collapsed = collapsed.replace(START_MARKER, "[REFLECTION_START]")
    collapsed = collapsed.replace(END_MARKER, "[REFLECTION_END]")

    escaped = []
    for char in collapsed:
        if char in "\\`*_[]":
            escaped.append("\\" + char)
        else:
            escaped.append(char)
    return "".join(escaped)


def build_blockquote(quote: str) -> str:
    safe_quote = sanitize_quote(quote)
    return f'> *"{safe_quote}"*'


def update_readme(readme_path: Path, blockquote_line: str) -> bool:
    content = read_utf8(readme_path)

    start_index = content.find(START_MARKER)
    end_index = content.find(END_MARKER)

    if start_index == -1 or end_index == -1:
        raise ReflectionError(
            f"Missing reflection markers in {readme_path}. Expected both {START_MARKER} and {END_MARKER}."
        )
    if start_index > end_index:
        raise ReflectionError(
            f"Invalid reflection markers order in {readme_path}: start marker appears after end marker."
        )

    start_content_index = start_index + len(START_MARKER)
    new_middle = f"\n{blockquote_line}\n"

    if content[start_content_index:end_index] == new_middle:
        return False

    updated = content[:start_content_index] + new_middle + content[end_index:]
    readme_path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    root = repo_root()
    readme_path = root / "README.md"
    reflections_path = root / "reflections.json"

    quotes = load_quotes(reflections_path)
    today_quote = quote_for_today(quotes)
    blockquote_line = build_blockquote(today_quote)
    changed = update_readme(readme_path, blockquote_line)

    if changed:
        print(f"Updated reflection in {readme_path}.")
    else:
        print("Reflection already up to date. No changes made.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReflectionError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
