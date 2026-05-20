# 00 — Decisiones técnicas

Este archivo lista las decisiones técnicas ya tomadas y validadas para el MVP. Toda sesión de implementación lo lee antes de empezar. Cada decisión tiene cuatro partes: **Decisión** (qué se hace), **Razón** (por qué), **Alternativa descartada** (qué no se hace y por qué), **Implicación** (cómo afecta a quien implementa).

Las decisiones aquí son **inmutables durante la ejecución** salvo que el usuario las cambie explícitamente. Si una sesión de implementación cree que una decisión es incorrecta, **no la modifica**: anota la duda en `docs/plan_implementacion/contracts_issues.md` (crear si no existe) y continúa con la decisión vigente. El usuario integra los issues al final.

---

## 1. Stack backend

**Decisión**: Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.x + SQLite.

**Razón**: stack que Claude conoce a fondo y escribe con bajo riesgo de alucinación. Pydantic + FastAPI generan OpenAPI gratis, lo cual destraba M5. SQLAlchemy 2.x tiene tipado moderno.

**Alternativa descartada**: Django (overhead innecesario para MVP de hackathon), Flask (no genera OpenAPI tipado), Node/Express (peor para NLP).

**Implicación**: cada módulo Python es un paquete con `pyproject.toml`. Versiones mínimas: Python 3.12, FastAPI ≥0.110, Pydantic ≥2.6, SQLAlchemy ≥2.0.

---

## 2. Stack frontend

**Decisión**: React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui + Recharts + TanStack Query + React Router.

**Razón**: stack moderno y predecible. Vite arranca rápido. shadcn/ui da primitives sin lock-in. TanStack Query elimina la necesidad de estado global.

**Alternativa descartada**: Next.js (SSR no aporta, agrega complejidad de routing y build), Angular/Vue (Claude tiene más fluidez con React), CSS plano sin Tailwind (productividad menor).

**Implicación**: el frontend es SPA estática, servida por nginx en Docker. Token JWT en `localStorage`. URL params para sucursal seleccionada.

---

## 3. Persistencia

**Decisión**: SQLite local en `data/processed/banamex.db`. Esquema declarado en código (un solo archivo SQL en M1), sin Alembic, sin migraciones.

**Razón**: cero infraestructura, archivo copiable para mover la demo entre máquinas, suficiente para 474k filas con índices apropiados.

**Alternativa descartada**: Postgres (requiere servicio aparte, infra), DuckDB (excelente analítico pero no tiene mismo soporte ORM), JSON en disco (no soporta queries complejas).

**Implicación**: schema único definido por M1 y aplicado con `core.db.init_schema()`. Si el schema cambia durante el desarrollo, se borra el `.db` y se regenera; ningún módulo persiste datos críticos que no se puedan regenerar.

---

## 4. Motor híbrido

**Decisión**: el motor de clasificación tiene tres fases:

- **Fase A (offline, una vez)**: un LLM local (Ollama + Qwen 2.5 7B Instruct) etiqueta una muestra de 5,000 verbalizaciones contra la taxonomía completa L1+L2+L3. Produce el golden set. Los datos nunca salen de la máquina del operador.
- **Fase B (entrenamiento, una vez)**: clasificador supervisado multilabel (sentence-transformers + Logistic Regression OneVsRest) se entrena sobre el golden set. Predice solo L1+L2.
- **Fase C (inferencia, runtime)**: el clasificador entrenado clasifica las 469k verbalizaciones restantes y cualquier upload nuevo. Sin LLM en runtime.

**Razón**: combina precisión del LLM en una muestra con offline/cero-costo/baja-latencia en producción. La demo no depende de internet.

**Alternativa descartada**: LLM zero-shot en todo (caro, depende de internet, latencia alta para uploads), clasificador clásico solo (sin golden set no se puede entrenar), embeddings + reglas (precisión moderada y requiere construir prototypes a mano).

