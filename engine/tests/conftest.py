"""Configuración compartida de pytest para M2a.

Inserta `src/` en `sys.path` para que `import engine.<modulo>` funcione sin
necesidad de hacer `pip install -e ./engine` antes de correr los tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

# engine/tests/conftest.py → engine/src
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
