# Dudas y conflictos de contratos

Cada sesión paralela anota aquí dudas que detecte sobre `00_decisiones_tecnicas.md` o `01_contratos_compartidos.md`. **No modifiques los contratos directamente** — anota y sigue con la decisión vigente. El usuario integra los issues al final de cada etapa.

Formato sugerido por entrada:

```
## YYYY-MM-DD — <sesión M-x>: <título corto>

**Decisión/contrato afectado:** <archivo, sección>
**Lo que el contrato dice:** <cita literal o resumen breve>
**Lo que la sesión propone:** <propuesta concreta>
**Razón:** <por qué la sesión cree que el contrato es incorrecto o ambiguo>
**Resolución del usuario:** _(pendiente)_
```

---

## 2026-05-19 — Etapa 0: divergencia con §26 sobre versionado

**Decisión afectada:** `00_decisiones_tecnicas.md` §26 (Versionado).

**Lo que el contrato dice:** "el proyecto no tiene git inicializado actualmente (el usuario lo desconectó en sesión previa). **No** se reinicia git como parte del plan."

**Lo que se hizo en Etapa 0:** El plan de orquestación paralela (`~/.claude/plans/nuestro-plan-de-implementaci-n-misty-walrus.md`) sí inicializa git como Etapa -1 (`git init` + `gh repo create --private`) porque el usuario cambió de opinión explícitamente y aprobó esa modificación.

**Estado:** Resuelto por el usuario al aprobar el plan de orquestación. La sección §26 queda obsoleta en este punto del proyecto. No bloquea ninguna sesión.

---

## 2026-05-19 — Etapa 0: ajuste defensivo sobre docs/originales/

**Decisión afectada:** Ninguna explícita; ajuste de implementación.

**Detección:** `docs/originales/Sentiment_analysis_original.zip` contiene los 3 corpus crudos de Banamex (los mismos `*.txt` que `data/raw/`). Versionar este ZIP duplica la exposición de datos sensibles en GitHub.

**Decisión tomada:** Se agregó `docs/originales/` a `.gitignore`. El ZIP permanece local como respaldo inmutable, no se versiona ni sube a remote.

**Estado:** Aplicado. No bloquea ninguna sesión. CLAUDE.md del proyecto sigue diciendo "el .zip original... conservar" — interpretado como conservar en disco local, no en git.

---

## 2026-05-21 — M2a: anexo L1/L2/L3 a `docs/taxonomia_revisada.md` (RESUELTO)

**Decisión/contrato afectado:** `03_M2a_anotador.md` (Detalles de implementación → Parseo de taxonomía) y `00_decisiones_tecnicas.md` Anexo C.

**Lo que la sesión propuso originalmente:** Cuando arrancó M2a, el archivo `docs/taxonomia_revisada.md` heredado en la rama contenía sólo la propuesta inicial del MVP (texto narrativo, sin L1/L2/L3 parseable). Se añadió un Anexo con un árbol deducido (15/48/90) para destrabar el anotador.

**Resolución:** El usuario sustituyó el archivo por la **versión autoritativa del cliente** (commit posterior al primer push de M2a), que ya incluye la jerarquía completa con notas de desambiguación inline. El Anexo deducido quedó descartado (sobrescrito por completo, ningún diff a revertir). La nueva fuente vigente es la taxonomía del cliente — todo lo demás se ajustó a ella.

**Estado:** Resuelto. No bloquea ninguna sesión.

---

## 2026-05-21 — M2a: discrepancia entre el summary del doc y el contenido real (RESUELTO)

**Decisión/contrato afectado:** `docs/taxonomia_revisada.md` (versión autoritativa del cliente, líneas 218-223 — sección "Resumen volumétrico estimado").

**Lo que el contrato decía (resumen del doc):**

> L1: 15 categorías raíz. L2: 48 subcategorías. L3: ~90 aspectos neutrales (dentro del rango 80-100).