**Implicación**: M2a y M2b son módulos separados con un contrato claro entre ellos (tabla `classifications` con `source='llm_annotation'`). M2b puede arrancar contra un golden set sintético de 30 ejemplos mientras M2a corre.

---

## 5. Modelo LLM

**Decisión**: LLM local servido por Ollama. Modelo por defecto: `qwen2.5:7b-instruct` (descargado con `ollama pull qwen2.5:7b-instruct`). Inferencia vía API local `http://localhost:11434` con el cliente Python `ollama>=0.4`. Salida estructurada forzada por `format=<json_schema>` (Ollama ≥0.5).

**Razón**: los datos del reto son sensibles (Banamex) y no deben salir del equipo. Qwen 2.5 7B es multilingüe (español/inglés), corre en Apple Silicon con aceleración Metal en pocos GB de RAM, y soporta JSON Schema constrained decoding. Costo monetario cero; tiempo de procesamiento aceptable para uso offline.

**Alternativa descartada**: Anthropic Batch API con Haiku 4.5 (mejor precisión pero envía datos sensibles a un proveedor externo; descartada por política de aislamiento del reto); Llama 3.1 8B (JSON mode menos confiable en versiones disponibles vía Ollama); embeddings + similitud coseno solamente (sin paso supervisado, peor calidad en L3); modelos de OpenAI/Gemini (misma objeción que Anthropic).

**Implicación**: M2a usa el cliente `ollama` con un endpoint configurable por env (`OLLAMA_HOST`, default `http://localhost:11434`). El operador debe tener Ollama corriendo y el modelo pre-descargado antes de ejecutar `engine.cli annotate-sample`. No se requiere `ANTHROPIC_API_KEY` ni ninguna otra credencial externa.

---

## 6. Tamaño y composición de la muestra para anotación

**Decisión**: 5,000 verbalizaciones, estratificadas:

- 35% detractores (1,750 filas)
- 25% pasivos (1,250 filas)
- 40% promotores (2,000 filas)

Adicionalmente estratificadas por mes para cubrir los 16 meses disponibles (enero 2025 a abril 2026). Filtros previos: `Verbalizacion` no nula, longitud ≥ 5 caracteres tras `strip()`. Semilla aleatoria fija `random_state=42`.

**Razón**: los detractores son la minoría con mayor interés (la voz del cliente con queja es lo que mueve NPS). Los pasivos son la palanca más barata para subir NPS. Estratificar por mes garantiza que el clasificador no se sobre-ajusta a tendencias temporales.

**Alternativa descartada**: muestra aleatoria (sub-representa detractores), muestra solo de detractores (no aprende a clasificar fortalezas), muestra > 5k (tiempo de procesamiento crece linealmente sin ganancia marginal demostrada en este corpus).

**Implicación**: M2a implementa la estratificación con `pandas.groupby + sample(random_state=42)`. Si una celda (grupo × mes) tiene menos filas que la cuota, toma todas las disponibles y compensa con detractores aleatorios.

---

## 7. L3 anotado pero no predicho

**Decisión**: el LLM en M2a clasifica L1+L2+L3 en el golden set. El clasificador supervisado en M2b predice **solo L1+L2 multilabel**. L3 queda en la tabla `classifications.l3_code` para las 5k filas anotadas; las 469k restantes tienen `l3_code = NULL`.

**Razón**: ~90 hojas L3 con muestra de 5k da 30-50 ejemplos por hoja en promedio; multilabel con tan poca data fracasa. Mantener L3 en el golden set permite drill-down en comentarios anotados sin sacrificar viabilidad técnica.

**Alternativa descartada**: predecir L3 (fracaso técnico previsible), no anotar L3 (pierde detalle del golden set), colapsar L3 a L2 (pierde granularidad para drill-down).

**Implicación**: las funciones de M3 que devuelven agregaciones operan sobre L1+L2. La UI de drill-down en M5, cuando muestra un comentario individual, sí muestra L3 si está disponible.

