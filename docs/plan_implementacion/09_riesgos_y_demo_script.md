---
tipo: riesgos-y-demo
tags:
  - plan-implementacion
  - cierre
---

# 09 — Riesgos del proyecto y guion de la demo

Este documento concentra los riesgos agregados del proyecto, el guion paso a paso de la demo, los riesgos específicos del día de la presentación y el plan B si algo falla en vivo. Es el referente operativo de cierre: cuando todos los módulos están integrados, esta es la guía que se ejecuta.

Convenciones:

- Probabilidad: Baja, Media, Alta.
- Impacto: Bajo, Medio, Alto, Crítico.
- Módulo dueño: M1 (datos), M2a (anotador LLM + extractores), M2b (clasificador supervisado), M3 (analytics), M4 (API), M5 (frontend), M6 (orquestación/empaquetado), o "Todos".

---

## Sección 1: Riesgos agregados del proyecto

| # | Riesgo | Probabilidad | Impacto | Mitigación | Módulo dueño |
|---|---|---|---|---|---|
| 1 | Tiempo de anotación con LLM local excede ventana operativa razonable | Media | Medio | Cap defensivo a 12 horas wall-clock por corrida en `engine.annotator`; abortar si excede; sample reducido como fallback (3,000 verbalizaciones); caché en disco permite reanudar | M2a |
| 2 | Tiempo de inferencia masiva (~3 horas CPU para 469k) demasiado lento para el timeline | Media | Alto | Procesar todo offline en `scripts/preprocess_corpora.py` antes de la demo; la demo solo usa la DB pre-procesada y carga un archivo pequeño en vivo | M2b / M6 |
| 3 | Cobertura del clasificador < 95% en clases con poca data | Alta | Medio | Fallback a "Genérico" / "Otros" en `engine.pipeline.classify()` garantiza cobertura 100% formal; M3 reporta clasificaciones por bucket aunque algunas vengan por fallback | M2b |
| 4 | F1 macro bajo en L2 raras | Alta | Bajo | No es KPI duro del reto; `class_weight='balanced'` mitiga parcial; documentar métricas honestamente en `classifier_runs` | M2b |
| 5 | Encoding de los TSV falla al parsear filas aisladas con bytes no estándar | Baja | Bajo | Apertura como `latin-1` (cubre 256 bytes); fallback `errors='replace'` con log de fila y `record_id` | M1 |
| 6 | Schema SQLite cambia tarde y rompe módulos consumidores | Media | Alto | Schema fijo en `01_contratos_compartidos.md §2`; cualquier cambio pasa por el usuario y obliga a regenerar el `.db` | Todos |
| 7 | Inconsistencia entre nombres de DTO en `analytics` vs `api` | Media | Medio | `analytics.schemas` manda (§12 contratos); `api/models_api.py` re-exporta sin renombrar | M3 / M4 |
| 8 | Frontend muestra datos mock en la build de demo de producción | Media | Alto | Toggle `VITE_USE_MOCKS=false` en build de prod; verificar en pre-flight con smoke test de UI | M5 |
| 9 | Sucursales con < 30 respuestas dan métricas ruidosas | Alta | Bajo | Mostrar "Datos insuficientes" en vista de sucursal cuando `total_responses < 30`; M3 expone `total_responses` en `NPSSummary` | M3 / M5 |
| 10 | Falsos positivos en personal mencionado (palabras como Banamex, México, Citi se interpretan como nombres) | Media | Bajo | Lista negra explícita en `engine.extractors`; tests unitarios cubren los casos críticos | M2a |
| 11 | Polaridad inferida del NPS confunde a evaluadores ("un Promotor con queja específica clasifica como pos") | Media | Bajo | Banner visible en UI: "Polaridad inferida del NPS del cliente"; documentado en §8 decisiones técnicas | M5 |
| 12 | Objetivos sintéticos cuestionados por el jurado | Media | Bajo | Banner visible "Objetivos NPS sintéticos para demo" en toda vista con brecha; fórmula documentada en §15 decisiones técnicas | M5 / M1 |
| 13 | Upload en runtime supera timeout de FastAPI (60s) con archivos grandes | Media | Medio | `BackgroundTasks` + polling vía `GET /upload/{file_id}/status` si archivo > 30k filas; documentado en §22 decisiones técnicas | M4 |
| 14 | Build de Docker falla por dependencia transitiva incompatible | Baja | Alto | Fijar versiones mínimas en cada `pyproject.toml`; documentar versión exacta funcional en este archivo cuando suceda | M4 / M5 / M6 |
| 15 | Sentence-transformer descargado (~120 MB) en cada build de Docker | Media | Bajo | Cachear el modelo en una layer separada del Dockerfile; alternativa: pre-descargar a `data/models/` y bind-mount | M6 |
| 16 | Demo en una máquina sin Docker | Baja | Alto | Documentar en `README_DEMO.md` cómo correr sin Docker como fallback (`uvicorn` + `npm run dev`) | M6 |
| 17 | Frontend Tailwind/shadcn inconsistente entre componentes | Media | Bajo | Componentes shadcn primitives son fuente única; design tokens centralizados en `tailwind.config.ts`; revisión visual antes de demo | M5 |
| 18 | Tiempo de query en endpoints > 500ms al cargar la vista nacional | Media | Bajo | Cachear con `lru_cache` sobre funciones de M3 o materializar agregados; medir con smoke test antes de demo | M3 / M4 |
| 19 | Sesiones en paralelo divergen porque alguien edita `01_contratos_compartidos.md` sin coordinación | Media | Alto | Convención: contratos solo cambian con aprobación del usuario; las dudas van a `contracts_issues.md` y se integran al final | Todos |
| 20 | Una sesión queda bloqueada esperando un módulo del que depende | Alta | Medio | Mocks declarados en cada paquete (`engine.mocks`, MSW handlers en `web/src/mocks/`, fixtures pytest en `core/tests/fixtures/`); cada módulo puede arrancar día 1 | Todos |
| 21 | Auth mock se interpreta como credencial real por alguien que pruebe | Baja | Bajo | Banner "Demo del Hackathon — autenticación simulada" visible en `LoginPage`; cualquier usuario/contraseña funciona | M4 / M5 |
| 22 | Datos sensibles de Banamex se commitean por error | Baja | Crítico | `data/raw/` ya está en `.gitignore`; M6 verifica que `.env` no entre al staging si el repo tiene git; pre-commit manual previo a cualquier push | M6 |
| 23 | Pre-procesamiento de los corpora se interrumpe a mitad del preprocess (5-7 horas) | Media | Medio | Idempotencia: cada fase (`annotate`, `train`, `predict`, `extract`) detecta lo hecho consultando `annotation_runs`, `classifier_runs` y la tabla `classifications`; reanudable con flags `--force-*` para forzar fases puntuales | M6 |
| 24 | Cliente OpenAPI desincronizado entre M4 y M5 | Media | Medio | `scripts/generate_openapi_client.sh` se ejecuta antes de cualquier build de M5; documentado en §10 contratos | M6 |
| 25 | El golden set queda con sesgo temporal (meses sin muestra suficiente) | Media | Bajo | Estratificación por mes en la muestra (§6 decisiones); si una celda tiene menos filas que la cuota, compensar con detractores aleatorios | M2a |
| 26 | Lockfiles ausentes generan diferencias entre máquinas de desarrollo | Media | Bajo | Versiones mínimas declaradas en cada `pyproject.toml` (Anexo B decisiones); documentar versión exacta funcional cuando rompa | Todos |
| 27 | El parser TSV mal-interpreta una columna porque el delimitador o el encoding cambian entre los 3 corpora | Baja | Alto | Parser robusto en `core.parser`: detecta delimitador y cuenta columnas por archivo; loguea encabezado real vs esperado | M1 |
| 28 | El dedup por `record_id` falla porque un archivo trae IDs colapsados o nulos | Baja | Medio | `core.loader` valida unicidad antes del INSERT; filas sin `record_id` válido caen en `rows_invalid` y se reportan en `LoadReport` | M1 |

