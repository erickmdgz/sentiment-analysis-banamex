---
tipo: estado-proyecto
tags:
  - fuente-de-verdad-viva
  - pivote
---

# Estado del proyecto — sentiment-analysis-banamex

> **Lee este archivo primero cuando arranques una sesión nueva.** Es la fuente de verdad viva del proyecto entre sesiones. CLAUDE.md describe **qué es** el proyecto (estable); este archivo describe **dónde va** (volátil, se actualiza después de cada milestone).
>
> Para visualización dinámica del grafo módulos / estados / dependencias en Obsidian (requiere Dataview), abre [[DASHBOARD]].

**Última actualización:** 2026-05-21 (cierre Etapa 2 — M2b y M4 mergeados, antes de lanzar Etapa 3)
**Main HEAD:** `50b7beb` (Merge pull request #6 from erickmdgz/feat/m4-api)
**Convención de actualización:** Claude actualiza este archivo después de cada milestone (cerrar PR, cerrar etapa, tomar decisión de contrato, descubrir convención operacional). Commit `docs(estado): ...`.

---

## Etapa actual

**Etapa 2 — Completa.** M2b (clasificador supervisado) y M4 (API FastAPI) mergeados. M4 fue rebaseado sobre el main post-M2b y su shim local `api._classifier_shim` fue sustituido por `engine.pipeline.classify_batch` en el mismo rebase. Próximo: lanzar Etapa 3 (M6) en un worktree único.

Plan de orquestación completo: `~/.claude/plans/nuestro-plan-de-implementaci-n-misty-walrus.md` (no se versiona — vive en config local de Claude).

```
Etapa -1  ✓  Bootstrap git + GitHub privado                       (main, e2997d7)
Etapa 0   ✓  Setup de contratos y stubs                           (PR #1 → 9d64f01)
Etapa 1   ✓  M1, M2a, M3, M5 paralelos                            (PRs #2/3/4/5)
Etapa 2   ✓  M2b, M4 paralelos                                    (PRs #7/6)
Etapa 3   ⏳ M6 integración Docker + scripts + demo               (worktree por crear)
```

---

## Worktrees activos

```
sentiment-analysis-banamex/        [main]
sentiment-wt-m6/                   [feat/m6-integration]  (por crear)
```

Los worktrees de Etapa 2 (`sentiment-wt-m2b` y `sentiment-wt-m4`) fueron removidos tras el merge. Los SHAs específicos se obtienen con `git worktree list`.

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
| #7 | M2b — clasificador supervisado + pipeline público | `ad255c2` | 2026-05-21 |
| #6 | M4 — API FastAPI (HTTP wrapper) | `50b7beb` | 2026-05-21 |

### Abiertos

(Ninguno actualmente. Próximo: PR de M6 cuando se lance la sesión de Etapa 3.)

---

## Próximos pasos

1. **Crear worktree `sentiment-wt-m6` y lanzar sesión M6 (Etapa 3).**
   - Branch: `feat/m6-integration` desde main actual (`50b7beb`).
   - Prompt en el plan de orquestación / `docs/plan_implementacion/07_M6_integracion.md` (si existe; verificar en la carpeta).
   - Alcance esperado: Docker compose (api + frontend + ollama opcional), scripts de demo end-to-end, ajuste del comando `docker build` (ver decisión 2026-05-21 sobre `-f api/Dockerfile .`).

2. **Pendiente humano antes/durante M6**: verificar `docker build` (Docker daemon estuvo apagado al cerrar M4).

3. **Para correr el clasificador real con datos reales** (no es trabajo de M6, es operativo del usuario):
   - Asegurar Ollama corriendo.
   - `python -m engine.cli annotate-sample --size 5000 --persist-db` (golden set sobre los corpora de Banamex).
   - `python -m engine.cli train --annotation-run-id <N>` → produce `data/models/classifier.joblib`.
   - `python -m engine.cli predict-all` para clasificar todas las verbalizaciones de la BD.

---

## Decisiones que sobrescriben docs/planes anteriores

| Fecha | Decisión | Origen |
|---|---|---|
| 2026-05-21 | M2b emite categoría de fallback (L1∈{14,15}, `confidence=0.0`) incluso cuando `is_classifiable=False`, satisfaciendo §11/§14.10 sobre §10.II del doc M2b. `01 §4` permite `is_classifiable=False` + `categories` no vacío como independientes. M3 (analytics) y M5 (web) excluyen L1=14,15 vía `ui_bucket="Otros"`, sin tests aguas abajo afectados. | `contracts_issues.md` (2026-05-21, M2b) |
| 2026-05-21 | `engine.mocks` no existía en main cuando M4 se implementó; M4 usó shim local `api._classifier_shim` durante Etapa 2. Tras el merge de M2b, M4 fue rebaseado y el shim sustituido por `engine.pipeline.classify_batch` (firma idéntica, parámetro opcional `classifier` kwarg-only). `_classifier_shim.py` eliminado. | `contracts_issues.md` (2026-05-21, M4 — RESUELTO) |
| 2026-05-21 | `docker build -t banamex-api ./api` (DoD de `06_M4_api.md`) es incompatible con el Dockerfile del contrato que hace `COPY core/ engine/ analytics/`. El comando correcto es `docker build -t banamex-api -f api/Dockerfile .` desde repo root. M6 ajusta `docker-compose.yml` y los scripts de demo. | `contracts_issues.md` (2026-05-21, M4) |
| 2026-05-21 | DTO `LoadReport` ampliado con `already_processed: bool = False`. Cierra pendiente M1. | Commit `da5958c` (commit 2 del bundle: `feat(core): ...`) |
| 2026-05-21 | Firma autoritativa de `parse_tsv` actualizada a `Iterator[ParsedRow]` (dataclass interno con `is_valid`/`error`/`row`). Cierra pendiente M1. | Commit `da5958c` (commit 3 del bundle: `docs(plan): ...`) |
| 2026-05-21 | `jsonschema>=4.0` añadido como dependencia de `engine/pyproject.toml` (lo importa `engine.annotator`). | Commit `da5958c` (commit 1 del bundle: `chore(engine): ...`) |
| 2026-05-21 | `docs/taxonomia_revisada.md` reemplazado por la versión autoritativa del cliente. El archivo de propuesta MVP previa se preserva como `docs/MVP Hackathon.md`. | Commit `ae3b19b` |
| 2026-05-21 | Resumen volumétrico interno de la taxonomía corregido a 15 L1 / 45 L2 / 82 L3 (no 48 / ~90 como decía la propuesta). | Commit `ae3b19b` |
| 2026-05-19 | Git se inicializó como Etapa -1 aunque `00_decisiones_tecnicas.md §26` decía "no reiniciar git". Decisión del usuario al aprobar el plan de orquestación. | `contracts_issues.md` (2026-05-19, Etapa 0) |
| 2026-05-19 | `docs/originales/Sentiment_analysis_original.zip` añadido a `.gitignore` (contiene corpora sensibles de Banamex). | `contracts_issues.md` (2026-05-19, Etapa 0) |

---

## Pendientes que requieren decisión del usuario

(Ninguno actualmente. Los 3 pendientes anteriores — firma `parse_tsv`, `already_processed`, dep `jsonschema` — fueron resueltos en commit `da5958c`. La decisión del fallback de M2b se resolvió en `0129554` registrándola en `contracts_issues.md` antes del merge.)

---

## Pendientes técnicos (no bloqueantes, para M6 o post-MVP)

Detectados durante reviews de Etapa 2; ninguno bloquea Etapa 3 ni el MVP. Registrarlos aquí para no perderlos.

**M2b / engine:**

- `trainer.train(--annotation-run-id)` no valida que el ID exista antes de entrenar. Con `PRAGMA foreign_keys=ON` (activo en `core/db.py:42`), un ID inválido hace que `_persist_classifier_run` (`engine/trainer.py:194`) explote con `IntegrityError` opaco tras 30+ min de embedding/entrenamiento. Fix sugerido: chequear existencia al inicio de `train()`.
- `engine.cli predict-all`: cursor con `stream_results=True` + segunda conexión `engine.begin()` puede contender si la BD no tiene WAL. WAL está activo en `core.db` por defecto, pero si el cliente usa una BD foránea sin WAL, hay bloqueo. Documentar o forzar WAL.
- `get_default_classifier(path=X)` no recarga si el path cambia (sólo si `_default_classifier is None` o `refresh=True`). El docstring (`engine/classifier.py:178`) lo promete; el código no lo cumple.
- Faltan tests de borde: texto > 128 tokens (límite del MiniLM-L12, trunca silenciosamente), texto con emojis/caracteres no latinos, anotaciones duplicadas en el golden set (`trainer.py:108` dedupe pero sin test).

**M4 / api:**

- Dockerfile corre como root (sin `USER appuser`). Aceptable para MVP; M6 puede agregarlo.
- Colisión de archivos temporales en uploads concurrentes: `api/src/api/routes/upload.py:55` usa `f"upload-{_safe_name(file.filename)}"`, así que dos requests con el mismo nombre se pisan. Fix sugerido: `tempfile.NamedTemporaryFile(delete=False)` o prefijar con UUID.
- `.env.example` declara `JWT_SECRET=cambia-esto-en-produccion-pero-en-mvp-da-igual`, idéntico al default de `api/src/api/settings.py:13`. Si alguien deploya sin `.env`, el secret queda hardcodeado. Aceptable en MVP pero rompe en producción.
- `docker build` no verificado por el autor de M4 (Docker daemon apagado). Pendiente humano: ejecutar `docker build -t banamex-api -f api/Dockerfile .` antes o durante M6.
- `/auth/login` sin rate-limit ni log de intentos. Coherente con MVP (cualquier user/pass válido por `00 §18`); post-MVP.

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

### Rebase de PRs entre etapas

- Cuando una etapa tiene PRs paralelos con dependencia (M4 depende de M2b vía `engine.mocks` → `engine.pipeline.classify_batch`), se mergea primero el dependee, después se rebasea el dependent sobre el nuevo main, se ajustan los imports/shims en el mismo rebase y se hace `git push --force-with-lease`.
- `--force-with-lease` requiere confirmación del usuario (regla global CLAUDE.md sobre comandos destructivos), aunque sea más seguro que `--force`.
- Tras el merge del rebase, removerlo del worktree (`git worktree remove`) y `git branch -D <branch>`. `gh pr merge --delete-branch` falla cosméticamente mientras el worktree sigue activo.

### Sincronizar el DASHBOARD de Obsidian al cerrar PRs

- `docs/DASHBOARD.md` se renderiza con Dataview leyendo el **frontmatter YAML** de cada M-doc en `docs/plan_implementacion/`. Campos relevantes: `estado` (`pendiente` / `en-progreso` / `completado`) y `pr` (número del PR mergeado).
- **Al mergear un PR de un módulo, actualizar el frontmatter del M-doc correspondiente** (no solo el ESTADO.md). Cambiar `estado:` a `completado` y añadir `pr: <N>`. El dashboard refleja el cambio sin tocarlo.
- Cuando una sesión arranca un módulo (worktree creado), si el M-doc todavía dice `estado: pendiente`, ajustar a `en-progreso` al inicio. Esto da una vista de "qué se está haciendo ahora mismo".

### Tests del API con el clasificador real

- M4 tiene un fixture autouse `_stub_classifier` en `api/tests/conftest.py` que monkeypatchea `engine.pipeline.get_default_classifier` por un stub que retorna `[[]for _ in texts]`. Resultado: `pipeline.classify_batch` aplica el fallback de M2b para todos los items y los tests del API no requieren un `.joblib` entrenado.
- Para correr el API con el modelo real, entrenarlo con `engine.cli train` y exponerlo vía `data/models/classifier.joblib` (o env `CLASSIFIER_MODEL_PATH`).
- `/healthz` reporta `classifier_loaded: bool` chequeando ese archivo.

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
