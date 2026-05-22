#!/usr/bin/env python3
"""Atajo para máquinas que no van a correr el preprocess.

Descomprime `data/processed/banamex.db.gz` a `data/processed/banamex.db`.
El `.gz` se genera manualmente por el equipo tras el primer preprocess
exitoso y se distribuye fuera de banda (no en git por tamaño).
"""

from __future__ import annotations

import gzip
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GZ_PATH = REPO_ROOT / "data" / "processed" / "banamex.db.gz"
DB_PATH = REPO_ROOT / "data" / "processed" / "banamex.db"


def main() -> int:
    if not GZ_PATH.exists():
        print(f"ERROR: No existe {GZ_PATH}.", file=sys.stderr)
        print(
            "        Opciones:\n"
            "        1) Ejecuta `python scripts/preprocess_corpora.py` (~4-7 horas).\n"
            "        2) Descarga `banamex.db.gz` del entregable del equipo y "
            "colócalo en data/processed/.",
            file=sys.stderr,
        )
        return 1

    if DB_PATH.exists():
        size_mb = DB_PATH.stat().st_size / 1e6
        print(f"DB ya existe en {DB_PATH} ({size_mb:.1f} MB).")
        print("Bórrala manualmente si quieres re-extraer desde el .gz.")
        return 0

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(GZ_PATH, "rb") as src, open(DB_PATH, "wb") as dst:
        shutil.copyfileobj(src, dst)
    size_mb = DB_PATH.stat().st_size / 1e6
    print(f"✓ DB extraída en {DB_PATH} ({size_mb:.1f} MB).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
