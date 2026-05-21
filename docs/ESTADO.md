# Estado del proyecto — sentiment-analysis-banamex

> **Lee este archivo primero cuando arranques una sesión nueva.** Es la fuente de verdad viva del proyecto entre sesiones. CLAUDE.md describe **qué es** el proyecto (estable); este archivo describe **dónde va** (volátil, se actualiza después de cada milestone).

**Última actualización:** 2026-05-21 (cierre de pendientes M1 + dep jsonschema, antes de lanzar Etapa 2)
**Main HEAD:** `da5958c` (docs(plan): actualizar firma parse_tsv y cerrar entradas M1 resueltas)
**Convención de actualización:** Claude actualiza este archivo después de cada milestone (cerrar PR, cerrar etapa, tomar decisión de contrato, descubrir convención operacional). Commit `docs(estado): ...`.

---

## Etapa actual

**Etapa 2 — Lista pero no lanzada.** Se esperan 2 sesiones paralelas: M2b (clasificador supervisado) y M4 (API FastAPI). Los worktrees deben recrearse desde main `da5958c` (los anteriores estaban en `d059973`, antes de los fixes de contrato M1 y la dep `jsonschema`).

Plan de orquestación completo: `~/.claude/plans/nuestro-plan-de-implementaci-n-misty-walrus.md` (no se versiona — vive en config local de Claude).

```
Etapa -1  ✓  Bootstrap git + GitHub privado                       (main, e2997d7)
Etapa 0   ✓  Setup de contratos y stubs                           (PR #1 → 9d64f01)
Etapa 1   ✓  M1, M2a, M3, M5 paralelos                            (PRs #2/3/4/5)
Etapa 2   ⏳ M2b, M4 paralelos                                    (worktrees listos)
Etapa 3   ⏸  M6 integración Docker + scripts + demo               (espera Etapa 2)
```

---

## Worktrees activos

```
/Users/etegi/Documents/personal/sentiment-analysis-banamex  d059973 [main]
/Users/etegi/Documents/personal/sentiment-wt-m2b            d059973 [feat/m2b-classifier]
/Users/etegi/Documents/personal/sentiment-wt-m4             d059973 [feat/m4-api]
```

Convención: los worktrees viven **fuera** del repo principal (no pueden vivir adentro — git lo rechaza). Cuando se cierra un PR de un worktree, removerlo con `git worktree remove <path>` y eliminar la rama local con `git branch -D <branch>`.

---

## PRs

### Mergeados

| PR | Módulo | Merge commit | Fecha |
|---|---|---|---|
| #1 | Etapa 0 — setup de contratos | `9d64f01` | 2026-05-21 |
| #2 | M1 — core de datos | `d059973` | 2026-05-21 |
| #3 | M2a — anotador LLM + extractores | `e658de6` | 2026-05-21 |
| #4 | M3 — capa de analytics | `bcd0418` | 2026-05-21 |
| #5 | M5 — frontend React SPA | `ea3f0b8` | 2026-05-21 |

### Abiertos

(Ninguno actualmente. Próximos: PRs de M2b y M4 cuando se lancen las sesiones de Etapa 2.)

---

## Próximos pasos

1. **Lanzar sesiones M2b y M4 de Etapa 2** (paralelas, en sus worktrees).
   - Prompts disponibles en el plan de orquestación líneas 378-463, o reconstruibles desde `docs/plan_implementacion/{04_M2b_clasificador.md,06_M4_api.md}`.
   - M2b necesita correr `engine.cli annotate-sample` con golden set pequeño (size 500) antes de entrenar.
   - M4 puede usar `engine.mocks.classify_mock()` hasta que M2b se mergee; luego ajustar a `engine.pipeline.classify_batch()`.

2. **Después de mergear M2b y M4** → lanzar Etapa 3 (M6 integración Docker + scripts + demo, sesión única).

---

## Decisiones que sobrescriben docs/planes anteriores

