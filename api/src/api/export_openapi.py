"""Variante invocable como `python -m api.export_openapi` (alias del script raíz).

Escribe `api/openapi.json` al lado del `pyproject.toml` del paquete.
Resuelve la ruta subiendo desde `api/src/api/` hasta `api/`.
"""

from __future__ import annotations

import json
from pathlib import Path

from .main import app


def main() -> None:
    pkg_root = Path(__file__).resolve().parents[2]  # api/
    out_path = pkg_root / "openapi.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(app.openapi(), f, indent=2, ensure_ascii=False)
    print(f"openapi.json escrito en {out_path}")


if __name__ == "__main__":
    main()
