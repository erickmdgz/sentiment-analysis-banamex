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

## 2026-05-21 — M1: firma de `parse_tsv` vs. necesidad de reportar inválidas

**Decisión/contrato afectado:** `02_M1_datos.md` (Entregables y Tests requeridos §13.5–§13.7) y `01_contratos_compartidos.md §4` (`VerbalizationRow`).

**Lo que el contrato dice:** El plan M1 declara la firma `core.parser.parse_tsv(path: Path) -> Iterator[VerbalizationRow]`, pero al mismo tiempo exige que el parser **reporte** filas inválidas (menos de 6 columnas, `nps_rate` fuera de rango, `nps_group` con typo, etc.) y que el loader las cuente en `LoadReport.rows_invalid`.

**Lo que la sesión hizo:** El parser yield-ea `ParsedRow` (dataclass interno con `is_valid`, `error`, `row: VerbalizationRow | None`, `response_date_iso`, `verbatim_clean`). Las filas válidas exponen su `VerbalizationRow` en `.row`; las inválidas llevan motivo. El loader consume `ParsedRow` directamente. El DTO público `VerbalizationRow` (frozen en `schemas.py`) no se tocó.

**Razón:** Yield-ear sólo `VerbalizationRow` obligaría a perder información para los conteos del `LoadReport` o a usar un canal lateral (logging) para "reportar". `ParsedRow` mantiene el contrato del DTO público intacto y hace contables las inválidas. Es además lo que la propia spec sugiere implícitamente en su ejemplo `_normalize_row(row, row_num)`.

**Resolución del usuario:** _(pendiente)_

---

## 2026-05-21 — M1: `LoadReport.already_processed` no existe en el DTO congelado

**Decisión/contrato afectado:** `02_M1_datos.md` (sección "LoadReport") y `01_contratos_compartidos.md §4` (`LoadReport`).

**Lo que el contrato dice:** El plan M1 dice "Adicionalmente expone una propiedad `already_processed: bool` (no en el schema persistido, sólo en el DTO) derivada de la existencia previa del `sha256`." Pero el DTO en `core/src/core/schemas.py` (stub congelado) **no** declara ese campo.

**Lo que la sesión hizo:** No se modificó el DTO. El caso "archivo ya procesado" es detectable por el caller con `report.rows_inserted == 0 and report.rows_duplicated == report.rows_total`. Los tests de loader verifican esa condición en lugar de `already_processed=True`.

**Razón:** El prompt de la sesión dijo "los stubs ya existen ... respétalos como contrato congelado". Modificar `schemas.py` para agregar el campo violaría esa instrucción. La invariante semántica se preserva por inferencia.

**Resolución del usuario:** _(pendiente)_

---
