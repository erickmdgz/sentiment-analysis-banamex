# engine — Motor de análisis (M2a + M2b)

Paquete Python del motor híbrido de clasificación para `sentiment-analysis-banamex`.

Este README documenta lo entregado en **M2a** (anotador LLM local + 4 extractores
rule-based). M2b (clasificador supervisado) vive en otro worktree y se integra
después por merge en `main`.

## Instalación

Desde la raíz del repositorio:

```bash
pip install -e ./engine
```

Para desarrollo, instala además las dependencias opcionales:

```bash
pip install -e "./engine[dev]"
```

## Pre-requisitos para anotar

El anotador llama a un LLM local servido por **Ollama**.

```bash
brew install ollama        # macOS
ollama serve               # mantenlo corriendo en otra terminal
ollama pull qwen2.5:7b-instruct
```

Variables de entorno (todas con defaults):

| Variable | Default | Descripción |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Endpoint de Ollama |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct` | Modelo a usar para anotación |
| `DATABASE_URL` | (sin default) | DSN SQLAlchemy de la DB de M1 |

## API Python expuesta

```python
from engine.taxonomy import load_taxonomy, get_l2_name
from engine.extractors import extract_all
from engine.annotator import run_annotation, sample_records, AnnotationCache
```

| Símbolo | Qué hace |
|---|---|
| `load_taxonomy()` | Parsea `docs/taxonomia_revisada.md` y devuelve dict L1/L2/L3 |
| `get_l2_name(l1_code, l2_code)` | Lookup canónico de nombre de L2 |
| `extract_all(text)` | Devuelve `Metadata` con los 4 extractores aplicados |
| `sample_records(df, target_size, seed)` | Muestreo estratificado 35/25/40 |
| `run_annotation(df, ...)` | Corre el anotador end-to-end (async) |
| `AnnotationCache` | Caché en disco por `record_id` |

Cuando M2b esté listo, también expondrá `engine.pipeline.classify` y
`engine.classifier`. Hasta entonces, los módulos `embeddings.py`, `trainer.py`,
`classifier.py`, `pipeline.py` y `mocks.py` no existen (los provee M2b).

## CLI

```bash
# Vista previa del muestreo, sin llamar al LLM
python -m engine.cli annotate-sample \
    --size 100 --seed 42 --dry-run \
    --fixture engine/tests/fixtures/verbalizations.csv

# Corrida real (requiere Ollama listo) sobre la DB de M1
python -m engine.cli annotate-sample \
    --size 5000 --seed 42 --concurrency 4 \
    --db-url sqlite:///./data/processed/banamex.db \
    --persist-db

# Extractores sobre todas las verbalizations (1 fila por record_id)
python -m engine.cli extract-metadata \
    --db-url sqlite:///./data/processed/banamex.db
```

Flags útiles de `annotate-sample`:

- `--dry-run` muestra el sample y termina.
- `--clear-cache` borra `data/cache/annotations/` antes de empezar.
- `--skip-preflight` evita el chequeo de Ollama (útil para pipelines de prueba).
- `--fixture <csv>` apunta a un CSV en lugar de la DB.

## Tests

```bash
pytest engine/tests/test_taxonomy.py \
       engine/tests/test_annotator.py \
       engine/tests/test_extractors.py
```

Los tests del anotador usan un cliente Ollama mock, no requieren Ollama real ni
DB. El fixture sintético en `engine/tests/fixtures/verbalizations.csv` cubre 200
filas con mix 35/25/40 y los 16 meses (enero 2025 a abril 2026).

## Archivos de datos del paquete

- `src/engine/data/spanish_names.txt` — diccionario de nombres de pila para
  detección de personal.
- `src/engine/data/mexican_banks.txt` — bancos competidores reconocidos.
- `src/engine/data/channel_keywords.txt` — keywords por canal canónico.

Los tres se cargan como `package_data` (declarado en `pyproject.toml`).

## Notas

- La taxonomía L1/L2/L3 vive en `docs/taxonomia_revisada.md` (Anexo). Cualquier
  cambio en los códigos rompe contratos con M2b.
- `data/cache/annotations/` se crea en runtime y está en `.gitignore`.
- La polaridad de cada clasificación se hereda del `nps_group` del cliente
  (decisión `00 §8`), no la elige el LLM.