---

## Sección 2: Guion paso a paso de la demo

Duración total objetivo: 5 minutos. Sesión arranca con `docker compose up -d` ya ejecutado y la pre-flight checklist (Sección 4) verde.

**0:00 – 0:30 — Apertura**

- La audiencia entra a la app en `http://localhost:3000`.
- Pantalla de login. El presentador menciona: "Demo del Hackathon Banamex CX. Cualquier credencial es válida — la autenticación está simulada para representar la experiencia ejecutiva, no para gestionar usuarios reales".
- Ingresa credenciales arbitrarias (ej. `demo` / `demo`). Redirige a `/upload`.

**0:30 – 1:00 — Upload (mostrar capacidad multisucursal incremental)**

- Pantalla muestra los archivos ya cargados (carrusel de los 3 corpora pre-cargados con `seed_db.py` durante el pre-procesamiento offline).
- El presentador menciona: "El sistema carga uno o varios archivos `.txt` con respuestas de múltiples sucursales y los integra al conjunto acumulado, evitando duplicados con `RecordId`. Aquí ya están los 3 corpora del reto cargados".
- Click en "Continuar a vista nacional".

**1:00 – 2:30 — Vista nacional YTD**

- Pantalla muestra hero con NPS actual, objetivo nacional, brecha y total de respuestas.
- El presentador menciona: "NPS actual de [X], objetivo nacional de [Y], brecha de [Z] puntos. Los objetivos son sintéticos para fines de demo, como indica el banner".
- Distribución promotores/pasivos/detractores: "X% promotores, Y% pasivos, Z% detractores".
- Tendencia mensual: señalar el mes con mayor caída o mejora.
- Top causas de detracción: "El principal punto de fricción es [bucket]. Las 5 causas principales explican Z% del total de quejas".
- Top fortalezas: "Lo que más reconoce el cliente promotor es la amabilidad del personal".
- Sucursales críticas: tabla con las 10 sucursales más críticas, mostrando qué condición disparó cada una (NPS bajo, brecha vs objetivo, % detractores, deterioro mes-a-mes).
- Impacto en NPS por categoría: "Si resolviéramos tiempos y espera, ganaríamos N puntos de NPS a nivel nacional".
- Voz de los pasivos: bloque corto. "Los pasivos cercanos a promotor (NPS=8) hablan de X; los cercanos a detractor (NPS=7) hablan de Y".