---

## 8. Polaridad heredada del grupo NPS

**Decisión**: la polaridad de cada categoría asignada a una verbalización se hereda del grupo NPS del cliente que la dijo:

- `nps_group = 'Detractor'` → `polarity = 'neg'`
- `nps_group = 'Pasivo'` → `polarity = 'neu'`
- `nps_group = 'Promotor'` → `polarity = 'pos'`

**Razón**: implementar ABSA real (Aspect-Based Sentiment Analysis) requiere modelo aparte, datos etiquetados a nivel aspecto, y aumenta riesgo de alucinación al implementar. El grupo NPS ya es la voz del cliente sobre su experiencia global y mapea bien a la mayoría de comentarios.

**Alternativa descartada**: modelo ABSA dedicado (complejidad alta para MVP), reglas léxicas de sentimiento (frágiles en español con sarcasmo), ignorar polaridad (rompe la lógica de "causas" vs "fortalezas").

**Implicación**: la columna `classifications.polarity` se llena directamente desde `verbalizations.nps_group` en el pipeline. Una verbalización de promotor con queja específica se clasifica como `polarity='pos'`; documentar como error tolerable. **El frontend debe mostrar la nota** "Polaridad inferida del NPS del cliente" como tooltip en las vistas de causas/fortalezas.

---

## 9. Embeddings

**Decisión**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Cacheado localmente en `~/.cache/torch/sentence_transformers/`.

**Razón**: modelo ligero (~120 MB), corre en CPU sin GPU, español/inglés/multilingue. Dimensión 384, suficiente para clasificación. Calidad probada en benchmarks multilingüe.

**Alternativa descartada**: `paraphrase-multilingual-mpnet-base-v2` (mejor calidad pero 2x más pesado, lento en CPU), embeddings de OpenAI/Anthropic (dependencia externa en runtime, costo), Word2Vec o GloVe propios (entrenar es overhead, calidad inferior).

**Implicación**: M2b implementa `engine.embeddings.Embedder` que carga el modelo una vez y expone `encode(texts) -> np.ndarray`. Tiempo estimado para 5k embeddings en CPU moderna: ~2 minutos. Para 469k: ~3 horas (aceptable, corre offline en preprocess).

---

## 10. Clasificador supervisado

**Decisión**: `OneVsRestClassifier(LogisticRegression(max_iter=1000, C=1.0, class_weight='balanced'))` aplicado sobre los embeddings. Multilabel binarizado con `MultiLabelBinarizer`.

**Razón**: combinación estándar de scikit-learn para multilabel. Logistic Regression es interpretable, rápida de entrenar (segundos sobre 5k embeddings), entrega probabilidades calibradas. `class_weight='balanced'` compensa parcialmente el desbalance de etiquetas.

**Alternativa descartada**: Random Forest multilabel (overfitting con muestra chica), SVM (más lento, menos interpretable), fine-tune de transformer (overkill, requiere GPU), redes neuronales (innecesario para 48 etiquetas L2).

**Implicación**: M2b entrega `data/models/classifier.joblib` con un dict `{'embedder_name': str, 'binarizer': MultiLabelBinarizer, 'clf': OneVsRestClassifier, 'trained_at': str, 'metrics': dict}`. Cargable con `joblib.load`.

---

## 11. Umbral de decisión por etiqueta y fallback

**Decisión**: umbral fijo de 0.5 sobre la probabilidad de cada etiqueta. Si ninguna etiqueta supera 0.5 en una verbalización, se aplica fallback:

- Si `len(verbatim.strip()) < 10` → L1=`15. Otros / No clasificable`.
- Else si `nps_group ∈ {Promotor, Pasivo}` → L1=`14. Elogio o queja genérica`, L2=`14.1 Elogio genérico`.
- Else (Detractor) → L1=`14`, L2=`14.2 Queja genérica`.

