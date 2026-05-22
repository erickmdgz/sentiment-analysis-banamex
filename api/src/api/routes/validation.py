"""Router de validación: `/validation` y `/validation/coverage`.

`/validation` agrega métricas sobre todos los archivos cargados. `/coverage`
reporta cobertura de objetivos NPS vs sucursales detectadas (`01 §4`).
"""

from __future__ import annotations

from core.models_db import BranchTarget, Verbalization
from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select, text
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models_api import CoverageSummary, UserInfo, ValidationSummary

router = APIRouter(prefix="/validation", tags=["validation"])


@router.get("", response_model=ValidationSummary)
def validation(
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> ValidationSummary:
    """Agrega `ValidationSummary` sobre la totalidad de archivos en `files`."""
    files_row = session.execute(
        text(
            """
            SELECT
                COUNT(*) AS files_processed,
                COALESCE(SUM(rows_total), 0) AS rows_loaded,
                COALESCE(SUM(rows_inserted), 0) AS rows_new,
                COALESCE(SUM(rows_duplicated), 0) AS rows_dup,
                COALESCE(SUM(rows_invalid), 0) AS rows_invalid
            FROM files
            """
        )
    ).one()
    files_processed = int(files_row[0])
    rows_loaded = int(files_row[1])
    rows_new = int(files_row[2])
    rows_dup = int(files_row[3])
    rows_invalid = int(files_row[4])

    branches_detected = int(
        session.execute(
            select(func.count(distinct(Verbalization.branch_id)))
        ).scalar_one()
    )

    months_rows = session.execute(
        select(distinct(Verbalization.response_year), Verbalization.response_month)
    ).all()
    months = sorted({f"{int(y):04d}-{int(m):02d}" for y, m in months_rows})

    dates = session.execute(
        select(func.min(Verbalization.response_date), func.max(Verbalization.response_date))
    ).one()
    period: tuple[str, str] = (
        (str(dates[0]), str(dates[1])) if dates[0] and dates[1] else ("", "")
    )

    rows_empty_verbatim = int(
        session.execute(
            select(func.count()).select_from(Verbalization).where(
                Verbalization.has_verbatim == 0
            )
        ).scalar_one()
    )

    return ValidationSummary(
        files_processed=files_processed,
        rows_loaded=rows_loaded,
        rows_new=rows_new,
        rows_duplicated_ignored=rows_dup,
        branches_detected=branches_detected,
        period_available=period,
        months_available=months,
        columns_detected=[
            "record_id",
            "response_date",
            "nps_group",
            "nps_rate",
            "verbatim",
            "branch_id",
        ],
        rows_valid=rows_new + rows_dup,
        rows_empty_verbatim=rows_empty_verbatim,
        rows_invalid_nps=0,
        rows_missing_branch=0,
        rows_duplicate_record_id=rows_dup,
        rows_invalid_date=rows_invalid,
    )


@router.get("/coverage", response_model=CoverageSummary)
def coverage(
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> CoverageSummary:
    """Cobertura de objetivos: detectadas vs con target, sin responses, etc."""
    branches_detected_rows = session.execute(
        select(distinct(Verbalization.branch_id))
    ).scalars().all()
    branches_detected_set = {str(b) for b in branches_detected_rows}

    target_rows = session.execute(
        select(BranchTarget.branch_id, BranchTarget.nps_target_annual)
    ).all()
    targets = {str(r[0]): int(r[1]) for r in target_rows}
    branches_with_target = set(targets.keys())

    branches_without_target = sorted(branches_detected_set - branches_with_target)
    branches_with_target_no_responses = sorted(
        branches_with_target - branches_detected_set
    )
    invalid_targets = sorted(
        bid for bid, v in targets.items() if v is None or v < 0 or v > 100
    )

    return CoverageSummary(
        branches_detected=len(branches_detected_set),
        branches_with_target=len(branches_with_target),
        branches_without_target=branches_without_target,
        branches_with_target_no_responses=branches_with_target_no_responses,
        invalid_targets=invalid_targets,
        duplicate_targets=[],  # PRIMARY KEY en branch_targets impide duplicados.
    )
