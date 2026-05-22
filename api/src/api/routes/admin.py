"""Router de administración (POC, solo lectura).

`/admin/files` lista los archivos cargados. `/admin/runs` une `annotation_runs`
y `classifier_runs` para trazabilidad.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..dtos import (
    AnnotationRunRecord,
    ClassifierRunRecord,
    FileRecord,
    RunsResponse,
)
from ..models_api import UserInfo

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/files", response_model=list[FileRecord])
def list_files(
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[FileRecord]:
    rows = session.execute(
        text(
            """
            SELECT id, filename, sha256, rows_inserted, uploaded_at
            FROM files
            ORDER BY uploaded_at DESC
            """
        )
    ).all()
    return [
        FileRecord(
            id=int(r[0]),
            filename=str(r[1]),
            sha256=str(r[2]),
            rows_inserted=int(r[3]),
            uploaded_at=str(r[4]),
        )
        for r in rows
    ]


@router.get("/runs", response_model=RunsResponse)
def list_runs(
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> RunsResponse:
    ann_rows = session.execute(
        text(
            """
            SELECT id, sample_size, model, started_at, finished_at,
                   runtime_seconds, status
            FROM annotation_runs
            ORDER BY started_at DESC
            """
        )
    ).all()
    clf_rows = session.execute(
        text(
            """
            SELECT id, model_path, trained_on_run_id, trained_at,
                   n_samples, n_labels, f1_micro, f1_macro, hamming_loss
            FROM classifier_runs
            ORDER BY trained_at DESC
            """
        )
    ).all()
    annotation_runs = [
        AnnotationRunRecord(
            id=int(r[0]),
            sample_size=int(r[1]),
            model=str(r[2]),
            started_at=str(r[3]),
            finished_at=str(r[4]) if r[4] is not None else None,
            runtime_seconds=float(r[5]) if r[5] is not None else None,
            status=str(r[6]),
        )
        for r in ann_rows
    ]
    classifier_runs = [
        ClassifierRunRecord(
            id=int(r[0]),
            model_path=str(r[1]),
            trained_on_run_id=int(r[2]) if r[2] is not None else None,
            trained_at=str(r[3]),
            n_samples=int(r[4]),
            n_labels=int(r[5]),
            f1_micro=float(r[6]) if r[6] is not None else None,
            f1_macro=float(r[7]) if r[7] is not None else None,
            hamming_loss=float(r[8]) if r[8] is not None else None,
        )
        for r in clf_rows
    ]
    return RunsResponse(
        annotation_runs=annotation_runs,
        classifier_runs=classifier_runs,
    )
