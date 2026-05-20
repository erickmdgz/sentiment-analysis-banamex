# M3 — Capa de analytics

## Responsabilidad

M3 implementa la capa de **funciones puras de agregación** sobre la base SQLite definida en `01_contratos_compartidos.md §2`. Calcula los indicadores que alimentan las pantallas descritas en `propuesta_inicial.md §7, §8, §10, §11, §12`: NPS nacional y por sucursal, distribuciones, brechas contra objetivo, sucursales críticas (decisión `00 §14`), rankings, tendencias mensuales, comparaciones entre meses, principales causas y fortalezas por bucket UI, palabras frecuentes, comentarios representativos, insights narrativos, impacto en NPS por categoría (counterfactual de `00 §16`), análisis específico de pasivos (`00 §17`) y menciones a personal. Todas las salidas son DTOs Pydantic ya declarados en `01_contratos_compartidos.md §4`.

Esta capa **no tiene estado**, **no expone HTTP**, **no contiene lógica de presentación**. Recibe una `Session` de SQLAlchemy (o estructuras iterables) y devuelve DTOs. La API de M4 envuelve estas funciones casi 1:1 en handlers HTTP que sólo serializan a JSON. El motor de M2 no se invoca en esta capa: las clasificaciones y metadatos ya están persistidos en `classifications` y `metadata_extractions` cuando M3 corre.

## Entregables

- [ ] `analytics/schemas.py` — re-exporta los DTOs Pydantic definidos en `01_contratos_compartidos.md §4` (`NPSDistribution`, `NPSSummary`, `MonthlyPoint`, `MonthlyTrend`, `CauseBucket`, `StrengthBucket`, `CriticalBranch`, `Ranking`, `Rankings`, `SuggestedAction`, `ImpactByCategory`, `Insight`, `WordFrequency`, `RepresentativeComment`, `PersonnelMention`, `NationalYTD`, `BranchYTD`, `MonthlyComparison`).
- [ ] `analytics/nps.py`:
  - [ ] `compute_nps(records: Iterable[Verbalization]) -> float`
  - [ ] `compute_distribution(records: Iterable[Verbalization]) -> NPSDistribution`
  - [ ] `national_ytd_summary(session) -> NPSSummary`
  - [ ] `branch_ytd_summary(session, branch_id) -> NPSSummary`
- [ ] `analytics/ranking.py`:
  - [ ] `critical_branches(session, limit=10) -> list[CriticalBranch]`
  - [ ] `branches_by_worst_nps(session, limit=20) -> list[CriticalBranch]`
  - [ ] `branches_by_worst_gap(session, limit=20) -> list[CriticalBranch]`
  - [ ] `branches_by_most_detractors(session, limit=20) -> list[CriticalBranch]`
  - [ ] `branches_worsened(session, month_a, month_b, limit=20) -> list[CriticalBranch]`
  - [ ] `branches_improved(session, month_a, month_b, limit=20) -> list[CriticalBranch]`
  - [ ] `rankings_bundle(session) -> Rankings`
- [ ] `analytics/trends.py`:
  - [ ] `monthly_trend(session, scope: Literal['national'] | str) -> MonthlyTrend`
  - [ ] `compare_months(session, month_a, month_b, scope) -> MonthlyComparison`
  - [ ] `available_months(session) -> list[str]`
- [ ] `analytics/topics.py`:
  - [ ] `top_causes(session, scope, group='Detractor', limit=10) -> list[CauseBucket]`
  - [ ] `top_strengths(session, scope, group='Promotor', limit=10) -> list[StrengthBucket]`
  - [ ] `bucket_distribution(session, scope) -> dict[str, int]`
  - [ ] `passive_analysis(session, scope) -> dict` (segmentación 7 vs 8 según decisión `00 §17`)
- [ ] `analytics/words.py`:
  - [ ] `top_words(session, branch_id, group=None, top_n=30) -> list[WordFrequency]`
  - [ ] Stopwords cargadas desde `analytics/data/stopwords_es_banking.txt`