**Razón**: garantiza cobertura ≥ 95% (KPI duro del reto), evita que comentarios cortos o ambiguos queden sin etiqueta, mantiene la bolsa "Otros" controlada en lugar de inflarla.

**Alternativa descartada**: umbral por etiqueta calibrado (requiere validación, complejidad), top-1 forzado (rompe multiclase, asigna mal a comentarios genuinamente ambiguos).

**Implicación**: el código de fallback vive en `engine.pipeline.classify()` (M2b). Toda fila clasificada por fallback se persiste con `source='fallback'` y `confidence=0.0`.

---

## 12. Extractores rule-based de los 4 metadatos transversales

**Decisión**: los 4 metadatos transversales se extraen con reglas determinísticas (regex + diccionarios), no con LLM ni con ML.

- **`personnel_named`**: regex de patrones (`(la|el)\s+(srita|sr|señor|señora|gerente|ejecutivo|cajero|cajera)`, nombres propios con capitalización), validado contra diccionario `engine/data/spanish_names.txt` (~5k nombres). Lista negra: `{Banamex, Citi, México, Sucursal, Banco, ...}`. Si match, extraer nombre y polaridad por contexto (palabras cercanas: `amable, atento, grosero, mala actitud` → mapea a `pos/neg`).
- **`explicit_recommendation`**: regex sobre frases pivote: `lo recomiendo`, `se lo recomendaría`, `no lo recomiendo`, `no se lo recomendaría a nadie`, `lo recomendaría ampliamente`. Devuelve `'pos'`, `'neg'` o `None`.
- **`mentions_other_bank`**: diccionario explícito de bancos mexicanos: `{BBVA, Banorte, Santander, HSBC, Scotiabank, Banregio, Inbursa, Banco Azteca, Afirme, BanBajío, Compartamos}`. Match case-insensitive con word boundaries `\b`. Devuelve lista.
- **`channels_mentioned`**: diccionario de keywords por canal canónico: `{app: [app, aplicación, móvil, celular]}`, `{atm: [atm, cajero automático]}`, `{telefonica: [telefónica, call center, llamada, contact center]}`, `{web: [web, portal, internet, página]}`, `{chat: [whatsapp, chat, mensaje]}`, `{sucursal: [sucursal, oficina, ventanilla]}`. Match con normalización (lowercase, sin acentos para la búsqueda, ojo: solo para la búsqueda, no para el contenido).

**Razón**: para campos con espacio de salida acotado y patrones lingüísticos predecibles, las reglas superan al LLM en consistencia y costo. Además son auditables.

**Alternativa descartada**: NER con spaCy (peso del modelo, dependencia adicional, sin ganancia significativa para nombres comunes), LLM por verbalización (precio se dispara, latencia inaceptable para 474k filas en runtime).

**Implicación**: M2a entrega 4 funciones puras en `engine/extractors.py` con tests unitarios extensos. Los 3 archivos de datos (`spanish_names.txt`, `mexican_banks.txt`, `channel_keywords.txt`) son parte del paquete `engine`.

---

## 13. Mapeo taxonomía L1 → buckets UI

**Decisión**: las 15 categorías L1 se agrupan en 10 buckets visibles para el frontend. El mapeo exacto vive en `01_contratos_compartidos.md §6` y se implementa como lookup table en `engine/pipeline.py` (función `assign_ui_bucket(l1_code) -> str`).

**Razón**: la propuesta inicial (§14) pide "agrupaciones simplificadas y accionables", no la taxonomía completa en pantalla. 10 buckets es manejable para un gerente que escanea la vista en 5 segundos.

**Alternativa descartada**: mostrar las 15 L1 (cognitive overload), mostrar L2 (48 buckets, no se puede escanear), buckets dinámicos por sucursal (rompe consistencia entre vistas).

