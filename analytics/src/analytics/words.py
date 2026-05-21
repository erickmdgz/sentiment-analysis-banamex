"""Frecuencias léxicas para wordcloud por sucursal (M3).

Referencias: 05_M3 §Top words.
"""

from __future__ import annotations

import re
from collections import Counter
from importlib.resources import files
from typing import Literal

from core.models_db import Verbalization
from sqlalchemy import select
from sqlalchemy.orm import Session

from .schemas import WordFrequency

_TOKEN_RE = re.compile(r"\b[a-záéíóúñü]{3,}\b")

_STOPWORDS_CACHE: frozenset[str] | None = None


def _load_stopwords() -> frozenset[str]:
    global _STOPWORDS_CACHE
    if _STOPWORDS_CACHE is not None:
        return _STOPWORDS_CACHE
    resource = files("analytics").joinpath("data/stopwords_es_banking.txt")
    raw = resource.read_text(encoding="utf-8")
    words: set[str] = set()
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        words.add(line.lower())
    _STOPWORDS_CACHE = frozenset(words)
    return _STOPWORDS_CACHE


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def top_words(
    session: Session,
    branch_id: str,
    group: Literal["Promotor", "Pasivo", "Detractor"] | None = None,
    top_n: int = 30,
) -> list[WordFrequency]:
    """Top palabras en `verbatim_clean` de la sucursal (excluye stopwords).

    Si `group` es None considera todos los grupos NPS.
    """
    stopwords = _load_stopwords()
    stmt = select(Verbalization.verbatim_clean).where(
        Verbalization.branch_id == branch_id
    )
    if group is not None:
        stmt = stmt.where(Verbalization.nps_group == group)
    rows = session.execute(stmt).scalars().all()
    counter: Counter[str] = Counter()
    for text in rows:
        if not text:
            continue
        for token in _tokenize(text):
            if token in stopwords:
                continue
            counter[token] += 1
    return [
        WordFrequency(word=word, count=count, group=group)
        for word, count in counter.most_common(top_n)
    ]