- [ ] `analytics/representatives.py`:
  - [ ] `pick_representatives(session, branch_id, n_per_topic=2) -> list[RepresentativeComment]`
- [ ] `analytics/insights.py`:
  - [ ] `national_insights(session) -> list[Insight]`
  - [ ] `branch_insights(session, branch_id) -> list[Insight]`
- [ ] `analytics/impact.py`:
  - [ ] `impact_by_category(session, scope) -> list[ImpactByCategory]` (counterfactual `00 §16`)
- [ ] `analytics/personnel.py`:
  - [ ] `mentions(session, branch_id) -> list[PersonnelMention]`
- [ ] `analytics/actions.py`:
  - [ ] `suggested_actions_national(session) -> list[SuggestedAction]`
  - [ ] `suggested_actions_branch(session, branch_id) -> list[SuggestedAction]`
- [ ] `analytics/data/stopwords_es_banking.txt` (~200 palabras: castellano básico + términos bancarios genéricos como `banco`, `banamex`, `sucursal`, `cliente`, `cuenta`).
- [ ] README del paquete (`analytics/README.md`) en español: cómo instalar, cómo correr tests, qué expone.

## Contratos consumidos

Tablas SQLite (definidas en `01_contratos_compartidos.md §2`) leídas vía SQLAlchemy con los modelos ORM de `01 §3`:

- `verbalizations` — campos clave: `record_id`, `response_year`, `response_month`, `nps_group`, `nps_rate`, `verbatim_clean`, `branch_id`.
- `branches` — catálogo de sucursales detectadas.
- `branch_targets` — objetivos sintéticos generados por M1 según decisión `00 §15`.
- `classifications` — multilabel; campos clave: `record_id`, `l1_code`, `l2_code`, `ui_bucket`, `polarity`, `source`. Una verbalización puede tener N filas.
- `metadata_extractions` — 1:1 con `verbalizations`; campos clave: `personnel_named`, `personnel_name`, `personnel_polarity`, `explicit_recommendation`, `other_bank_names`, `channels_mentioned`.

Constantes consumidas desde `engine.ui_buckets` (declaradas en `01 §6`): `CAUSE_BUCKETS`, `STRENGTH_BUCKETS`, `UI_BUCKETS_BY_L1`.

Si M1 o M2 no están listos en el momento de implementar M3, se trabaja contra un dataset sintético en `analytics/tests/fixtures/synthetic_db.sql` con 1.000 verbalizaciones pre-clasificadas (distribuidas en ~20 sucursales sintéticas, 12 meses, distribución NPS realista 40/25/35). El fixture se carga en una SQLite in-memory para cada corrida de pytest.

## Contratos producidos

Los DTOs Pydantic listados en `01_contratos_compartidos.md §4`. La API de M4 los re-exporta sin modificación (ver `01 §12`: "los DTOs de `analytics.schemas` mandan; la API los re-exporta sin cambios"). No se introducen nuevos DTOs en M3 — si una agregación requiere un schema nuevo, primero se añade a `01 §4` y luego se implementa.

## Estructura de archivos esperada

Subárbol del paquete `analytics/` tomado de `01_contratos_compartidos.md §1`:

```
analytics/                        # Agregaciones y análisis (M3)
├── pyproject.toml
├── src/analytics/
│   ├── __init__.py
│   ├── schemas.py                # DTOs Pydantic (la API los re-exporta)
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
    ├── fixtures/
    │   └── synthetic_db.sql
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

## Detalles de implementación clave

### Cálculo de NPS

- Fórmula canónica:

  ```
  NPS = (n_promotores − n_detractores) / n_total × 100
  ```

- Retornar `float`. El redondeo (a entero o a 1 decimal) ocurre en la capa de presentación (frontend) o, a lo sumo, en la serialización Pydantic, **no en el cálculo**.
- Filtro YTD: idealmente `response_year = 2026 AND response_month <= mes_actual`. Para MVP se aplica la regla operativa: `response_year = max(response_year disponible en la base)` y todos sus meses presentes. Esto evita la dependencia de "fecha actual" en el demo y respeta lo que sugiere `propuesta_inicial.md §7.2`.

### `national_ytd_summary` — NPS nacional YTD

- `nps_actual`: NPS calculado sobre todas las `verbalizations` del año YTD.
- `nps_target`: **promedio simple** de `branch_targets.nps_target_annual` sobre las sucursales presentes en la base (decisión por `propuesta_inicial.md §7.3` y consistente con `00 §15`). Como alternativa documentada en docstring queda el promedio ponderado por volumen de respuestas; el MVP usa el simple por simplicidad.
- `gap`: `nps_actual − nps_target`.
- `total_responses`: `COUNT(*)` sobre las verbalizations del periodo YTD.
- `distribution`: `NPSDistribution` con conteos y porcentajes (P/Pa/D).

### `branch_ytd_summary` — NPS por sucursal

- Mismo cálculo agregando filtro `branch_id = ?`.
- `nps_target`: leído directamente de `branch_targets` para esa sucursal; si no existe registro, `None`.
- `gap`: `None` si `nps_target is None`; en caso contrario `nps_actual − nps_target`.

### Sucursales críticas (`critical_branches`)

Implementa las cuatro condiciones de `00 §14`. Cada sucursal con al menos una condición disparada entra al resultado.

1. `nps_actual < (nps_target − 5)` — requiere `nps_target IS NOT NULL`.
2. La brecha cae en el **percentil 10 peor del nacional** — requiere target; el percentil se calcula con `numpy.percentile` sobre el array de brechas no nulas (post-query), o con `PERCENT_RANK()` (window function) si se prefiere SQL puro.
3. `detractors_pct >= 30` — siempre aplicable.
4. Deterioro mes-a-mes ≥ 5 puntos de NPS, comparando el último mes disponible contra el inmediato anterior. Opcional: si no hay dos meses disponibles para esa sucursal, la condición se omite (no se considera disparada).

Reglas:

- Si la sucursal **no tiene target**, sólo se evalúan las condiciones (3) y (4) (consistente con `00 §14`).
- `triggered_conditions: list[str]` contiene strings legibles, p.ej. `"NPS < objetivo − 5"`, `"brecha en percentil 10 peor"`, `"≥30% detractores"`, `"deterioro mes-a-mes ≥ 5"`.
- Ordenar resultados por (a) número de condiciones disparadas desc, luego (b) brecha asc cuando aplique, luego (c) `detractors_pct` desc como desempate.

### Rankings (`rankings_bundle`)

Cada ranking individual produce una `Ranking` con `name` y `items: list[dict]`. Cada item es `{"branch_id": str, "value": float | int, "label": str}`. Los cinco rankings derivan de `propuesta_inicial.md §7.9`:

- `worst_nps`: orden ascendente por `nps_actual`.
- `worst_gap`: orden ascendente por `gap` (excluye sucursales sin target).
- `most_detractors`: orden descendente por `detractors_pct`.
- `worsened`: orden ascendente por delta NPS (mes actual − mes previo).
- `improved`: orden descendente por el mismo delta.

`rankings_bundle` los empaqueta en el DTO `Rankings`.

### Tendencia mensual (`monthly_trend`)

- Agrupar por `(response_year, response_month)`.
- Formato del campo `month`: `"YYYY-MM"` (zero-padded).
- Calcular NPS por punto sobre el subconjunto del mes.
- Ordenar cronológicamente ascendente.
- Marcar `partial=True` o filtrar puntos con `responses < N_minimo` (N=50) si el mes tiene muy pocas respuestas; documentar el umbral como constante de módulo.
- `scope='national'` o `scope=branch_id` (string) — la función filtra en consecuencia.

### `compare_months`

- **Validar previo**: ambos meses deben existir en `available_months(session)`. Si alguno no existe, `raise ValueError` con mensaje listando los meses válidos.
- Calcular para cada mes: `NPSSummary`, `NPSDistribution`, top causes, top strengths.
- `causes_increased` / `causes_decreased`: deltas de conteo por bucket entre los dos meses; devolver lista de nombres ordenada por magnitud del delta.
- `strengths_increased` / `strengths_decreased`: análogo.
- `branches_improved` / `branches_worsened`: reutilizar `branches_improved(session, month_a, month_b)` y `branches_worsened(session, month_a, month_b)`.

### Top causes (`top_causes`)

Decisión: multiclase cuenta **1 por categoría por comentario**, no N (evita inflar conteos). Query base:

```sql
SELECT c.ui_bucket, COUNT(DISTINCT c.record_id) AS count
FROM classifications c
JOIN verbalizations v ON c.record_id = v.record_id
WHERE v.nps_group = :group
  AND c.ui_bucket IN :CAUSE_BUCKETS
  -- + filtro de scope (branch_id) y filtro YTD si aplica