**Implicación**: cada fila de `classifications` tiene `ui_bucket` poblado por el pipeline. M3 agrupa por `ui_bucket` para "Principales causas" y "Principales fortalezas". M5 muestra `ui_bucket` como nombre del tema.

---

## 14. Criterio de sucursal crítica

**Decisión**: una sucursal es crítica si cumple **al menos una** de las siguientes condiciones:

1. `NPS_actual < (NPS_objetivo_sucursal − 5)`
2. La brecha vs objetivo está en el percentil 10 peor del nacional
3. `% detractores ≥ 30%`
4. Deterioro mes-a-mes ≥ 5 puntos de NPS (cuando aplica comparación)

Si la sucursal no tiene objetivo configurado, las condiciones (1) y (2) se omiten; (3) y (4) aplican.

**Razón**: combina absoluto (NPS bajo), relativo (peor que pares), composición (muchos detractores) y dinámica (empeoramiento). Cuatro condiciones distintas cubren patrones distintos de deterioro sin ser redundantes.

**Alternativa descartada**: solo NPS absoluto (no captura empeoramiento), solo brecha (penaliza sucursales con objetivo alto), solo composición de detractores (no captura sucursales con muchos pasivos no-promotores).

**Implicación**: M3 implementa `analytics.ranking.critical_branches(limit=10)` con una expresión SQL/Python explícita que evalúa las 4 condiciones y une con OR. La función expone qué condición(es) disparó cada sucursal para que la UI muestre el motivo.

---

## 15. Generación de objetivos NPS sintéticos

**Decisión**: para cada `Id_branch` detectado:

```python
import numpy as np
rng = np.random.default_rng(seed=int(branch_id.removeprefix('A-')))
nps_real = nps_historico_de_la_sucursal  # promedio histórico en la base
perturbacion = rng.normal(loc=3, scale=4)  # objetivos suelen ser optimistas
target = int(np.clip(nps_real + perturbacion, 50, 85))
```

Si la sucursal no tiene NPS histórico (caso teórico, no debería ocurrir con los 3 corpora cargados), se asigna `target = 65 + rng.normal(0, 5)` clipeado a [50, 85].

Los objetivos se generan **una sola vez** al cargar la primera vez la base, se persisten en `branch_targets`, y no se regeneran al cargar archivos adicionales.

**Razón**: los objetivos sintéticos no deben ser arbitrarios: deben tener cierta correlación con el desempeño histórico (no se le pone objetivo 80 a una sucursal con NPS histórico de 40). La perturbación con μ=3 simula que los objetivos son ligeramente optimistas pero alcanzables, igual que en operación real.

**Alternativa descartada**: target uniforme 70 para todas (no permite mostrar variedad de brechas), target = NPS_real (sin brecha, no hay narrativa), valores manualmente curados (no escala a 1,291 sucursales).

**Implicación**: M1 implementa `core.targets.generate_all(seed=42)` que llena `branch_targets`. La UI muestra etiqueta visible "Objetivos NPS sintéticos para demo" en la cabecera de cualquier vista con brecha.

---

## 16. Fórmula de impacto en NPS por categoría

**Decisión**: counterfactual simple. Para cada bucket UI:

```
impacto_bucket = NPS_actual − NPS_simulado_sin_bucket

donde NPS_simulado_sin_bucket = NPS calculado tras reclasificar como Pasivos
a los detractores que mencionaron ese bucket.
```

**Razón**: cuantifica cuánto subiría el NPS si esa fricción dejara de aplastar a los detractores que la mencionan. Es defendible: "si arregláramos esto, ganamos X puntos". No reasigna a Promotor (sería demasiado optimista); reasigna a Pasivo (cliente queda neutral, deja de penalizar).

**Alternativa descartada**: regresión NPS ~ buckets (requiere modelo, complejidad, datos sintéticos llevan a sobre-ajuste), peso lineal por frecuencia (no es impacto real, solo conteo), simulación más sofisticada (overkill para MVP).