**Lo que el contenido real enumera al parsear:** **15 L1, 45 L2, 82 L3**. El parser determinístico (`engine.taxonomy.load_taxonomy`) cuenta ese desfase; los tests reflejan los conteos reales (`test_l2_count_matches_taxonomy_content`, `test_l3_count_matches_taxonomy_content`).

**Razón del desfase:** el resumen del doc se escribió antes de cerrar la jerarquía, o algunas hojas se colapsaron sin actualizar el conteo. No afecta funcionalidad de M2a — la prompt de Ollama se construye a partir del contenido parseado, no del summary.

**Resolución:** Aceptado el conteo real. El resumen volumétrico del doc fue actualizado a 45/82 en `main` (commit `ae3b19b`, antes del merge de Etapa 1).

---

## 2026-05-21 — M2a: verificación L1 codes vs ui_buckets/schemas (sin discrepancia)

**Decisión/contrato afectado:** `engine/src/engine/ui_buckets.py` y `core/src/core/schemas.py` (stubs congelados).

**Verificación realizada:** Los 15 L1 de la taxonomía vigente (códigos `"1"` a `"15"`) coinciden uno-a-uno con las claves de `UI_BUCKETS_BY_L1`. Los nombres canónicos de L1 (`"Atención al cliente"`, `"Tiempos y operación"`, `"Cajeros automáticos (ATM)"`, etc.) son distintos a los display-names de bucket (`"Atención del personal"`, `"Tiempos y espera"`, `"Cajeros (ATM)"`) **por diseño de `01 §6`** — el bucket es una etiqueta de UI, no el nombre del L1. No requiere acción.

`core/src/core/schemas.py` no referencia códigos L1 directamente (sólo DTOs de NPSGroup, Polarity, ClassificationSource), por lo que no hay conflicto.

**Estado:** Sin discrepancia. Anotado para trazabilidad.

---

## 2026-05-21 — M1: firma de `parse_tsv` vs. necesidad de reportar inválidas (RESUELTO)

**Decisión/contrato afectado:** `02_M1_datos.md` (Entregables y Tests requeridos §13.5–§13.7) y `01_contratos_compartidos.md §4` (`VerbalizationRow`).

**Lo que el contrato decía:** El plan M1 declaraba la firma `core.parser.parse_tsv(path: Path) -> Iterator[VerbalizationRow]`, pero al mismo tiempo exigía que el parser **reportara** filas inválidas (menos de 6 columnas, `nps_rate` fuera de rango, `nps_group` con typo, etc.) y que el loader las contara en `LoadReport.rows_invalid`.

**Lo que la sesión hizo:** El parser yield-ea `ParsedRow` (dataclass interno con `is_valid`, `error`, `row: VerbalizationRow | None`, `response_date_iso`, `verbatim_clean`). Las filas válidas exponen su `VerbalizationRow` en `.row`; las inválidas llevan motivo. El loader consume `ParsedRow` directamente. El DTO público `VerbalizationRow` (frozen en `schemas.py`) no se tocó.

**Razón:** Yield-ear sólo `VerbalizationRow` obligaría a perder información para los conteos del `LoadReport` o a usar un canal lateral (logging) para "reportar". `ParsedRow` mantiene el contrato del DTO público intacto y hace contables las inválidas.

**Resolución:** Aceptado `Iterator[ParsedRow]` como firma autoritativa. `02_M1_datos.md` actualizado para reflejar la firma real con descripción del dataclass interno. El DTO público `VerbalizationRow` permanece sin cambios — sigue siendo el tipo expuesto en `ParsedRow.row` cuando `is_valid=True`.

---

## 2026-05-21 — M1: `LoadReport.already_processed` no existe en el DTO congelado (RESUELTO)

**Decisión/contrato afectado:** `02_M1_datos.md` (sección "LoadReport") y `01_contratos_compartidos.md §4` (`LoadReport`).

**Lo que el contrato decía:** El plan M1 declaraba "Adicionalmente expone una propiedad `already_processed: bool` (no en el schema persistido, sólo en el DTO) derivada de la existencia previa del `sha256`." Pero el DTO en `core/src/core/schemas.py` (stub congelado de Etapa 0) **no** declaraba ese campo.

