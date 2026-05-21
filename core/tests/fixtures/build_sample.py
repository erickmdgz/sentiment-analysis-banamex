"""Generador determinístico de ``sample.tsv`` (100 filas sintéticas latin-1).

Ejecutar desde la raíz del repo:

    .venv/bin/python core/tests/fixtures/build_sample.py

NO contiene datos reales de Banamex: las verbalizaciones son frases genéricas
escritas a propósito para este fixture. El schema y el encoding coinciden con
los corpora reales (6 columnas TAB, latin-1, fechas DD/MM/YYYY).
"""

from __future__ import annotations

import csv
import io
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).parent / "sample.tsv"

VERBATIMS_DETRACTOR = [
    "La atención fue muy lenta y el cajero automático no funcionaba.",
    "Esperé más de 30 minutos para una operación simple, pésimo servicio.",
    "Mala experiencia: no resolvieron mi aclaración después de tres visitas.",
    "El personal no estaba capacitado para atender mi caso, María fue grosera.",
    "Cobraron una comisión que no debía pagar y no aceptaron corregirla.",
    "El cajero se tragó mi tarjeta y nadie pudo ayudarme.",
]
VERBATIMS_PASIVO = [
    "La sucursal está bien pero a veces hay filas largas.",
    "Servicio promedio, sin novedad.",
    "Cumplió con lo básico, nada destacable en la atención.",
    "Atención correcta aunque mejorable en tiempos de espera.",
    "Está OK, podría mejorar la señalización dentro de la sucursal.",
]
VERBATIMS_PROMOTOR = [
    "Excelente atención de María en caja, muy amable y eficiente.",
    "Resolvieron mi situación rápido y con muy buen trato.",
    "Sucursal limpia, personal atento. Muy recomendable, la mejor de la ciudad.",
    "El gerente Juan se portó muy profesional, resolvió todo en minutos.",
    "Súper recomendable, gran atención de Carlos y todo el equipo.",
]


def _group_for(rate: int) -> tuple[str, list[str]]:
    if rate <= 6:
        return "Detractor", VERBATIMS_DETRACTOR
    if rate <= 8:
        return "Pasivo", VERBATIMS_PASIVO
    return "Promotor", VERBATIMS_PROMOTOR


def build_rows() -> list[list[str]]:
    rng = random.Random(2025)
    base = date(2025, 1, 1)
    rows: list[list[str]] = []
    for i in range(1, 101):
        record_id = f"REC-{i:06d}"
        d = base + timedelta(days=rng.randint(0, 150))
        date_str = d.strftime("%d/%m/%Y")
        rate = rng.randint(0, 10)
        grp, options = _group_for(rate)
        verbatim = "" if rng.random() < 0.15 else rng.choice(options)
        # Distribución de branch_ids: ~20 sucursales, algunas con muchas y otras con pocas
        branch_id = f"A-{rng.choice([100, 101, 102, 103, 104, 105, 200, 201, 202, 300, 301, 302, 400, 500, 600, 700, 800, 900, 901, 902])}"
        rows.append([record_id, date_str, grp, str(rate), verbatim, branch_id])
    return rows


def main() -> None:
    rows = build_rows()
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter="\t", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    for row in rows:
        writer.writerow(row)
    OUT.write_bytes(buf.getvalue().encode("latin-1"))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(rows)} rows)")


if __name__ == "__main__":
    main()