**Implicación**: M3 implementa `analytics.impact.impact_by_category(scope='national' | branch_id)`. Returns lista ordenada por `impacto` descendente. La UI lo muestra como "Cada categoría representa X puntos perdidos de NPS".

---

## 17. Análisis específico de pasivos

**Decisión**: M3 incluye una función `analytics.topics.passive_analysis(scope)` que segmenta los pasivos por NPS:

- Pasivos con NPS=7 (cerca de detractor): reporta temas dominantes (presumiblemente con tono de queja sin gravedad).
- Pasivos con NPS=8 (cerca de promotor): reporta temas dominantes (presumiblemente con tono neutro o tibiamente positivo).

La UI puede mostrar esto como subsección "Voz de los pasivos" en vista nacional o como bloque secundario en sucursal.

**Razón**: en NPS, mover un Pasivo a Promotor sube el indicador 1 punto; mover un Detractor a Pasivo también sube 1 punto. Pero hay generalmente más Pasivos que Detractores y son más fáciles de convencer (no están enojados). Cuantificar qué temas los mueven es valioso para "acciones sugeridas".

**Alternativa descartada**: ignorar pasivos (omisión clásica del análisis NPS), tratar a todos como un grupo (pierde la asimetría entre 7 y 8).

**Implicación**: M5 puede o no exponer esto como pantalla dedicada; mínimo lo incluye como bloque en vista nacional YTD.

---

## 18. Autenticación

**Decisión**: endpoint `POST /auth/login` acepta JSON `{"username": str, "password": str}` y devuelve `{"token": str, "expires_at": str}`. El token es un JWT firmado con HS256 y secreto en `JWT_SECRET` (`.env`). Expiración 24 horas. Cualquier combinación usuario/contraseña es válida.

Middleware FastAPI valida el token en todos los endpoints excepto `/auth/login`, `/healthz`, `/docs`, `/openapi.json`.

**Razón**: el sistema necesita una pantalla de login para representar la "experiencia ejecutiva" del demo, pero no necesita gestión real de usuarios. El JWT lo hace defendible en demo sin construir un sistema de identidad.

**Alternativa descartada**: sin auth (rompe la propuesta §4), auth real con bcrypt + tabla de usuarios (overhead para un solo usuario demo), OAuth con un proveedor externo (dependencia de internet).

**Implicación**: M4 implementa el endpoint y el middleware. M5 guarda el token en `localStorage.banamex_token` y lo envía como `Authorization: Bearer <token>` en cada llamada. Si la API devuelve 401, M5 redirige a `/login`.

---

## 19. CORS

**Decisión**: el backend permite los orígenes `http://localhost:5173` (Vite dev server) y `http://localhost` (build servido por nginx). Métodos: GET, POST, PUT, DELETE, OPTIONS. Headers: todos.

**Razón**: dev local sin fricción. Sin permitir orígenes externos, sin wildcard `*`.

**Alternativa descartada**: wildcard `*` (mal hábito), proxy en Vite (overhead innecesario).

**Implicación**: M4 configura `CORSMiddleware` con esa lista al arrancar la app.

---

## 20. Empaquetado de demo

**Decisión**: `docker-compose.yml` en la raíz con dos servicios:

- `api`: build desde `./api/Dockerfile`, expone 8000, monta `./data` como volumen.
- `web`: build desde `./web/Dockerfile`, expone 80, depende de `api`.

Variables de entorno en `.env` (no commiteado, plantilla en `.env.example`).

**Razón**: un solo `docker compose up` arranca toda la demo. Volumen montado permite actualizar la DB pre-procesada sin reconstruir imágenes.

**Alternativa descartada**: ejecución local sin Docker (problemas de versión de Python/Node entre máquinas), Kubernetes/k3d (overkill), single-container con supervisord (peor separación de concerns).

**Implicación**: M6 escribe el `docker-compose.yml` y los dos `Dockerfile`. M4 y M5 entregan sus respectivos Dockerfile como parte de su DoD.

