# Plan de implementación — MVP Hackathon CX Banamex

Esta carpeta contiene el plan de implementación detallado del MVP. Es la fuente única de verdad para todas las sesiones de Claude que vayan a implementar código del proyecto.

## Propósito

El proyecto `sentiment-analysis-banamex` se construye en 7 módulos paralelizables. Cada módulo puede ser implementado por **una sesión de Claude independiente** que trabaja en aislamiento. Para que ese paralelismo funcione sin colisiones, todos los contratos entre módulos están fijados de antemano en estos documentos. Una sesión de implementación lee solo los archivos que le tocan, no necesita coordinarse con las demás durante el trabajo.

## Regla de lectura por sesión

Cada sesión de implementación lee **exactamente tres archivos** de esta carpeta:

1. `README.md` (este archivo) — mapa general.
2. `00_decisiones_tecnicas.md` — decisiones técnicas inmutables (stack, motor, polaridad, umbrales, etc.).
3. `01_contratos_compartidos.md` — schema SQLite, DTOs, endpoints, mapeo taxonomía→UI.
4. Su archivo de módulo (`02_M1_datos.md` a `08_M6_integracion.md`).

Adicionalmente puede consultar `docs/propuesta_inicial.md` (frontend), `docs/taxonomia_revisada.md` (clasificación), `docs/contexto_estrategico_reto_sentimientos_banamex.md` (reto). **No** lee los archivos de módulos ajenos al suyo.

## Mapa de archivos

| Archivo | Contenido | Quién lo lee |
|---|---|---|
| `README.md` | Este mapa | Todas |
| `00_decisiones_tecnicas.md` | 26 decisiones técnicas con razón/alternativa/implicación | Todas |
| `01_contratos_compartidos.md` | Estructura del proyecto, schema SQLite, DTOs, endpoints, mapeo UI | Todas |
| `02_M1_datos.md` | Núcleo de datos: parser TSV, persistencia, dedup, objetivos sintéticos | Sesión M1 |
| `03_M2a_anotador.md` | Anotador LLM local (Ollama + Qwen) + extractores rule-based de metadatos | Sesión M2a |
| `04_M2b_clasificador.md` | Clasificador supervisado L1+L2 + pipeline público | Sesión M2b |
| `05_M3_analytics.md` | Agregaciones, rankings, comparaciones, insights, impacto | Sesión M3 |
| `06_M4_api.md` | FastAPI con todos los endpoints, auth mock, upload | Sesión M4 |
| `07_M5_frontend.md` | SPA React + Vite + Tailwind + shadcn/ui, todas las pantallas | Sesión M5 |
| `08_M6_integracion.md` | docker-compose, scripts de preprocess/seed, README de demo | Sesión M6 |
| `09_riesgos_y_demo_script.md` | Riesgos agregados + guion paso a paso de la demo | Todas (lectura opcional) |
| `contracts_issues.md` | (Se crea sobre la marcha si una sesión detecta un contrato dudoso) | Usuario |

## Orden de ejecución de sesiones

```
Día 1 (mañana)   Día 1 (tarde)   Día 2 (mañana)   Día 2 (tarde)   Día 3
─────────────   ─────────────   ──────────────   ─────────────   ─────────
M1 ──────────────────────────────────────────────► DoD
M2a ─────────────────────────────────────────────► DoD
M2b ────────────────────────────────────────────────────────────► DoD
M3 ──────────────────────────────────────────────► DoD
M4 ──────────────────────────────────────────────► DoD
M5 ────────────────────────────────────────────────────────────► DoD
                                                                 M6 ─► DoD
```

Las sesiones M1, M2a, M2b, M3, M4 y M5 pueden **arrancar al mismo tiempo el día 1** porque los contratos están fijos desde el inicio. Cada sesión trabaja contra mocks de las demás hasta que los entregables reales estén disponibles. M6 es la última: integra, no implementa nuevo código de módulos.

## Tabla de dependencias y mocks

| Módulo | Depende de | Mock que usa mientras tanto |
|---|---|---|
| M1 | (ninguno) | — |
| M2a | M1 (tabla `verbalizations`) | `engine/tests/fixtures/sample_verbalizations.json` |
| M2b | M2a (golden set en `classifications`) | golden set sintético manual de 200 filas |
| M3 | M1 (tablas), M2b (`engine.pipeline.classify`) | `engine.mocks.classify_mock` + dataset sintético de 1000 filas |
| M4 | M1 (DB), M2b (pipeline), M3 (analytics) | mocks de M3 stubs + `engine.mocks` |
| M5 | M4 (`openapi.json`) | MSW handlers con fixtures sintéticas |
| M6 | M1, M2a, M2b, M3, M4, M5 (entregables) | (no trabaja contra mocks; corre al final) |

## Convenciones del repo

- **Idioma**: docs en español, código/identificadores en inglés (regla global del usuario).
- **Archivos**: kebab-case para scripts y docs (`preprocess-corpora.py`, `smoke-test.sh`); PascalCase para componentes React; snake_case para Python.
- **Funciones**: verbo en infinitivo (`load_file`, `compute_nps`, `classify`).
- **Tests**: `test_<modulo>.py` (pytest), `<componente>.test.ts` (vitest).
- **Commits** (si se reactiva git al final): Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`).
- **Branches** (si se reactiva git): `feat/m1-datos`, `feat/m2a-anotador`, etc.

## Cómo escalar a más sesiones en paralelo

El plan se puede ejecutar con menos paralelismo (1 sesión hace varios módulos en secuencia) o con más (M5 se parte en M5a `shell+upload+admin` y M5b `vistas analíticas`). Si se parte M5, ambas sub-sesiones leen el mismo `07_M5_frontend.md` y se reparten las pantallas; coordinan el `tailwind.config.ts` y los componentes shadcn como zona común.

## Cómo reportar problemas con un contrato

Si una sesión de implementación descubre que un contrato del `00` o del `01` es incorrecto o ambiguo:

1. **No modifica** el contrato.
2. Anota la duda en `docs/plan_implementacion/contracts_issues.md` (crea el archivo si no existe).
3. Sigue trabajando con el contrato vigente.
4. El usuario revisa los issues al final y decide cambios.

## Estado de los contratos

Inmutables salvo orden explícita del usuario. Cualquier sesión que cambie un contrato sin pasar por el usuario rompe el paralelismo.
