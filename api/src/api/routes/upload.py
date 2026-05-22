"""Router de upload: `POST /upload`, `GET /upload/{file_id}/status`.

Recibe un `.txt` (TSV de Banamex), repite el pipeline M1 (parse → dedup), invoca
`engine.pipeline.classify_batch` para las filas nuevas y rellena
`metadata_extractions`. DTO `ClassificationResult` definido en `01 §4 / §7`.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core.loader import load_file
from engine.pipeline import classify_batch
from engine.ui_buckets import assign_ui_bucket
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..dtos import UploadResponse, UploadStatusResponse
from ..models_api import UserInfo, ValidationSummary

router = APIRouter(prefix="/upload", tags=["upload"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB (`00 §22`)
_READ_CHUNK = 64 * 1024


@router.post("", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> UploadResponse:
    """Sube un `.txt` y lo procesa (parse → dedup → clasifica).

    Devuelve `{file_id, validation_summary, already_processed}` (`01 §8`).
    """
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "detail": "Solo se aceptan archivos .txt.",
                "code": "invalid_extension",
                "hint": "El reto usa TSV con extensión .txt.",
            },
        )

    tmp_dir = Path(tempfile.gettempdir())
    tmp_path = tmp_dir / f"upload-{_safe_name(file.filename)}"
    total = 0
    try:
        with open(tmp_path, "wb") as out:
            while True:
                chunk = await file.read(_READ_CHUNK)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "detail": "Archivo demasiado grande (límite 50 MB).",
                            "code": "file_too_large",
                            "hint": f"Recibido al menos {total} bytes.",
                        },
                    )
                out.write(chunk)

        report = load_file(tmp_path)
        if not report.already_processed:
            _classify_and_persist(session, file_id=int(report.file_id))

        return UploadResponse(
            file_id=int(report.file_id),
            validation_summary=_validation_summary_for_file(
                session, file_id=int(report.file_id), report=report
            ),
            already_processed=bool(report.already_processed),
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


@router.get("/{file_id}/status", response_model=UploadStatusResponse)
def upload_status(
    file_id: int,
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> UploadStatusResponse:
    """Devuelve el estado de procesamiento. En el flujo síncrono actual: `done`."""
    row = session.execute(
        text("SELECT id FROM files WHERE id = :id"), {"id": file_id}
    ).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Archivo {file_id} no existe.",
                "code": "file_not_found",
            },
        )
    return UploadStatusResponse(
        file_id=file_id,
        status="done",
        progress=1.0,
        error=None,
    )


def _safe_name(filename: str) -> str:
    return "".join(c for c in filename if c.isalnum() or c in (".", "-", "_"))[:120]


def _validation_summary_for_file(
    session: Session, file_id: int, report
) -> ValidationSummary:
    """Construye `ValidationSummary` para un upload específico.

    En MVP, las métricas detalladas por tipo de invalidez no se desglosan a este
    nivel — se usa `rows_invalid` agregado del archivo. Los conteos por tipo
    (`rows_empty_verbatim`, etc.) se calculan vía consultas sobre la DB.
    """
    rows_invalid = int(report.rows_invalid)
    branches_detected = len(report.branches_detected)
    rows_empty_verbatim = int(
        session.execute(
            text(
                "SELECT COUNT(*) FROM verbalizations "
                "WHERE file_id = :fid AND has_verbatim = 0"
            ),
            {"fid": file_id},
        ).scalar_one()
    )
    return ValidationSummary(
        files_processed=1,
        rows_loaded=int(report.rows_total),
        rows_new=int(report.rows_inserted),
        rows_duplicated_ignored=int(report.rows_duplicated),
        branches_detected=branches_detected,
        period_available=tuple(report.date_range)
        if report.date_range and report.date_range[0]
        else ("", ""),
        months_available=list(report.months_available),
        columns_detected=[
            "record_id",
            "response_date",
            "nps_group",
            "nps_rate",
            "verbatim",
            "branch_id",
        ],
        rows_valid=int(report.rows_inserted) + int(report.rows_duplicated),
        rows_empty_verbatim=rows_empty_verbatim,
        rows_invalid_nps=0,  # Detalle desglosado no disponible (`MVP`).
        rows_missing_branch=0,
        rows_duplicate_record_id=int(report.rows_duplicated),
        rows_invalid_date=rows_invalid,
    )


def _classify_and_persist(session: Session, file_id: int) -> None:
    """Clasifica las filas recién insertadas y persiste classifications + metadata.

    Solo procesa registros que aún no tienen filas en `classifications` (idempotente
    si se vuelve a llamar para el mismo `file_id`).
    """
    rows = session.execute(
        text(
            """
            SELECT v.record_id, v.verbatim_clean, v.nps_group
            FROM verbalizations v
            LEFT JOIN classifications c ON c.record_id = v.record_id
            WHERE v.file_id = :fid AND c.id IS NULL
            """
        ),
        {"fid": file_id},
    ).all()
    if not rows:
        return

    items = [(str(r[0]), (r[1] or ""), str(r[2])) for r in rows]
    results = classify_batch(items)

    classification_params: list[dict] = []
    metadata_params: list[dict] = []
    for res in results:
        polarity = res["polarity"]
        for cat in res["categories"]:
            classification_params.append(
                {
                    "record_id": res["record_id"],
                    "l1_code": cat["l1_code"],
                    "l1_name": cat["l1_name"],
                    "l2_code": cat["l2_code"],
                    "l2_name": cat["l2_name"],
                    "l3_code": cat.get("l3_code"),
                    "l3_name": cat.get("l3_name"),
                    "confidence": float(cat["confidence"]),
                    # TODO: cambiar a 'classifier' cuando M2b reemplace al shim.
                    "source": "fallback"
                    if cat["confidence"] == 0.0
                    else "classifier",
                    "polarity": polarity,
                    "ui_bucket": assign_ui_bucket(cat["l1_code"]),
                }
            )
        meta = res["metadata"]
        metadata_params.append(
            {
                "record_id": res["record_id"],
                "personnel_named": 1 if meta["personnel_named"] else 0,
                "personnel_name": meta["personnel_name"],
                "personnel_polarity": meta["personnel_polarity"],
                "explicit_recommendation": meta["explicit_recommendation"],
                "mentions_other_bank": 1 if meta["mentions_other_bank"] else 0,
                "other_bank_names": json.dumps(meta["other_bank_names"]),
                "channels_mentioned": json.dumps(meta["channels_mentioned"]),
            }
        )

    if classification_params:
        session.execute(
            text(
                """
                INSERT INTO classifications (
                    record_id, l1_code, l1_name, l2_code, l2_name, l3_code, l3_name,
                    confidence, source, polarity, ui_bucket
                ) VALUES (
                    :record_id, :l1_code, :l1_name, :l2_code, :l2_name, :l3_code, :l3_name,
                    :confidence, :source, :polarity, :ui_bucket
                )
                """
            ),
            classification_params,
        )
    if metadata_params:
        session.execute(
            text(
                """
                INSERT OR REPLACE INTO metadata_extractions (
                    record_id, personnel_named, personnel_name, personnel_polarity,
                    explicit_recommendation, mentions_other_bank, other_bank_names,
                    channels_mentioned
                ) VALUES (
                    :record_id, :personnel_named, :personnel_name, :personnel_polarity,
                    :explicit_recommendation, :mentions_other_bank, :other_bank_names,
                    :channels_mentioned
                )
                """
            ),
            metadata_params,
        )
    session.commit()
