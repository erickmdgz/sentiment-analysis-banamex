# analytics — capa de agregaciones (M3)

Funciones puras de agregación sobre la base SQLite del proyecto. Calcula los
indicadores que alimentan el dashboard ejecutivo: NPS nacional y por sucursal,
sucursales críticas, rankings, tendencias mensuales, comparaciones entre meses,
causas y fortalezas por bucket UI, palabras frecuentes, comentarios
representativos, insights narrativos, impacto counterfactual por categoría y
menciones de personal.

Esta capa **no tiene estado**, **no expone HTTP** y **no contiene lógica de
presentación**. Recibe una `Session` de SQLAlchemy (o iterables de
`Verbalization`) y devuelve los DTOs Pydantic declarados en
`analytics/schemas.py`. La API (M4) las envuelve casi 1:1 en endpoints.

Spec autoritativa: `docs/plan_implementacion/05_M3_analytics.md`.

## Instalación

Desde la raíz del repo (recomendado: dentro de un virtualenv con Python 3.12):

```bash
pip install -e ./core ./engine ./analytics --no-deps
pip install 'pydantic>=2.6' 'sqlalchemy>=2.0' 'pytest>=8.0' 'mypy>=1.10'
```

`core` y `engine` se instalan sin sus dependencias pesadas (Ollama,
sentence-transformers, etc.); para M3 sólo se importan los modelos ORM
(`core.models_db`) y las constantes de buckets UI (`engine.ui_buckets`).

## Correr los tests

Desde la raíz:

```bash
cd analytics && pytest -q
```

Todos los tests cargan `tests/fixtures/synthetic_db.sql` sobre una SQLite
in-memory. Son determinísticos (`random.seed(42)`) y cubren los casos listados
en `05_M3_analytics.md §Tests requeridos`.

## Verificación de tipos

```bash
cd analytics && mypy --strict .
```

> **Nota:** la invocación `mypy --strict analytics/` desde la raíz del repo
> requiere que `core/` y `engine/` declaren su marcador `py.typed`
> (PEP 561). Ese marcador vive fuera del scope de este módulo. Hasta que se
> añada, el comando equivalente y validado es el de arriba (`mypy --strict .`
> desde `analytics/`).

## Qué expone

```python
from analytics.nps import (
    compute_nps,
    compute_distribution,
    national_ytd_summary,
    branch_ytd_summary,
)
from analytics.ranking import (
    critical_branches,
    branches_by_worst_nps,
    branches_by_worst_gap,
    branches_by_most_detractors,
    branches_worsened,
    branches_improved,
    rankings_bundle,
)
from analytics.trends import (
    monthly_trend,
    compare_months,
    available_months,
)
from analytics.topics import (
    top_causes,
    top_strengths,
    bucket_distribution,
    passive_analysis,
)
from analytics.words import top_words
from analytics.representatives import pick_representatives
from analytics.insights import national_insights, branch_insights
from analytics.impact import impact_by_category
from analytics.personnel import mentions
from analytics.actions import (
    suggested_actions_national,
    suggested_actions_branch,
)
```

Los DTOs Pydantic en `analytics.schemas` son contrato congelado de
`01_contratos_compartidos.md §4`; la API (M4) los re-exporta sin cambios.

## Decisiones implementadas

- **Filtro YTD operativo**: año más reciente disponible en `verbalizations`
  (`05_M3 §Cálculo de NPS`). Evita depender de "fecha actual" en demo.
- **Target nacional**: promedio simple de `branch_targets.nps_target_annual`
  (decisión `00 §15`).
- **Sucursales críticas**: 4 condiciones de `00 §14`. Sin target sólo se
  evalúan (3) y (4). Resultado ordenado por número de condiciones desc.
- **Top causes / strengths**: `COUNT(DISTINCT record_id)` para evitar
  multiplicar conteos en multilabel.
- **Pasivos**: segmentación `nps_rate=7` vs `nps_rate=8`
  (decisión `00 §17`).
- **Impacto counterfactual**: detractores → pasivos (no se promueve a
  Promotor); más conservador (decisión `00 §16`).
- **Insights**: cada plantilla devuelve `Insight | None`; si total responses
  es bajo, se inserta fallback `Datos insuficientes para X` (categoría
  `cobertura`).
- **Stopwords**: `analytics/data/stopwords_es_banking.txt` — castellano básico
  + términos bancarios genéricos (`banco`, `sucursal`, `cuenta`, …).
- **Representatives**: heurística longitud P25-P75 + polaridad de
  classification consistente con grupo NPS + match léxico con palabras
  canónicas por bucket.

## Estructura

```
analytics/
├── pyproject.toml
├── README.md
├── src/analytics/
│   ├── __init__.py
│   ├── schemas.py            # DTOs Pydantic (contrato congelado, 01 §4)
│   ├── nps.py
│   ├── ranking.py
│   ├── trends.py
│   ├── topics.py
│   ├── words.py
│   ├── representatives.py
│   ├── insights.py
│   ├── impact.py
│   ├── personnel.py
│   ├── actions.py
│   └── data/
│       └── stopwords_es_banking.txt
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   └── synthetic_db.sql  # 1.000 verbalizaciones sintéticas
    ├── test_nps.py
    ├── test_ranking.py
    ├── test_trends.py
    ├── test_topics.py
    ├── test_words.py
    ├── test_representatives.py
    ├── test_insights.py
    ├── test_impact.py
    ├── test_personnel.py
    └── test_actions.py
```

## Performance

Sin caché por defecto. La spec (`05_M3 §Caché`) describe la estrategia a
seguir si alguna función supera 500 ms sobre 474k filas: `functools.lru_cache`
para funciones puras y `cachetools.TTLCache` cuando se involucre `Session`.
Sobre el fixture sintético (1.000 filas) cada función pública corre por debajo
de 50 ms en una laptop M-series.