---

## 21. Pre-procesamiento de los corpora del reto

**Decisión**: script `scripts/preprocess_corpora.py` que ejecuta el pipeline completo offline:

1. Inicializa el schema SQLite si no existe.
2. Carga los 3 `.txt` de `data/raw/` con dedup por `record_id`.
3. Genera objetivos NPS sintéticos para todas las sucursales detectadas.
4. Corre M2a sobre la muestra de 5k → tabla `classifications` con `source='llm_annotation'`.
5. Corre M2b para entrenar el clasificador y persistirlo.
6. Corre el clasificador sobre las 469k filas restantes → `classifications` con `source='classifier'`.
7. Corre los 4 extractores de metadatos sobre las 474k filas → `metadata_extractions`.
8. Reporta totales.

El script es **idempotente**: si ya hay anotaciones, no las re-genera; si ya hay un clasificador, no re-entrena. Flags `--force-annotate`, `--force-train`, `--force-predict` para forzar re-ejecución de cada fase.

**Razón**: una sola ejecución antes de la demo deja todo listo. La demo entonces solo demuestra el flujo de upload sobre un archivo adicional o pequeño.

**Alternativa descartada**: procesar todo en vivo durante la demo (lento, riesgo de fallo en escenario en vivo), procesar al primer login (UX rota, primera carga tarda 4 horas).

**Implicación**: M6 escribe este script orquestador. Se ejecuta una vez antes de la demo. Tiempo estimado de ejecución completa: ~5-7 horas (3 horas inferencia del clasificador local + 2-4 horas anotación con LLM local sobre la muestra de 5,000). El paso 4 requiere que Ollama esté corriendo y el modelo descargado.

---

## 22. Upload en runtime

**Decisión**: el endpoint `POST /upload` recibe un `.txt`, repite el pipeline de M1 (parse → dedup) y M2b (clasificación inline con el modelo ya entrenado) + M2a extractores (rule-based, rápidos). **No ejecuta M2a anotador en runtime** (no llama al LLM). **No reentrena el clasificador**.

Procesamiento síncrono para archivos ≤ 30k filas (tiempo estimado: 1-2 minutos). Para archivos mayores, asincronía con `BackgroundTasks` de FastAPI y polling vía `GET /upload/{file_id}/status`.

**Razón**: la demo necesita demostrar carga de archivo nuevo (§5 de propuesta). El modelo entrenado offline es suficiente para clasificar uploads, no requiere LLM.

**Alternativa descartada**: re-anotar con LLM en runtime (cuelga la API, cuesta dinero), reentrenar clasificador con cada upload (no aporta, datos nuevos son marginales).

**Implicación**: M4 implementa el endpoint con el patrón síncrono primero; si el archivo cargado en la demo excede el timeout, se cambia a asíncrono. Documentado en M4.

---

## 23. Encoding de los TSV

**Decisión**: leer los `.txt` como `latin-1`. Normalizar a UTF-8 en memoria. Persistir en SQLite como UTF-8.

**Razón**: probado durante la exploración inicial — los archivos vienen en ISO-8859 (latin-1) y `latin-1` no falla ante ningún byte (cubre todos los 256 valores posibles). UTF-8 fallaría con caracteres no válidos.

**Alternativa descartada**: detección automática con `chardet` (overhead, ocasionalmente equivoca), abrir como `utf-8` con `errors='replace'` (corrupción silenciosa de acentos).

**Implicación**: M1 abre los archivos con `open(path, encoding='latin-1', newline='')`. Documenta esto en el código y en el README.

---

## 24. Tests E2E

**Decisión**: no se implementan tests E2E con browser (Playwright, Cypress, Selenium). Solo:

- Tests unitarios y de integración a nivel paquete (pytest, vitest).
- Un único smoke test end-to-end vía HTTP (curl/httpx): login → upload → consulta de vista nacional → consulta de sucursal → assertion sobre estructura JSON.