| Fecha | Decisión | Origen |
|---|---|---|
| 2026-05-21 | DTO `LoadReport` ampliado con `already_processed: bool = False`. Cierra pendiente M1. | Commit `da5958c` (commit 2 del bundle: `feat(core): ...`) |
| 2026-05-21 | Firma autoritativa de `parse_tsv` actualizada a `Iterator[ParsedRow]` (dataclass interno con `is_valid`/`error`/`row`). Cierra pendiente M1. | Commit `da5958c` (commit 3 del bundle: `docs(plan): ...`) |
| 2026-05-21 | `jsonschema>=4.0` añadido como dependencia de `engine/pyproject.toml` (lo importa `engine.annotator`). | Commit `da5958c` (commit 1 del bundle: `chore(engine): ...`) |
| 2026-05-21 | `docs/taxonomia_revisada.md` reemplazado por la versión autoritativa del cliente. El archivo de propuesta MVP previa se preserva como `docs/MVP Hackathon.md`. | Commit `ae3b19b` |
| 2026-05-21 | Resumen volumétrico interno de la taxonomía corregido a 15 L1 / 45 L2 / 82 L3 (no 48 / ~90 como decía la propuesta). | Commit `ae3b19b` |
| 2026-05-19 | Git se inicializó como Etapa -1 aunque `00_decisiones_tecnicas.md §26` decía "no reiniciar git". Decisión del usuario al aprobar el plan de orquestación. | `contracts_issues.md` (2026-05-19, Etapa 0) |
| 2026-05-19 | `docs/originales/Sentiment_analysis_original.zip` añadido a `.gitignore` (contiene corpora sensibles de Banamex). | `contracts_issues.md` (2026-05-19, Etapa 0) |

---

## Pendientes que requieren decisión del usuario

(Ninguno actualmente. Los 3 pendientes anteriores — firma `parse_tsv`, `already_processed`, dep `jsonschema` — fueron resueltos en commit `da5958c` con la opción recomendada por Claude.)

---

## Convenciones operacionales (lecciones aprendidas)

### Entorno Python

- **Usar `/opt/homebrew/bin/python3.12`**, no el del sistema (`/usr/bin/python3` es 3.9.6 y los `pyproject.toml` requieren `>=3.12`).
- Para correr la suite global desde main: `python3.12 -m venv .venv && source .venv/bin/activate && pip install -e core/ -e engine/ -e analytics/ && pip install pytest jsonschema`. `.venv/` está en `.gitignore`.

### Git

- **Worktrees viven fuera del repo**: `~/Documents/personal/sentiment-wt-<modulo>`. Git no permite que un worktree viva dentro del repo padre.
- **`gh pr merge --delete-branch` falla cosméticamente** cuando el worktree de esa rama sigue activo (mensaje `cannot delete branch used by worktree`). El merge en GitHub sí se hace; basta con `git worktree remove <path>` y `git branch -D <branch>` después.
- **Al mergear PRs de Etapa N a main**, esperar 2 tipos de conflicto:
  - `docs/plan_implementacion/contracts_issues.md` — concatenar entradas de ambas ramas, mantener orden cronológico.
  - `docs/taxonomia_revisada.md` (si el PR fue creado antes de `ae3b19b`) — `git checkout origin/main -- docs/taxonomia_revisada.md`.

### Aislamiento entre sesiones paralelas

- **No leer M-docs de otros módulos.** Cada sesión lee solo `README + 00 + 01 + su M-doc`.
- **No tocar stubs congelados de Etapa 0** sin documentar en `contracts_issues.md`.
- **No tocar archivos fuera del paquete asignado.**

### Datos sensibles

- `data/raw/*.txt` está en `.gitignore`. **Nunca commitear** los corpora reales de Banamex.
- `docs/originales/` también en `.gitignore` (contiene el ZIP original con los corpora).
- Fixtures de tests deben ser **sintéticas y determinísticas**, no extractos de corpora reales.

---

## Referencias rápidas

| Archivo / ruta | Contenido |
|---|---|
| `CLAUDE.md` | Spec estable del proyecto (estructura, stack, convenciones permanentes) |
| `docs/ESTADO.md` (este archivo) | Estado vivo del proyecto entre sesiones |
| `docs/plan_implementacion/README.md` | Mapa del plan de implementación modular |
| `docs/plan_implementacion/00_decisiones_tecnicas.md` | Contrato congelado: decisiones técnicas |
| `docs/plan_implementacion/01_contratos_compartidos.md` | Contrato congelado: schema, DTOs, endpoints |
| `docs/plan_implementacion/contracts_issues.md` | Dudas y resoluciones de contratos |
| `docs/taxonomia_revisada.md` | Taxonomía autoritativa del cliente Banamex |
| `docs/MVP Hackathon.md` | Propuesta inicial MVP (preservada, no operativa) |
| `~/.claude/plans/nuestro-plan-de-implementaci-n-misty-walrus.md` | Plan de orquestación paralela con prompts por sesión |
