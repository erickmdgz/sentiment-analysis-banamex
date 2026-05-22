"""Script ejecutable: `python -m api.export_openapi`.

Genera `api/openapi.json` desde la app FastAPI. Lo consume M5 para regenerar el
cliente TS con `openapi-typescript` (`01 §10`).

NOTA: el script vive en `api/` (no en `api/src/api/`) por compatibilidad con el
contrato declarado en `01 §1` ("api/export_openapi.py"). El paquete `api`
provee también `api/src/api/export_openapi.py` con la misma lógica para que
`python -m api.export_openapi` funcione tras `pip install -e ./api`.
"""

from __future__ import annotations

import json
from pathlib import Path

from api.main import app


def main() -> None:
    out_path = Path(__file__).resolve().parent / "openapi.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(app.openapi(), f, indent=2, ensure_ascii=False)
    print(f"openapi.json escrito en {out_path}")


if __name__ == "__main__":
    main()
