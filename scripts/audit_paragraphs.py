#!/usr/bin/env python3
"""Audit and, with --apply, split overlong reading paragraphs at sentence ends.

The reviewed JSON files are the source of truth.  This script only inserts
paragraph breaks; it never changes, adds or removes words.  Rich inline markup
(italics and bold) is carried across a split and reopened on the next paragraph.

Usage:
    python3 scripts/audit_paragraphs.py
    python3 scripts/audit_paragraphs.py --apply
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXTS = ROOT / "reading_texts"
TAG_RE = re.compile(r"</?(i|b|em|strong)>|<br\s*/?>", re.IGNORECASE)

ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "st", "no", "rev", "col", "gen", "capt", "hon",
    "jr", "sr", "esq", "viz", "cf", "pp", "vol", "ch", "sec", "art", "fig",
    "al", "etc", "e.g", "i.e", "lt", "ltd", "messrs", "mme", "mlle", "prof",
    "gov", "sen", "rep", "pres", "supt", "dept", "univ",
}


def sentence_ends(text: str) -> list[int]:
    """Return offsets just after sentence-final punctuation."""
    ends: list[int] = []
    length = len(text)
    for index, char in enumerate(text):
        if char not in ".!?":
            continue
        if char == ".":
            if (index and text[index - 1] == ".") or (
                index + 1 < length and text[index + 1] == "."
            ):
                continue
            if (
                index and index + 1 < length
                and text[index - 1].isdigit() and text[index + 1].isdigit()
            ):
                continue
            match = re.search(r"([A-Za-z][A-Za-z.]*)$", text[:index])
            if match:
                word = match.group(1)
                if word.lower() in ABBREVIATIONS or (
                    len(word) == 1 and word.isupper()
                ):
                    continue
        end = index + 1
        while end < length and text[end] in "”’\"')]}":
            end += 1
        if end < length and not text[end].isspace():
            continue
        after = end
        while after < length and text[after].isspace():
            after += 1
        if after < length and (text[after].isupper() or text[after] in "“\"‘'"):
            ends.append(end)
    return ends


def split_points(text: str, target: int, minimum: int, maximum: int) -> list[int]:
    if len(text) <= maximum:
        return []
    ends = sentence_ends(text)
    points: list[int] = []
    start = 0
    while len(text) - start > maximum:
        candidates = [
            end for end in ends
            if start + minimum < end <= start + maximum
        ]
        if not candidates:
            candidates = [end for end in ends if end > start + minimum]
            if not candidates:
                break
        point = min(candidates, key=lambda end: abs(end - (start + target)))
        if point <= start:
            break
        points.append(point)
        start = point
    return points


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def plain_from_markup(markup: str) -> str:
    return normalize(re.sub(r"<[^>]+>", "", html.unescape(markup)))


def tokenize(markup: str):
    markup = html.unescape(markup)
    tokens: list[tuple[str, str, int, int]] = []
    plain = 0
    pos = 0
    for match in TAG_RE.finditer(markup):
        if match.start() > pos:
            segment = markup[pos:match.start()]
            tokens.append(("text", segment, plain, plain + len(segment)))
            plain += len(segment)
        tag = match.group(0)
        if tag.startswith("<br"):
            normalized = "<br/>"
        else:
            name = "b" if match.group(1).lower() in ("b", "strong") else "i"
            normalized = f"</{name}>" if tag.startswith("</") else f"<{name}>"
        tokens.append(("tag", normalized, plain, plain))
        pos = match.end()
    if pos < len(markup):
        segment = markup[pos:]
        tokens.append(("text", segment, plain, plain + len(segment)))
        plain += len(segment)
    return tokens, plain


def open_stack_at(tokens, position: int) -> list[str]:
    stack: list[str] = []
    for kind, value, start, _ in tokens:
        if kind != "tag":
            continue
        if start < position:
            if value.startswith("</"):
                if stack:
                    stack.pop()
            elif not value.startswith("<br"):
                stack.append(value[1])
        elif start == position and value.startswith("</"):
            if stack:
                stack.pop()
    return stack


def split_markup(markup: str, points: list[int]) -> list[str]:
    tokens, plain_length = tokenize(markup)
    bounds = [0] + points + [plain_length]
    segments: list[str] = []
    for start, end in zip(bounds, bounds[1:]):
        if start >= end:
            continue
        stack = open_stack_at(tokens, start)
        out = [f"<{name}>" for name in stack]
        for kind, value, token_start, token_end in tokens:
            if kind == "text":
                low = max(start, token_start)
                high = min(end, token_end)
                if low < high:
                    out.append(value[low - token_start:high - token_start])
            elif value.startswith("</"):
                if start < token_start <= end:
                    out.append(value)
                    if stack:
                        stack.pop()
            elif value.startswith("<br"):
                if start <= token_start < end:
                    out.append(value)
            else:
                if start <= token_start < end:
                    out.append(value)
                    stack.append(value[1])
        out.extend(f"</{name}>" for name in reversed(stack))
        segment = normalize("".join(out))
        if segment:
            segments.append(segment)
    return segments


def split_element(element: dict, target: int, minimum: int, maximum: int):
    text = normalize(element.get("text", ""))
    if len(text) <= maximum:
        return [element]
    points = split_points(text, target, minimum, maximum)
    if not points:
        return [element]
    markup = element.get("markup") or text
    segments = split_markup(markup, points)
    if len(segments) < 2:
        return [element]
    new_elements = []
    for segment in segments:
        item = dict(element)
        item["markup"] = segment
        item["text"] = plain_from_markup(segment)
        new_elements.append(item)
    before = re.sub(r"\s+", " ", " ".join(plain_from_markup(e.get("markup") or e["text"]) for e in new_elements)).strip()
    if before != text:
        raise ValueError(f"paragraph split changed text: {text[:80]!r}")
    return new_elements


def run(apply: bool, target: int, minimum: int, maximum: int) -> None:
    report = []
    files = sorted(TEXTS.glob("[0-9][0-9]_*.json"))
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        new_elements = []
        changes = []
        for index, element in enumerate(data["elements"]):
            if element["kind"] != "paragraph":
                new_elements.append(element)
                continue
            parts = split_element(element, target, minimum, maximum)
            if len(parts) > 1:
                changes.append(
                    {
                        "element": index,
                        "before_chars": len(normalize(element["text"])),
                        "after_chars": [len(normalize(part["text"])) for part in parts],
                        "first_words": [normalize(part["text"])[:80] for part in parts],
                    }
                )
                new_elements.extend(parts)
            else:
                new_elements.append(element)
        if changes:
            data["elements"] = new_elements
            if apply:
                path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        report.append(
            {
                "number": data["number"],
                "title": data["title"],
                "paragraphs_before": sum(1 for e in data["elements"] if e["kind"] == "paragraph") - sum(len(c["after_chars"]) - 1 for c in changes),
                "paragraphs_after": sum(1 for e in data["elements"] if e["kind"] == "paragraph"),
                "split_elements": changes,
            }
        )
        print(
            f'{data["number"]:02d} {data["title"][:45]:45s} '
            f'{report[-1]["paragraphs_before"]} -> {report[-1]["paragraphs_after"]} paragraphs',
            flush=True,
        )
    if apply:
        (TEXTS / "paragraph_audit.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {TEXTS / 'paragraph_audit.json'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the split paragraphs")
    parser.add_argument("--target", type=int, default=900)
    parser.add_argument("--minimum", type=int, default=400)
    parser.add_argument("--maximum", type=int, default=1200)
    args = parser.parse_args()
    run(args.apply, args.target, args.minimum, args.maximum)


if __name__ == "__main__":
    main()