**2:30 – 3:30 — Drill-down a sucursal crítica**

- Click en la primera sucursal de la tabla crítica.
- Pantalla muestra vista YTD de la sucursal.
- Si la sucursal no tiene objetivo: el presentador menciona el banner "Esta sucursal no tiene objetivo NPS configurado".
- Mostrar palabras frecuentes del grupo Detractor: "Las palabras que más se repiten son espera, turno, app...".
- Mostrar 2-3 comentarios representativos con bucket + NPS + fecha.
- Mostrar personal mencionado: "Diana tiene 8 menciones positivas, el gerente tiene 3 menciones negativas".

**3:30 – 4:30 — Comparación de meses**

- Volver a vista nacional.
- Ir a `/national/compare`.
- Seleccionar dos meses (ej. enero 2026 vs marzo 2026).
- Mostrar tabla con cambios: NPS subió/bajó N puntos.
- Causas que subieron / bajaron en participación.
- Sucursales que más mejoraron / empeoraron entre los dos cortes.

**4:30 – 5:00 — Sección admin POC y cierre**

- Click en sidebar → "Administración".
- Mostrar sección admin con placeholders: archivos cargados, corridas de anotación, corridas del clasificador.
- El presentador menciona: "La interfaz contempla las secciones administrativas: gestión de usuarios, monitoreo, validación de archivos. Estas quedan como representación POC para el MVP; en una versión posterior cada una se implementa completa".
- Cierre: "El motor que clasifica los comentarios es híbrido: un clasificador supervisado entrenado sobre una muestra de 5,000 verbalizaciones anotadas con un LLM que corre 100% local en la máquina del operador (Ollama + Qwen 2.5). Una vez entrenado, el clasificador procesa cualquier archivo nuevo offline, sin dependencia de internet ni envío de datos a terceros. El sistema escala a otros productos y canales repitiendo la anotación con otra taxonomía. Sin dependencia de internet en runtime, sin costo por inferencia, sin riesgo de fuga de datos sensibles".

---

## Sección 3: Riesgos del día de la demo

Tabla diagnóstica para resolver en vivo. Cada fila tiene síntoma observable, causa probable y acción inmediata. Si la acción inmediata no resuelve en < 60 segundos, ir a la Sección 4 (plan B).

