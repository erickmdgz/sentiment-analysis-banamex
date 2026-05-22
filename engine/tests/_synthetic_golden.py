"""Helpers compartidos: golden set sintético determinístico para tests M2b.

Construye una DB SQLite temporal con `core/schema.sql`, inserta una corrida
de anotación falsa y 200 verbalizaciones con sus etiquetas L2 distribuidas
entre 5 buckets temáticos claramente separables (atención, espera, sucursal
física, ATM, app). Suficiente para que `LogisticRegression` aprenda y produzca
`f1_micro > 0.4` sin tener que llamar al LLM real.

Lo usan: `test_trainer.py`, `test_classifier.py`, `test_pipeline.py`.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, text

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "core" / "src" / "core" / "schema.sql"


LABEL_TEXTS: dict[str, list[str]] = {
    "1.1": [
        "el personal fue muy amable y atento",
        "la atención del ejecutivo fue excelente",
        "muy buena atención al cliente, me ayudaron rápido",
        "el cajero fue cortés y profesional",
        "trato amable y servicio impecable",
        "personal atento, me resolvieron todo",
        "la gerente fue muy amable conmigo",
        "el ejecutivo nos atendió con paciencia",
        "amabilidad del personal de la sucursal",
        "buen trato, recibí ayuda inmediata",
    ],
    "2.1": [
        "la fila fue interminable, esperé más de una hora",
        "demasiado tiempo de espera en la sucursal",
        "esperé mucho rato para ser atendido",
        "tiempos de espera larguísimos",
        "tardaron mucho en atenderme, demasiada fila",
        "la espera fue eterna, perdí toda la mañana",
        "muy lentos atendiendo, pésimo tiempo",
        "fila enorme y poco personal",
        "esperar tanto tiempo es injustificable",
        "demoras excesivas en la operación",
    ],
    "3.1": [
        "la sucursal está muy limpia y ordenada",
        "instalaciones cómodas y bien mantenidas",
        "buena sucursal, agradable y limpia",
        "la oficina tiene buen ambiente y espacio",
        "sucursal con buena iluminación y aseo",
        "instalaciones modernas y limpias",
        "el lugar está bien cuidado",
        "sucursal cómoda con aire acondicionado",
        "espacio físico agradable",
        "la sucursal se ve limpia y nueva",
    ],
    "4.1": [
        "el cajero automático estaba descompuesto",
        "el atm no me dio mi dinero",
        "cajero automático sin servicio",
        "el atm se quedó con mi tarjeta",
        "no servían los cajeros automáticos",
        "atm sin efectivo, muy mal",
        "el cajero automático tragó mi dinero",
        "todos los atm fuera de servicio",
        "cajero automático con falla técnica",
        "atm bloqueado y no pude retirar",
    ],
    "5.1": [
        "la app no funciona, no puedo entrar",
        "la aplicación móvil se cae todo el tiempo",
        "no me deja iniciar sesión en la app",
        "muy mala experiencia con la aplicación",
        "la app tarda mucho en cargar",
        "errores constantes en la aplicación móvil",
        "no puedo hacer transferencias en la app",
        "aplicación pésima, llena de bugs",
        "no carga la app del banco",
        "la app móvil no responde",
    ],
}


def make_synthetic_records() -> list[tuple[str, str, list[str]]]:
    """200 records: 40 por etiqueta. Cada record tiene sólo su label."""
    out: list[tuple[str, str, list[str]]] = []
    counter = 0
    for label, samples in LABEL_TEXTS.items():
        for variation in range(4):
            for base in samples:
                counter += 1
                rid = f"R{counter:05d}"
                text_variant = base if variation == 0 else f"{base} ({variation})"
                out.append((rid, text_variant, [label]))
    return out


def init_sqlite(db_path: Path) -> Engine:
    """Crea un engine SQLite y aplica `core/schema.sql` literalmente."""
    engine = create_engine(f"sqlite:///{db_path}")
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    return engine


def seed_golden_set(
    engine: Engine, records: list[tuple[str, str, list[str]]]
) -> int:
    """Inserta files / annotation_runs / verbalizations / classifications.

    Cada classification queda con `source='llm_annotation'` para que el
    trainer la reconozca como golden set.
    """
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO files (id, filename, sha256, rows_total, rows_inserted, "
                "rows_duplicated, rows_invalid, uploaded_at) "
                "VALUES (1, 'fixture.tsv', 'fixturehash', :n, :n, 0, 0, '2025-01-01')"
            ),
            {"n": len(records)},
        )
        conn.execute(
            text(
                "INSERT INTO annotation_runs (id, sample_size, model, started_at, "
                "finished_at, runtime_seconds, status) "
                "VALUES (1, :n, 'qwen2.5:7b-instruct', '2025-01-01', '2025-01-01', 1.0, 'done')"
            ),
            {"n": len(records)},
        )
        for record_id, verbatim, labels in records:
            conn.execute(
                text(
                    "INSERT INTO verbalizations "
                    "(record_id, file_id, response_date, response_year, response_month, "
                    " nps_group, nps_rate, verbatim, verbatim_clean, branch_id, has_verbatim) "
                    "VALUES (:rid, 1, '2025-01-15', 2025, 1, 'Detractor', 5, :v, :v, 'A-0001', 1)"
                ),
                {"rid": record_id, "v": verbatim},
            )
            for label in labels:
                l1, _ = label.split(".")
                conn.execute(
                    text(
                        "INSERT INTO classifications "
                        "(record_id, l1_code, l1_name, l2_code, l2_name, l3_code, l3_name, "
                        " confidence, source, polarity, ui_bucket) VALUES "
                        "(:rid, :l1, :l1n, :l2, :l2n, NULL, NULL, 0.9, 'llm_annotation', "
                        " 'neg', 'Otros')"
                    ),
                    {
                        "rid": record_id,
                        "l1": l1,
                        "l1n": f"L1 {l1}",
                        "l2": label,
                        "l2n": f"L2 {label}",
                    },
                )
    return len(records)
