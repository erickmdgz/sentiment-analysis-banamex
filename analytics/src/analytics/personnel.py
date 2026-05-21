"""Menciones de personal por sucursal (M3).

Referencias: 05_M3 §Personnel mentions.
"""

from __future__ import annotations

from core.models_db import MetadataExtraction, Verbalization
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .schemas import PersonnelMention


def mentions(session: Session, branch_id: str) -> list[PersonnelMention]:
    """Agrega por (personnel_name, personnel_polarity) en la sucursal indicada.

    Cada fila incluye un `example_record_id` y `example_verbatim` con la primera
    mención de ese par (name, polarity) en la sucursal.
    """
    stmt = (
        select(
            MetadataExtraction.personnel_name,
            MetadataExtraction.personnel_polarity,
            func.count().label("c"),
        )
        .join(Verbalization, MetadataExtraction.record_id == Verbalization.record_id)
        .where(MetadataExtraction.personnel_named == 1)
        .where(Verbalization.branch_id == branch_id)
        .where(MetadataExtraction.personnel_name.is_not(None))
        .where(MetadataExtraction.personnel_polarity.is_not(None))
        .group_by(
            MetadataExtraction.personnel_name,
            MetadataExtraction.personnel_polarity,
        )
        .order_by(func.count().desc())
    )
    out: list[PersonnelMention] = []
    for row in session.execute(stmt).all():
        name = str(row[0])
        polarity = str(row[1])
        count = int(row[2])
        example = session.execute(
            select(
                MetadataExtraction.record_id,
                Verbalization.verbatim_clean,
            )
            .join(
                Verbalization, MetadataExtraction.record_id == Verbalization.record_id
            )
            .where(Verbalization.branch_id == branch_id)
            .where(MetadataExtraction.personnel_named == 1)
            .where(MetadataExtraction.personnel_name == name)
            .where(MetadataExtraction.personnel_polarity == polarity)
            .order_by(MetadataExtraction.record_id)
            .limit(1)
        ).first()
        if example is None:
            continue
        example_rid = str(example[0])
        example_verb = str(example[1] or "")
        if polarity not in {"pos", "neg"}:
            continue
        out.append(
            PersonnelMention(
                name=name,
                polarity=polarity,  # type: ignore[arg-type]
                count=count,
                example_record_id=example_rid,
                example_verbatim=example_verb,
            )
        )
    return out
