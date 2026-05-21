"""Generador determinístico del fixture verbalizations.csv.

Se ejecuta una sola vez para producir el CSV; se commitea el resultado.
Si los tests requieren más volumen o un mix distinto, se regenera con
`python engine/tests/fixtures/generate_verbalizations.py`.

Reglas:
- ~200 filas en total.
- Cobertura: 16 meses (enero 2025 a abril 2026).
- Mix por nps_group respetando ±5%: 35% Detractor, 25% Pasivo, 40% Promotor.
- Verbalizaciones sintéticas en español mexicano cortas y realistas.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

random.seed(20260521)

DETRACTOR_TEMPLATES = [
    "El servicio fue muy lento y la fila no avanzaba.",
    "El gerente fue grosero conmigo, no recomiendo esta sucursal.",
    "No me resolvieron el problema, llevo tres visitas.",
    "El cajero automático no funciona desde la semana pasada.",
    "La app no me deja transferir, NetKey siempre falla.",
    "Esperé más de dos horas para una aclaración de cargo.",
    "Cobros no reconocidos en mi tarjeta y nadie me ayuda.",
    "Mala actitud del personal de ventanilla, no lo recomiendo.",
    "Los requisitos para el crédito son excesivos y burocráticos.",
    "Las comisiones que me cobran son altísimas e injustas.",
    "En México tardan mucho en atender, prefiero BBVA.",
    "Reporté un fraude y no me dieron seguimiento, terrible.",
    "La sucursal está sucia y mal cuidada, da mala impresión.",
    "El cajero retuvo mi tarjeta y nadie sabe nada.",
    "No respetaron mi turno, me adelantaron a tres personas.",
    "El asesor no sabía nada del producto que me ofrecía.",
    "Promoción engañosa, terminé pagando más comisiones.",
    "Pésimo trato en el call center, me cuelgan.",
    "Demasiados trámites para algo tan simple, vueltas innecesarias.",
    "La página web siempre está caída cuando la necesito.",
]

PASSIVE_TEMPLATES = [
    "El servicio fue regular, nada especial.",
    "La atención fue normal, esperé un poco.",
    "Pude hacer mi operación, aunque tomó tiempo.",
    "El personal me atendió, pero sin mucho entusiasmo.",
    "La app funcionó esta vez, antes había tenido problemas.",
    "Encontré estacionamiento aunque la sucursal estaba llena.",
    "Cumplió con lo necesario, sin sobresalir.",
    "Me dieron información, podría haber sido más clara.",
    "El cajero funcionó pero solo dispensaba billetes de mayor denominación.",
    "Hice mi transferencia sin problemas, esperando que mejore la app.",
]

PROMOTER_TEMPLATES = [
    "La srita Diana fue muy amable y resolvió mis dudas, lo recomiendo.",
    "El gerente Roberto me atendió excelente, muy profesional.",
    "Atención rápida y eficiente, sin filas.",
    "La cajera Ana fue muy cordial y paciente, gracias.",
    "Excelente servicio en la app, todo funciona bien.",
    "El ejecutivo Mateo me explicó claramente todas las opciones.",
    "Sucursal limpia, ordenada y con personal amable.",
    "Resolvieron mi aclaración en menos de una hora, excelente.",
    "Buena atención telefónica, la asesora Carmen muy paciente.",
    "Recomiendo ampliamente esta sucursal, atención de primera.",
    "Lo recomiendo, la atención es mejor que en BBVA o Santander.",
    "El cajero automático funciona perfecto y siempre tiene billetes.",
    "Trámite ágil para abrir mi cuenta, salí en 15 minutos.",
    "Los puntos los pude canjear sin problema, todo claro.",
    "El portal web responde rápido, hago mis transferencias en segundos.",
    "Personal capacitado, me asesoró bien sobre mi crédito.",
]

MONTHS = [
    (2025, m) for m in range(1, 13)
] + [(2026, m) for m in range(1, 5)]


def _rate_for_group(group: str, rng: random.Random) -> int:
    if group == "Detractor":
        return rng.randint(0, 6)
    if group == "Pasivo":
        return rng.randint(7, 8)
    return rng.randint(9, 10)


def _branch_id(rng: random.Random) -> str:
    return f"A-{rng.randint(1, 99):04d}"


def main() -> None:
    rng = random.Random(20260521)

    out_path = Path(__file__).parent / "verbalizations.csv"

    rows: list[dict[str, object]] = []

    targets = {
        "Detractor": 70,  # 35%
        "Pasivo": 50,  # 25%
        "Promotor": 80,  # 40%
    }
    templates = {
        "Detractor": DETRACTOR_TEMPLATES,
        "Pasivo": PASSIVE_TEMPLATES,
        "Promotor": PROMOTER_TEMPLATES,
    }

    record_counter = 1
    for group, total in targets.items():
        # Distribuir uniformemente entre los 16 meses (algunos meses repiten).
        per_month = total // len(MONTHS)
        extras = total - per_month * len(MONTHS)
        for i, (year, month) in enumerate(MONTHS):
            count = per_month + (1 if i < extras else 0)
            for _ in range(count):
                tpl = rng.choice(templates[group])
                row = {
                    "record_id": f"R{record_counter:05d}",
                    "response_date": f"{year:04d}-{month:02d}-{rng.randint(1, 28):02d}",
                    "response_year": year,
                    "response_month": month,
                    "nps_group": group,
                    "nps_rate": _rate_for_group(group, rng),
                    "verbatim": tpl,
                    "verbatim_clean": tpl,
                    "branch_id": _branch_id(rng),
                    "has_verbatim": 1,
                }
                rows.append(row)
                record_counter += 1

    # Añadir 3 verbalizaciones vacías para verificar filtros del muestreo.
    for _ in range(3):
        year, month = rng.choice(MONTHS)
        rows.append(
            {
                "record_id": f"R{record_counter:05d}",
                "response_date": f"{year:04d}-{month:02d}-{rng.randint(1, 28):02d}",
                "response_year": year,
                "response_month": month,
                "nps_group": rng.choice(("Detractor", "Pasivo", "Promotor")),
                "nps_rate": rng.randint(0, 10),
                "verbatim": "",
                "verbatim_clean": "",
                "branch_id": _branch_id(rng),
                "has_verbatim": 0,
            }
        )
        record_counter += 1

    fieldnames = list(rows[0].keys())
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows → {out_path}")


if __name__ == "__main__":
    main()
