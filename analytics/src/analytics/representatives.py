"""Selección de comentarios representativos por bucket UI para una sucursal.

Referencias: 05_M3 §Comentarios representativos.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from core.models_db import Classification, Verbalization
from sqlalchemy import select
from sqlalchemy.orm import Session

from .schemas import RepresentativeComment

# Diccionario léxico canónico por bucket; declarado como constante para
# documentar la heurística aplicada en pick_representatives.
BUCKET_KEYWORDS: dict[str, frozenset[str]] = {
    "Atención del personal": frozenset(
        {"atención", "atendieron", "amable", "grosero", "actitud", "personal"}
    ),
    "Tiempos y espera": frozenset(
        {"espera", "fila", "turno", "demora", "tardanza"}
    ),
    "Sucursal física": frozenset(
        {"sucursal", "instalaciones", "limpieza", "estacionamiento", "espacio"}
    ),
    "Cajeros (ATM)": frozenset(
        {"cajero", "atm", "billetes", "máquina", "tarjeta"}
    ),
    "Canales digitales": frozenset(
        {"app", "netkey", "aplicación", "móvil", "internet"}
    ),
    "Productos y promociones": frozenset(
        {"producto", "promoción", "beneficio", "tarjeta", "crédito"}
    ),
    "Operaciones transaccionales": frozenset(
        {"depósito", "retiro", "transferencia", "pago", "operación"}
    ),
    "Costos": frozenset({"comisión", "costo", "cargo", "tarifa", "precio"}),
    "Aclaraciones, quejas y fraude": frozenset(
        {"aclaración", "queja", "fraude", "reclamo", "robo"}
    ),
    "Procesos y requisitos": frozenset(
        {"trámite", "papeleo", "requisitos", "burocracia", "proceso"}
    ),
}

_GROUP_POLARITY: dict[str, str] = {
    "Promotor": "pos",
    "Detractor": "neg",
}


@dataclass
class _Candidate:
    record_id: str
    verbatim: str
    nps_rate: int
    nps_group: str
    response_date: str
    length: int


def _percentile(values: list[int], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    rank = (pct / 100.0) * (len(sorted_vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = rank - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _lexical_match(text: str, keywords: Iterable[str]) -> bool:
    low = text.lower()
    return any(kw in low for kw in keywords)


def pick_representatives(
    session: Session, branch_id: str, n_per_topic: int = 2
) -> list[RepresentativeComment]:
    """Toma `n_per_topic` comentarios por bucket presente en la sucursal.

    Heurística:
      - longitud entre P25 y P75 de la distribución de longitudes;
      - polaridad de la classification consistente con el grupo NPS;
      - match léxico contra palabras canónicas del bucket.
    """
    verb_rows = session.execute(
        select(
            Verbalization.record_id,
            Verbalization.verbatim_clean,
            Verbalization.nps_rate,
            Verbalization.nps_group,
            Verbalization.response_date,
        ).where(Verbalization.branch_id == branch_id)
    ).all()
    if not verb_rows:
        return []
    lengths = [len(r[1] or "") for r in verb_rows]
    p25 = _percentile(lengths, 25.0)
    p75 = _percentile(lengths, 75.0)

    candidates: dict[str, _Candidate] = {}
    for row in verb_rows:
        rid = str(row[0])
        verbatim = row[1] or ""
        length = len(verbatim)
        if not verbatim or length < p25 or length > p75:
            continue
        candidates[rid] = _Candidate(
            record_id=rid,
            verbatim=verbatim,
            nps_rate=int(row[2]),
            nps_group=str(row[3]),
            response_date=str(row[4]),
            length=length,
        )

    if not candidates:
        return []

    # Cargar classifications de los record_ids candidatos
    class_rows = session.execute(
        select(
            Classification.record_id,
            Classification.ui_bucket,
            Classification.polarity,
        ).where(Classification.record_id.in_(list(candidates.keys())))
    ).all()

    by_bucket: dict[str, list[_Candidate]] = {}
    seen_in_bucket: dict[str, set[str]] = {}
    for cr in class_rows:
        rid = str(cr[0])
        bucket = str(cr[1])
        polarity = str(cr[2])
        cand = candidates.get(rid)
        if cand is None:
            continue
        expected_polarity = _GROUP_POLARITY.get(cand.nps_group)
        if expected_polarity is not None and polarity != expected_polarity:
            continue
        keywords = BUCKET_KEYWORDS.get(bucket)
        if keywords is None or not _lexical_match(cand.verbatim, keywords):
            continue
        seen = seen_in_bucket.setdefault(bucket, set())
        if rid in seen:
            continue
        seen.add(rid)
        by_bucket.setdefault(bucket, []).append(cand)

    out: list[RepresentativeComment] = []
    for bucket, cands in by_bucket.items():
        # Orden estable por record_id para reproducibilidad.
        cands.sort(key=lambda c: c.record_id)
        for cand in cands[:n_per_topic]:
            # nps_group viene como str en SQLAlchemy; Pydantic exige el Literal.
            group = cand.nps_group
            if group not in {"Promotor", "Pasivo", "Detractor"}:
                continue
            out.append(
                RepresentativeComment(
                    record_id=cand.record_id,
                    verbatim=cand.verbatim,
                    nps_rate=cand.nps_rate,
                    nps_group=group,  # type: ignore[arg-type]
                    response_date=cand.response_date,
                    bucket=bucket,
                )
            )
    return out