GROUP BY c.ui_bucket
ORDER BY count DESC
LIMIT :limit;
```

- `DISTINCT record_id`: un comentario que toca 3 categorías cuenta 1 vez por cada bucket, no 3 veces dentro del mismo bucket.
- `pct_of_group`: `count / total_del_grupo_NPS` (denominador = total de verbalizations del grupo en el scope).
- `sample_l2`: subquery por bucket que toma los 3 `l2_name` más frecuentes dentro de ese bucket.
- Excluir `ui_bucket = 'Otros'` del listado para causas, salvo decisión explícita en contrario (los buckets visibles son los de `CAUSE_BUCKETS` en `01 §6`).

### Top strengths (`top_strengths`)

Análogo a causes, con `nps_group = 'Promotor'` y `ui_bucket IN STRENGTH_BUCKETS` (que excluye `Costos`, `Aclaraciones, quejas y fraude`, `Procesos y requisitos`, ver `01 §6`).

### `passive_analysis` (decisión `00 §17`)

- Segmentar verbalizations con `nps_group = 'Pasivo'` por `nps_rate` en dos subgrupos: 7 (cerca de detractor) y 8 (cerca de promotor).
- Para cada subgrupo, reportar `top_causes`-style sobre todos los buckets (no sólo `CAUSE_BUCKETS`).
- Retornar dict `{"near_detractor": list[CauseBucket], "near_promoter": list[CauseBucket]}`.

### Top words (`top_words`)

- Cargar stopwords desde `analytics/data/stopwords_es_banking.txt` (cacheada en variable de módulo).
- Tokenización: `re.findall(r"\b[a-záéíóúñ]{3,}\b", text.lower())` sobre `verbatim_clean`.
- Filtrar tokens que estén en stopwords.
- Contar con `collections.Counter`.
- Retornar top N como lista de `WordFrequency`.
- Si `group` se pasa (`'Promotor' | 'Pasivo' | 'Detractor'`), filtrar por `nps_group` antes de tokenizar.

### Comentarios representativos (`pick_representatives`)

Heurística por bucket:

- Calcular P25 y P75 de longitud (`len(verbatim_clean)`) sobre comentarios de la sucursal.
- Filtrar comentarios cuya longitud esté entre P25 y P75 (no extremadamente cortos ni demasiado discursivos).
- Filtrar comentarios cuya `polarity` sea consistente con el grupo NPS (Promotor→pos, Detractor→neg).
- Requerir match léxico contra **palabras canónicas** declaradas por bucket, p.ej.:
  - `"Tiempos y espera"` → `{espera, fila, turno, demora, tardanza}`.
  - `"Atención del personal"` → `{atención, atendieron, amable, grosero, actitud}`.
  - `"Cajeros (ATM)"` → `{cajero, atm}`.
  - (Diccionario completo declarado como constante de módulo).
- Tomar `n_per_topic` comentarios por bucket presente en la sucursal.
- Retornar lista de `RepresentativeComment` (`record_id`, `verbatim`, `nps_rate`, `nps_group`, `response_date`, `bucket`).

### Insights narrativos

Plantillas tipo `f-string` con datos calculados (consistentes con `propuesta_inicial.md §12.1` y `§12.2`):

```python
# Ejemplos:
f"El NPS nacional YTD está {abs(gap):.0f} puntos por debajo del objetivo anual."   # si gap < 0
f"Las principales causas de detracción son {', '.join(top_3_causes)}."
f"Las principales fortalezas son {', '.join(top_3_strengths)}."
f"Hay {n_critical} sucursales críticas por brecha negativa contra objetivo."
f"Las sucursales con peor NPS son {', '.join(top_3_worst)}."
f"De {month_a} a {month_b}, el NPS nacional {'subió' if delta>0 else 'bajó'} {abs(delta):.0f} puntos."
f"La sucursal {branch_id} tiene un NPS YTD de {nps:.0f} contra objetivo de {target}."
f"Esta sucursal no tiene objetivo anual disponible en la fuente interna."         # cuando target is None
f"El principal motivo de detracción es {top_cause}."
```

- Una función privada por plantilla, cada una devuelve `Insight | None` (None si los datos no permiten generar el insight).
- `national_insights` / `branch_insights` componen y devuelven la lista filtrando los `None`.
- Fallback cuando no hay datos suficientes: emitir `Insight(text="Datos insuficientes para X", category=...)` en lugar de omitir silenciosamente.

### `impact_by_category` (counterfactual `00 §16`)

Pseudocódigo:

```python
def impact_by_category(session, scope) -> list[ImpactByCategory]:
    nps_actual = compute_scope_nps(session, scope)
    out = []
    for bucket in CAUSE_BUCKETS:
        affected = SELECT DISTINCT record_id
                   FROM classifications c JOIN verbalizations v USING (record_id)
                   WHERE c.ui_bucket = bucket
                     AND v.nps_group = 'Detractor'
                     AND scope_filter(v)
        nps_simulated = recompute_nps_treating_as_passive(session, scope, affected)
        impact_points = nps_simulated - nps_actual
        out.append(ImpactByCategory(bucket=bucket, impact_points=impact_points))
    return sorted(out, key=lambda x: x.impact_points, reverse=True)
