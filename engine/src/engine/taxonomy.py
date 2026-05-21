"""Parseo de la taxonomía L1/L2/L3 desde docs/taxonomia_revisada.md.

Fuente única de verdad de la jerarquía. Consumido por `engine.annotator`
(para construir el SYSTEM_PROMPT) y por `engine.pipeline` (para hacer
lookup de nombres a partir de códigos).

Contrato (01_contratos_compartidos.md §7 y 03_M2a_anotador.md):
    - load_taxonomy() -> dict jerárquico
    - get_l2_name(l1_code, l2_code) -> str
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import TypedDict


class L2Node(TypedDict):
    name: str
    l3: dict[str, str]


class L1Node(TypedDict):
    name: str
    l2: dict[str, L2Node]


TaxonomyDict = dict[str, L1Node]


_L1_RE = re.compile(r"^####\s+(\d+)\.\s+\*\*(.+?)\*\*\s*$")
# L2 acepta texto trailing tras `**` (la taxonomía real usa parentéticos:
# `- **14.1 Elogio genérico** ("excelente", "todo bien")`).
_L2_RE = re.compile(r"^-\s+\*\*(\d+\.\d+)\s+(.+?)\*\*")
_L3_RE = re.compile(r"^\s+-\s+(\d+\.\d+\.\d+)\s+(.+?)\s*$")


def _default_taxonomy_path() -> Path:
    # engine/src/engine/taxonomy.py → repo root / docs / taxonomia_revisada.md
    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    return repo_root / "docs" / "taxonomia_revisada.md"


def _parse(text: str) -> TaxonomyDict:
    taxonomy: TaxonomyDict = {}
    current_l1: str | None = None
    current_l2: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")

        m1 = _L1_RE.match(line)
        if m1:
            current_l1 = m1.group(1)
            current_l2 = None
            taxonomy[current_l1] = {"name": m1.group(2).strip(), "l2": {}}
            continue

        m2 = _L2_RE.match(line)
        if m2 and current_l1 is not None:
            l2_code = m2.group(1)
            # Validar que el L2 sea hijo del L1 actual ("1.1" empieza con "1.").
            if l2_code.split(".")[0] != current_l1:
                # L2 fuera de contexto: ignorar silenciosamente.
                continue
            current_l2 = l2_code
            taxonomy[current_l1]["l2"][l2_code] = {
                "name": m2.group(2).strip(),
                "l3": {},
            }
            continue

        m3 = _L3_RE.match(line)
        if m3 and current_l1 is not None and current_l2 is not None:
            l3_code = m3.group(1)
            parent_l2 = ".".join(l3_code.split(".")[:2])
            if parent_l2 != current_l2:
                # L3 fuera de su L2 padre: ignorar.
                continue
            taxonomy[current_l1]["l2"][current_l2]["l3"][l3_code] = m3.group(2).strip()

    return taxonomy


@lru_cache(maxsize=4)
def load_taxonomy(path: str | None = None) -> TaxonomyDict:
    """Parsea la taxonomía L1/L2/L3 y devuelve un dict jerárquico.

    Si `path` es None, usa `<repo>/docs/taxonomia_revisada.md`.
    El resultado se memoiza por path para evitar re-parseo.
    """
    resolved = Path(path) if path else _default_taxonomy_path()
    if not resolved.exists():
        raise FileNotFoundError(f"No se encontró la taxonomía en {resolved}")
    return _parse(resolved.read_text(encoding="utf-8"))


def get_l2_name(l1_code: str, l2_code: str, *, path: str | None = None) -> str:
    """Devuelve el nombre del L2 dado su código.

    Lanza KeyError si el código no existe (contrato §7: la firma es estricta).
    """
    tax = load_taxonomy(path)
    if l1_code not in tax:
        raise KeyError(f"L1 desconocido: {l1_code!r}")
    l2_map = tax[l1_code]["l2"]
    if l2_code not in l2_map:
        raise KeyError(f"L2 desconocido: {l2_code!r} (L1 {l1_code!r})")
    return l2_map[l2_code]["name"]


def get_l1_name(l1_code: str, *, path: str | None = None) -> str:
    tax = load_taxonomy(path)
    if l1_code not in tax:
        raise KeyError(f"L1 desconocido: {l1_code!r}")
    return tax[l1_code]["name"]


def l3_belongs_to_l2(l3_code: str, l2_code: str) -> bool:
    """Verifica que `l3_code` sea descendiente sintáctico de `l2_code`.

    Útil para validar respuestas del LLM antes de persistir
    (03_M2a §Riesgos → Disonancia entre L3 anotado y L2 padre).
    """
    return l3_code.startswith(l2_code + ".") and l3_code.count(".") == 2


def count_levels(tax: TaxonomyDict | None = None) -> tuple[int, int, int]:
    """Devuelve (n_l1, n_l2, n_l3). Útil para tests y diagnóstico."""
    if tax is None:
        tax = load_taxonomy()
    n_l1 = len(tax)
    n_l2 = sum(len(node["l2"]) for node in tax.values())
    n_l3 = sum(
        len(l2_node["l3"]) for node in tax.values() for l2_node in node["l2"].values()
    )
    return n_l1, n_l2, n_l3


def serialize_for_prompt(tax: TaxonomyDict | None = None) -> str:
    """Serializa la taxonomía a un bloque de texto plano para inyectar al prompt.

    Formato compacto para minimizar tokens:
        1. Atención al cliente
          1.1 Trato del personal
            1.1.1 Amabilidad y cortesía
            1.1.2 Trato distante o grosero
          1.2 ...
    """
    if tax is None:
        tax = load_taxonomy()
    lines: list[str] = []
    for l1_code in sorted(tax.keys(), key=lambda c: int(c)):
        node = tax[l1_code]
        lines.append(f"{l1_code}. {node['name']}")
        for l2_code in sorted(
            node["l2"].keys(), key=lambda c: tuple(int(x) for x in c.split("."))
        ):
            l2_node = node["l2"][l2_code]
            lines.append(f"  {l2_code} {l2_node['name']}")
            for l3_code in sorted(
                l2_node["l3"].keys(), key=lambda c: tuple(int(x) for x in c.split("."))
            ):
                lines.append(f"    {l3_code} {l2_node['l3'][l3_code]}")
    return "\n".join(lines)
