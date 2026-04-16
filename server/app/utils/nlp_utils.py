from __future__ import annotations

import re

# NLP Constants centralized from risk_knowledge_base and agent_service
NEGATION_CUES: tuple[str, ...] = (
    "不涉及",
    "未涉及",
    "不会",
    "不",
    "没有",
    "没",
    "无",
    "并非",
    "不是",
    "拒绝",
    "无需",
    "不用",
    "不要",
)

CLAUSE_DELIMITERS: tuple[str, ...] = (
    "，",
    ",",
    "；",
    ";",
    "。",
    "！",
    "!",
    "？",
    "?",
    "\n",
    "\r",
    "\t",
)

SENTENCE_DELIMITERS: tuple[str, ...] = (
    "。",
    "！",
    "!",
    "？",
    "?",
    "\n",
    "\r",
)

CONTRAST_CUES: tuple[str, ...] = (
    "但是",
    "但",
    "不过",
    "然而",
    "而是",
    "却",
)

def normalize_text(text: str) -> str:
    """Standardize text for matching."""
    return text.strip().lower().replace(" ", "")

def get_span(text: str, start: int, delimiters: tuple[str, ...]) -> tuple[int, int]:
    """Find the boundaries of a text segment defined by delimiters."""
    left = 0
    for index in range(start - 1, -1, -1):
        if text[index] in delimiters:
            left = index + 1
            break
    right = len(text)
    for index in range(start, len(text)):
        if text[index] in delimiters:
            right = index
            break
    return left, right

def get_clause_span(text: str, start: int) -> tuple[int, int]:
    return get_span(text, start, CLAUSE_DELIMITERS)

def get_sentence_span(text: str, start: int) -> tuple[int, int]:
    return get_span(text, start, SENTENCE_DELIMITERS)

def is_negated_occurrence(text: str, start: int, term_len: int) -> bool:
    """Check if a term occurrence at a given position is negated."""
    clause_start, clause_end = get_clause_span(text, start)
    left_clause = text[clause_start:start]
    right_clause = text[start + term_len:clause_end]

    # Check left side for negation cues within a window
    negation_scope = left_clause[-12:]
    if any(cue in negation_scope for cue in CONTRAST_CUES):
        return False

    if any(cue in negation_scope for cue in NEGATION_CUES):
        return True

    # Check right side for immediate negation
    if any(right_clause.startswith(cue) for cue in ("没有", "没", "未", "不")):
        return True

    return False

def get_sentence_polarity(text: str, term: str) -> tuple[set[int], set[int]]:
    """Find affirmative and negated sentence start positions for a term."""
    affirmative_sentences: set[int] = set()
    negated_sentences: set[int] = set()

    if not term:
        return affirmative_sentences, negated_sentences

    start = 0
    while True:
        index = text.find(term, start)
        if index == -1:
            break

        sentence_start, _ = get_sentence_span(text, index)
        if is_negated_occurrence(text, index, len(term)):
            negated_sentences.add(sentence_start)
        else:
            affirmative_sentences.add(sentence_start)

        start = index + len(term)

    return affirmative_sentences, negated_sentences

def contains_affirmative(text: str, term: str) -> bool:
    pos, neg = get_sentence_polarity(text, term)
    return bool(pos - neg)

def contains_negated(text: str, term: str) -> bool:
    _, neg = get_sentence_polarity(text, term)
    return bool(neg)