```

`recompute_nps_treating_as_passive` recalcula NPS suponiendo que los `record_id` afectados ahora son Pasivos (es decir, no cuentan como Detractor ni Promotor). No reasigna a Promotor; la decisión es defendible y conservadora.

### Personnel mentions (`mentions`)

Query base:

```sql
SELECT m.personnel_name, m.personnel_polarity, COUNT(*) AS count
FROM metadata_extractions m
JOIN verbalizations v ON m.record_id = v.record_id
WHERE v.branch_id = :branch_id
  AND m.personnel_named = 1
GROUP BY m.personnel_name, m.personnel_polarity
ORDER BY count DESC;
```

Para cada fila, completar `example_record_id` y `example_verbatim` con una subquery que devuelve la primera mención de ese (`name`, `polarity`) en la sucursal.

### Suggested actions

Reglas declarativas (10-15 reglas que cubran los escenarios típicos de `propuesta_inicial.md §7.10`, `§13.1`, `§13.2`):

- Si `top_causes[0].bucket == 'Tiempos y espera'` → `"Revisar operación de turnos en sucursales con alta espera"` (priority alta).
- Si `len(critical_branches) >= 10` → `"Priorizar intervención en sucursales críticas"` (priority alta).
- Si hay menciones negativas a personal → `"Atender menciones negativas hacia personal"` (priority media).
- Si `top_causes` incluye `'Canales digitales'` con conteo significativo → `"Reforzar capacitación en resolución de problemas de app / NetKey"`.
- Si hay sucursales con respuestas pero sin target → `"Revisar sucursales sin objetivo configurado en la fuente interna"`.
- Si `top_causes` incluye `'Procesos y requisitos'` → `"Revisar procesos que generan vueltas innecesarias"`.
- Si una sucursal tiene `gap < -10` → `"Auditar sucursal con brecha negativa amplia"`.
- Si `top_strengths` tiene `'Atención del personal'` con alta concentración → `"Replicar prácticas de personal con menciones positivas"`.
- (Resto de reglas en `actions.py`).

Cada regla devuelve `SuggestedAction(text, priority, related_bucket, related_branches)`. La lista final se ordena por priority (`alta` > `media` > `baja`) y se trunca a 10.

### Caché

- Empezar **sin caché**. Medir con `time.perf_counter` en cada función.
- Si alguna función excede 500 ms sobre 474k filas con los índices declarados en `01 §2`, añadir `functools.lru_cache(maxsize=None)` a la función pura subyacente cuando el parámetro `session` no aparezca en la firma.
- Para funciones que reciben `session`, considerar `cachetools.TTLCache` con TTL corto (5 min), keyed por los demás parámetros.
- Documentar tiempos medidos en el docstring de cada función pública (medidos contra la base completa de 474k filas).

## Tests requeridos

Mínimo 25 tests, distribuidos por módulo. Cada test usa el fixture `synthetic_db.sql` cargado en SQLite in-memory salvo que se indique otra cosa.

- `test_nps`
  - [ ] `compute_nps` con 50P/30S/20D → NPS = 30.
  - [ ] `compute_nps` sobre lista vacía → comportamiento definido: devuelve `0.0` o lanza `ValueError`. Documentar y testear el comportamiento elegido.
  - [ ] `compute_distribution`: los tres porcentajes suman 100 (± epsilon).
  - [ ] `national_ytd_summary`: estructura completa, todos los campos presentes.
  - [ ] `branch_ytd_summary`: sucursal con target → `gap` numérico; sucursal sin target → `nps_target is None` y `gap is None`.
- `test_ranking`
  - [ ] `critical_branches`: las 4 condiciones se evalúan correctamente con datasets controlados (sucursal A dispara sólo (1), B sólo (3), C dispara (1) y (3), etc.).
  - [ ] `critical_branches`: sucursal sin target sólo evaluada por (3) y (4); jamás aparece en (1)/(2).
  - [ ] `rankings_bundle`: las 5 listas presentes, sin sucursales duplicadas dentro de cada lista.
- `test_trends`
  - [ ] `monthly_trend`: puntos en orden cronológico ascendente.
  - [ ] `compare_months`: mes inexistente → `ValueError` con mensaje que lista meses disponibles.
- `test_topics`
  - [ ] `top_causes`: multiclase cuenta DISTINCT correctamente (un comentario con 3 buckets aporta 1 a cada uno).
  - [ ] `top_causes`: `0 <= pct_of_group <= 1` para toda fila.
  - [ ] `top_strengths`: sólo computa sobre `nps_group = 'Promotor'`.
  - [ ] `passive_analysis`: segmentación 7 vs 8 correcta; los record_ids reportados en `near_detractor` tienen `nps_rate=7` exclusivamente.
- `test_words`
  - [ ] `top_words`: stopwords se filtran (ninguna palabra del archivo de stopwords aparece en la salida).
  - [ ] `top_words`: tokenización ignora puntuación y números.
- `test_representatives`
  - [ ] `pick_representatives`: todos los comentarios devueltos pertenecen a la `branch_id` solicitada.
  - [ ] `pick_representatives`: longitud de los comentarios está entre P25 y P75 de la distribución de longitudes de la sucursal.
- `test_insights`
  - [ ] `national_insights`: cuenta correcta para cada plantilla (e.g. al menos 1 insight de tipo `nps`, 1 de `brecha`, etc.).
  - [ ] Caso "datos insuficientes": un fixture mini con 3 verbalizations produce insights de fallback en lugar de exception.
- `test_impact`
  - [ ] Para un bucket con muchos detractores asignados, `impact_points > 0`.
  - [ ] La lista resultante está ordenada descendente por `impact_points`.
- `test_personnel`
  - [ ] `mentions` agrega correctamente por `(name, polarity)`; un mismo nombre con dos polaridades aparece como dos filas.
- `test_actions`
  - [ ] La regla "Tiempos y espera" se dispara cuando el bucket es el top cause; no se dispara cuando no lo es.

## Definition of Done

- [ ] `pytest analytics/tests` pasa al 100%.
- [ ] `mypy --strict analytics/` pasa sin errores.
- [ ] Dataset sintético de 1.000 filas en `analytics/tests/fixtures/synthetic_db.sql` cubre todos los casos de los tests anteriores (sucursales con/sin target, los 10 `CAUSE_BUCKETS`, los 7 `STRENGTH_BUCKETS`, al menos 12 meses, distribuciones P/Pa/D balanceadas, comentarios con menciones a personal positivas y negativas).
- [ ] README del paquete escrito en español, indica cómo instalar (`pip install -e ./analytics`), cómo correr tests, cómo importar las funciones públicas.
- [ ] Tiempos de cada función pública documentados en su docstring (medidos contra la base completa de 474k filas o, en su defecto, contra el fixture sintético escalado a 100k).
- [ ] Sin secrets en archivos commiteables (regla global del usuario).

## Riesgos específicos del módulo

- **Latencia sobre 474k filas**: cómputos con joins entre `classifications` y `verbalizations` pueden ser lentos. Mitigación: los índices `idx_class_record`, `idx_class_bucket`, `idx_verb_branch`, `idx_verb_date`, `idx_verb_nps_group` ya están declarados en `01 §2`. Si aún así se exceden 500 ms, aplicar la estrategia de caché documentada arriba.
- **Tendencia mensual con meses parciales**: el último mes disponible puede tener muy pocas respuestas (especialmente si la base se cargó a mediados de mes). Mitigación: marcar `partial=True` en el `MonthlyPoint` o filtrar puntos con `responses < 50`. Documentar el umbral.
- **Multiclase contado mal**: el riesgo más alto en `top_causes` y `top_strengths` es multiplicar conteos cuando un comentario toca varias categorías. Mitigación: usar `COUNT(DISTINCT record_id)` siempre que se cuente "comentarios", reservar `COUNT(*)` para "etiquetas".
- **Insights vacíos o triviales**: si una sucursal tiene pocas respuestas (e.g. <20), las plantillas pueden generar texto absurdo (`"El principal motivo de detracción es Otros"`). Mitigación: cada plantilla devuelve `None` cuando sus precondiciones no se cumplen, y la lista final emite un `Insight(text="Datos insuficientes para X", ...)` declarativo.
- **Polaridad heredada del grupo NPS** (`00 §8`): los comentarios donde un promotor expresa una queja específica entran como `polarity='pos'` y pueden aparecer en `top_strengths` con texto incongruente. Es un error tolerable documentado; M3 no intenta corregirlo (sería rehacer M2).
- **Targets sintéticos** (`00 §15`): el `gap` siempre es contra un target sintético. La narrativa generada en `insights` se basa en una métrica artificial. Mitigación: el frontend muestra el aviso "Objetivos NPS sintéticos para demo"; M3 sólo entrega números.
- **Pasivos con segmentación 7/8** (`00 §17`): si en la base hay muy pocos pasivos con `nps_rate=7` o `nps_rate=8`, los top causes de `passive_analysis` pueden ser ruido. Mitigación: documentar y dejar que el frontend decida si mostrar o no la sección.