| # | Síntoma | Causa probable | Acción inmediata |
|---|---|---|---|
| 1 | Frontend muestra "Error de red" al cargar cualquier vista | La API no arrancó o murió | `docker compose restart api`; revisar `docker compose logs api --tail=50` |
| 2 | Vista nacional carga vacía (NPS=0, sin sucursales) | DB sin datos | Verificar que `data/processed/banamex.db` existe y no está vacío; correr `python scripts/seed_db.py` si se perdió |
| 3 | NPS muestra `null` o `NaN` en alguna tarjeta | División por cero en grupo con 0 respuestas | Bug: la UI debería mostrar "Datos insuficientes"; reportar a consola y avanzar a la siguiente vista |
| 4 | Login no redirige tras enviar credenciales | Token mal generado o `JWT_SECRET` ausente | Revisar `JWT_SECRET` en `.env`; `docker compose logs api` para ver el traceback; `docker compose restart api` |
| 5 | Carga de archivo falla con 500 | Permisos del volumen Docker sobre `data/` | `chmod -R 755 data/`; revisar `docker compose logs api` |
| 6 | Latencia > 5s en vista nacional | DB sin índices, consulta sin caché o el embedder se recarga | Verificar que los índices del schema están creados (`sqlite3 data/processed/banamex.db ".indexes"`); fallback a fixtures de MSW si persiste |
| 7 | Comparación de meses devuelve 422 | El mes seleccionado no existe en la base | Recargar la página; el selector solo debe mostrar meses disponibles vía `/validation` |
| 8 | Personal mencionado vacío en toda la vista de sucursal | Los extractores rule-based no corrieron sobre los corpora | Ejecutar `python -m engine.cli extract-metadata --all` y refrescar |
| 9 | Sidebar muestra rutas pero al hacer click no carga nada | TanStack Query cacheó un error previo | Forzar refresh con Cmd+Shift+R; si persiste, `docker compose restart web` |
| 10 | El selector de sucursal devuelve lista vacía al buscar | Endpoint `/branches?q=...` rompe con caracteres especiales | Buscar con prefijo simple (`A-1`); reportar a consola |
| 11 | Tabla de sucursales críticas muestra solo placeholder | M3 no encontró sucursales que disparen las 4 condiciones | Esperado si la base es muy uniforme; mencionar verbalmente y avanzar |
| 12 | El gráfico de tendencia se ve plano | Solo hay un mes cargado | Verificar `/validation` reporta múltiples meses; si no, reseed |
| 13 | Banners "objetivos sintéticos" no aparecen | Bug de M5 en el render condicional | Mencionar verbalmente al jurado; reportar en post-mortem |
| 14 | Docker se queda colgado durante `up` | Otro proceso usa el puerto 8000 o 80 | `lsof -i :8000` y `lsof -i :80`; matar proceso o cambiar puertos en `docker-compose.yml` |
| 15 | El smoke test del pre-flight falla en `/upload` | Volumen Docker no monta `data/` correctamente en macOS | Verificar el path absoluto del volumen en `docker-compose.yml`; restart |

---

## Sección 4: Plan B si algo falla en vivo

Tres niveles de degradación, en orden de preferencia.

**Nivel 1 — El backend cae o responde con error**

- Acción: levantar `web` con MSW activado (`VITE_USE_MOCKS=true`).
- Comando rápido (con la imagen ya construida): `docker compose stop web && VITE_USE_MOCKS=true docker compose up -d web`.
- El frontend funciona contra `web/src/mocks/handlers.ts` con fixtures sintéticas que validan los DTOs de §4 contratos.
- La demo sigue "como si el backend respondiera".
- Disclaimer honesto al jurado si pregunta: "estamos viendo data de respaldo, el backend tuvo un incidente durante el deploy de demo. La arquitectura completa con backend real está en el repo".

**Nivel 2 — DB corrupta, faltante o desincronizada**

- Acción: bajar la app, regenerar la DB con `python scripts/seed_db.py` (que copia un snapshot pre-procesado de `data/processed/banamex.db`), levantar de nuevo.
- Comando: `docker compose down && python scripts/seed_db.py && docker compose up -d`.
- Si la regeneración tarda > 1 minuto o vuelve a fallar, pasar a Nivel 1.

**Nivel 3 — Docker entero falla o la máquina no soporta el stack**

- Acción: mostrar el video grabado de la demo (responsabilidad del presentador, fuera del plan técnico).
- Explicar la arquitectura sobre las slides del entregable.
- Mostrar el repo de código si el jurado pide ver implementación.

---

### Pre-flight checklist

Correr 1 hora antes de la demo, en orden:

- [ ] `docker compose up -d` arranca sin errores en `docker compose ps`.
- [ ] `bash scripts/smoke_test.sh` pasa todas sus assertions.
- [ ] `curl http://localhost:8000/healthz` devuelve `{"status": "ok", ..., "classifier_loaded": true}`.
- [ ] Abrir `http://localhost:3000/login`: la pantalla se renderiza sin errores en consola del navegador.
- [ ] Login con credenciales arbitrarias funciona y redirige a `/upload`.
- [ ] La vista de upload muestra los 3 corpora pre-cargados.
- [ ] La vista nacional YTD muestra datos no vacíos: NPS numérico, distribución, tendencia, causas, fortalezas, sucursales críticas con al menos una fila.
- [ ] La vista de al menos 3 sucursales distintas carga correctamente (incluyendo una sin objetivo configurado, si existe en la base).
- [ ] La comparación entre 2 meses arbitrarios funciona y muestra cambios.
- [ ] La sección admin POC se ve íntegra (archivos cargados, corridas de anotación, corridas del clasificador).
- [ ] El banner "Objetivos NPS sintéticos para demo" aparece en al menos la vista nacional YTD.
- [ ] El banner "Polaridad inferida del NPS del cliente" aparece como tooltip en causas/fortalezas.
- [ ] `data/raw/`, `.env` y `data/processed/banamex.db` están en disco y no están en git.
- [ ] Existe el video de respaldo (Nivel 3 del plan B) y se sabe dónde está.
