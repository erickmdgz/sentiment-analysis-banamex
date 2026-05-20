"""Prompts y schema JSON del output del LLM anotador.

OUTPUT_SCHEMA se pasa a Ollama como format=<schema> para constrained decoding
nativo (requiere Ollama >= 0.5). M2a lo carga literal; no modificar sin pasar
por el usuario.

Fuente: docs/plan_implementacion/01_contratos_compartidos.md §5.
SYSTEM_PROMPT lo construye M2a a partir de docs/taxonomia_revisada.md.
"""

from __future__ import annotations

# JSON Schema autoritativo que cada respuesta del LLM debe satisfacer.
OUTPUT_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "VerbalizationClassification",
    "type": "object",
    "required": ["record_id", "is_classifiable", "categories"],
    "additionalProperties": False,
    "properties": {
        "record_id": {
            "type": "string",
            "description": "El record_id de la verbalización a clasificar",
        },
        "is_classifiable": {
            "type": "boolean",
            "description": (
                "false si el texto está vacío, es ininteligible, "
                "o no contiene contenido temático"
            ),
        },
        "categories": {
            "type": "array",
            "minItems": 0,
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": ["l1_code", "l1_name", "l2_code", "l2_name", "confidence"],
                "additionalProperties": False,
                "properties": {
                    "l1_code": {
                        "type": "string",
                        "enum": [str(i) for i in range(1, 16)],
                    },
                    "l1_name": {"type": "string"},
                    "l2_code": {"type": "string"},
                    "l2_name": {"type": "string"},
                    "l3_code": {"type": ["string", "null"]},
                    "l3_name": {"type": ["string", "null"]},
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confianza subjetiva del clasificador en esta etiqueta",
                    },
                },
            },
        },
    },
}

# M2a sobreescribe este placeholder con la taxonomía serializada
# (parsea docs/taxonomia_revisada.md y la inyecta en el prompt).
SYSTEM_PROMPT_TEMPLATE: str = """\
Eres un anotador experto en sentimientos de clientes bancarios.
Clasifica cada verbalización contra la taxonomía L1/L2/L3 que se te da.
Responde SIEMPRE con un JSON que valide contra el schema declarado.

Taxonomía:
{taxonomy}
"""