**Razón**: tests E2E con browser son frágiles, lentos y consumen tiempo de hackathon. El smoke test cubre el flujo de demo con mínimo costo.

**Alternativa descartada**: Playwright para flujos críticos (no se justifica el tiempo de configuración).

**Implicación**: M6 escribe `scripts/smoke_test.sh` con ~5 invocaciones de `curl` y validaciones con `jq`.

---

## 25. Logging

**Decisión**: backend usa `structlog` con renderer JSON. Frontend usa `console.log/warn/error` plano. Sin servicio de logs externo.

**Razón**: logs JSON en backend son fácilmente parseables si se necesitan, sin overhead. Frontend no es producción.

**Alternativa descartada**: librería de logging pesada (Loguru, etc., no aporta), enviar a Datadog/Sentry (no aplica a hackathon).

**Implicación**: M4 configura `structlog` al arrancar la app. Cada módulo Python obtiene su logger con `structlog.get_logger(__name__)`.

---

## 26. Versionado

**Decisión**: el proyecto no tiene git inicializado actualmente (el usuario lo desconectó en sesión previa). **No** se reinicia git como parte del plan. Si se requiere al final, M6 lo documenta como paso opcional manual.

**Razón**: el usuario manifestó preferencia por no tener repo conectado. Mantener consistente esa decisión hasta que él la cambie.

**Alternativa descartada**: `git init` automático (ignora la decisión explícita del usuario).

**Implicación**: cada sesión de implementación trabaja sin git (o en una worktree si el usuario inicializa después). Los entregables son archivos en disco, no commits.

---

## Anexo A — Variables de entorno

`.env.example` (commiteado) y `.env` (gitignored si hay git, sino solo `.env.example` en disco):

```env
# API
JWT_SECRET=cambia-esto-en-produccion-pero-en-mvp-da-igual
JWT_EXPIRATION_HOURS=24
API_PORT=8000
DATABASE_URL=sqlite:///./data/processed/banamex.db

# Motor LLM local (solo M2a, fase de anotación)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## Anexo B — Versiones exactas (lockfiles)

Cada paquete define versiones mínimas en su `pyproject.toml` con resolución por `pip install`. No se generan lockfiles para MVP (sin garantía de reproducibilidad estricta). Si surge un problema de versión durante el desarrollo, se documenta en `09_riesgos_y_demo_script.md` y se fija puntualmente.

Versiones objetivo:

- Python 3.12
- Node 20 LTS
- ollama (Python client) ≥ 0.4
- Ollama runtime ≥ 0.5.0 (requerido para `format=<json_schema>`)
- sentence-transformers ≥ 2.7
- scikit-learn ≥ 1.4
- FastAPI ≥ 0.110
- React 18.3
- Vite 5.x

---

## Anexo C — Glosario

- **Verbalización**: comentario abierto de un cliente en encuesta NPS. Equivale a `verbatim` en el código.
- **L1 / L2 / L3**: niveles 1, 2 y 3 de la taxonomía (`taxonomia_revisada.md`). L1 son las 15 raíz, L2 las 48 subcategorías, L3 las ~90 hojas.
- **Bucket UI**: agrupación de L1 que se muestra al usuario final (10 buckets, ver §6 de contratos).
- **Golden set**: las 5,000 verbalizaciones anotadas por LLM con etiquetas L1+L2+L3. Es el dataset de entrenamiento del clasificador.
- **Polaridad**: `pos | neu | neg`, derivada del grupo NPS del cliente.
- **NPS**: Net Promoter Score = %Promotores − %Detractores. Escala 0-10 por cliente, agregado por sucursal o nacional.
- **Brecha**: NPS actual − NPS objetivo.
- **Impacto**: cuánto subiría el NPS si se eliminara una categoría como fuente de detracción (counterfactual del §16).