**Lo que la sesión hizo originalmente:** No modificó el DTO. El caso "archivo ya procesado" era detectable por el caller con `report.rows_inserted == 0 and report.rows_duplicated == report.rows_total`. Los tests de loader verificaban esa condición en lugar de `already_processed=True`.

**Resolución:** Añadido `already_processed: bool = False` al DTO `LoadReport` en `core/src/core/schemas.py` y reflejado en `01_contratos_compartidos.md §4`. El loader lo pobla con `True` cuando el `sha256` ya existía y con `False` cuando es un archivo nuevo. Test de loader extendido para validar el campo.

---

## 2026-05-21 — M2b: fallback emite categoría con `is_classifiable=False` (contradicción interna del doc M2b)

**Decisión/contrato afectado:** `04_M2b_clasificador.md` §10.II vs. §11 / §14.10, y `01_contratos_compartidos.md §4` (`ClassificationResult`).

**Lo que el doc M2b dice (contradictorio internamente):**

- §10.II declara: cuando `len(text_clean) < MIN_TEXT_LEN_CLASSIFIABLE` ⇒ `is_classifiable=False, categories=[]`.
- §11 ("Regla de fallback") manda emitir L1=15/L2=15.1 cuando `text_clean < 10` chars (o L1=14/L2=14.1-14.2 según polaridad), sin excepción para `is_classifiable=False`.
- §14.10 ("KPI de cobertura") exige que **toda verbalización tenga al menos una fila en `classifications`** (cobertura 100%), incluso las no clasificables.

`01_contratos_compartidos.md §4` declara `is_classifiable: bool` y `categories: list[CategoryPrediction]` como campos **independientes**; no prohíbe categorías cuando `is_classifiable=False`.

**Lo que la sesión implementó:**

`engine/src/engine/pipeline.py:155-190` aplica la lectura §11 + §14.10:

1. Calcula `is_classifiable = len(text_clean) >= MIN_TEXT_LEN_CLASSIFIABLE` (umbral 5).
2. Si `is_classifiable=False`, salta embedding/inferencia y deja `categories=[]`.
3. Antes de devolver, **todo** registro con `categories == []` (sea por `is_classifiable=False` o por probas bajas) recibe `_fallback_category(...)` con `confidence=0.0`, que emite L1∈{14,15} ("Otros" en `ui_buckets`).
4. `persist_classification` marca esas filas con `source='fallback'` (vs. `'classifier'`).

**Razón:** Cumplir el KPI §14.10 (cobertura 100% en `classifications`) y mantener la métrica de §10.II ("`is_classifiable=False`" sigue siendo señal cruda de "texto inservible para el modelo"). El campo `is_classifiable` se preserva como flag observacional; el campo `categories` deja de ser vacío para satisfacer la cobertura.

**Por qué no rompe consumidores:**

- M3 (`analytics/`) no consulta `is_classifiable`; agrega por `ui_bucket` y excluye explícitamente L1=14,15 (bucket "Otros") en `CAUSE_BUCKETS`, `STRENGTH_BUCKETS` y `BUCKET_KEYWORDS`. Las filas de fallback no aparecen en causes/strengths/impact.
- M5 (`web/`) consume DTOs ya agregados por M3; nunca ve la categoría cruda.
- Cero tests aguas abajo asumen `is_classifiable=False ⇒ categories=[]`.

**Resolución:** Adoptada la lectura §11 + §14.10 (fallback siempre, incluso si `is_classifiable=False`). §10.II queda **obsoleta** en este punto: el código y la cobertura mandan. `01_contratos_compartidos.md §4` no necesita cambios — los campos son independientes y compatibles con esta lectura. Esta entrada documenta la divergencia; futuros consumidores deben asumir que `is_classifiable=False` puede coexistir con una `categories` no vacía (donde la fila se distingue por `source='fallback'` y `confidence=0.0`).

---
