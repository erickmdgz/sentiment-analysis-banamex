# M2a — Motor: anotador LLM + extractores de metadatos

Este documento detalla la planeación del módulo **M2a**, que provee dos componentes del paquete `engine`: el **anotador LLM** (que produce el golden set sobre una muestra estratificada de 5,000 verbalizaciones) y los **extractores rule-based** de los 4 metadatos transversales (que se aplican sobre las 474k verbalizaciones).

Toda decisión técnica referenciada aquí proviene de `00_decisiones_tecnicas.md` y `01_contratos_compartidos.md`. Cualquier sección que parezca cuestionar un contrato vigente se anota en `contracts_issues.md` y se sigue la decisión vigente.

---

## Responsabilidad

M2a tiene dos sub-responsabilidades complementarias dentro del motor híbrido de tres fases descrito en `00_decisiones_tecnicas.md §4`. La primera es la **anotación con LLM local**: usando el modelo configurado en `OLLAMA_MODEL` (default `qwen2.5:7b-instruct`) vía API local de Ollama (`00 §5`), se clasifica una muestra estratificada de **5,000 verbalizaciones** (`00 §6`) contra la taxonomía completa L1+L2+L3 de `docs/taxonomia_revisada.md`. El resultado es el **golden set**: filas en la tabla `classifications` con `source='llm_annotation'` y `l3_code` poblado (`00 §7`), que M2b consume como dataset de entrenamiento. La polaridad **no** la decide el LLM: se hereda del `nps_group` de la verbalización al momento de persistir (`00 §8`).

La segunda sub-responsabilidad es la **extracción rule-based** de los 4 metadatos transversales descritos en `00 §12`: `personnel_named`, `explicit_recommendation`, `mentions_other_bank`, `channels_mentioned`. A diferencia del anotador LLM (que solo corre sobre 5k filas), los extractores se aplican sobre **las 474k verbalizaciones** y pueblan la tabla `metadata_extractions` (1:1 con `verbalizations`, ver `01 §2`). Ambas sub-responsabilidades se entregan como API Python (`engine.annotator`, `engine.extractors`) y como subcomandos de CLI (`python -m engine.cli`).

---

## Entregables

- [ ] `engine.taxonomy.load_taxonomy()` parsea `docs/taxonomia_revisada.md` y devuelve dict jerárquico.
- [ ] `engine.taxonomy.get_l2_name(l1_code, l2_code) -> str` (firma exigida por `01 §7`).
- [ ] `engine.prompts.SYSTEM_PROMPT` (string con la taxonomía serializada + instrucciones).
- [ ] `engine.prompts.OUTPUT_SCHEMA` (el JSON Schema literal del `01 §5`).
- [ ] `engine.prompts.build_user_message(record_id, verbatim, nps_group)` construye el mensaje por verbalización.
- [ ] `engine.annotator.run_annotation(sample_size=5000, model='qwen2.5:7b-instruct', seed=42, concurrency=4) -> AnnotationRun`.
- [ ] `engine.annotator.AnnotationCache` persiste resultados en `data/cache/annotations/{record_id}.json`.
- [ ] `engine.annotator.sample_records(target_size=5000, seed=42) -> list[record_id]` (muestreo estratificado).
- [ ] `engine.extractors.extract_personnel(text: str) -> dict`.
- [ ] `engine.extractors.extract_explicit_recommendation(text: str) -> str | None`.
- [ ] `engine.extractors.extract_other_bank(text: str) -> list[str]`.
- [ ] `engine.extractors.extract_channels(text: str) -> list[str]`.
- [ ] `engine.extractors.extract_all(text: str) -> Metadata` (compose; firma exigida por `01 §7`).
- [ ] Archivos de datos: `engine/data/spanish_names.txt` (~5k nombres), `engine/data/mexican_banks.txt`, `engine/data/channel_keywords.txt`.
- [ ] CLI: `python -m engine.cli annotate-sample --size 5000 --seed 42`.
- [ ] CLI: `python -m engine.cli annotate-sample --size N --seed S --dry-run` (muestra el sample sin llamar al LLM).
- [ ] CLI: `python -m engine.cli extract-metadata --all` (corre los 4 extractores sobre todas las verbalizations sin metadata).
- [ ] README del paquete (`engine/README.md`) en español, con instalación, comandos, qué expone.

---

## Contratos consumidos

- **Tabla `verbalizations`** (`01 §2`): se leen `record_id`, `verbatim_clean`, `nps_group`, `nps_rate`, `response_year`, `response_month`, `has_verbatim`, `branch_id`. M2a **no escribe** en esta tabla.
- **Tabla `branches`** (`01 §2`): se lee `branch_id` (solo para verificación de integridad referencial en tests). M2a no escribe en esta tabla.
- **`docs/taxonomia_revisada.md`**: fuente del árbol jerárquico L1/L2/L3 que parsea `engine.taxonomy.load_taxonomy()`.
- **Variables de entorno `OLLAMA_HOST` y `OLLAMA_MODEL`** (`00 §5`, Anexo A): leídas por el cliente Ollama en `engine.annotator`. Ollama debe estar corriendo (`ollama serve`) y el modelo descargado (`ollama pull <model>`) antes de invocar el anotador.

Si M1 no está listo cuando arranca M2a, los tests usan **fixtures sintéticas** en `engine/tests/fixtures/verbalizations.csv` con ~200 filas (mix de detractores/pasivos/promotores y meses). El CLI también acepta `--db-url sqlite:///<path>` para apuntar a una DB alternativa, lo que permite trabajar contra una DB sembrada con fixtures.

---

## Contratos producidos

M2a, al ejecutarse, persiste tres tipos de filas (estructura exacta en `01 §2`):

- **Filas en `classifications`** con `source='llm_annotation'`. Una verbalización con N categorías produce N filas (multilabel desnormalizado). Cada fila incluye `l3_code` y `l3_name` cuando el LLM los devuelve no-nulos (`00 §7`). `ui_bucket` se asigna al persistir usando `engine.ui_buckets.assign_ui_bucket(l1_code)` (`01 §6`). `polarity` se asigna al persistir desde `nps_group` (`00 §8`).
- **Filas en `metadata_extractions`** (1:1 con verbalizations procesadas). `other_bank_names` y `channels_mentioned` se serializan como JSON string (lista de strings).
- **Una fila en `annotation_runs`** por corrida del anotador. Incluye `sample_size`, `model`, `started_at`, `finished_at`, `runtime_seconds`, `status`.

Lo que **no** produce M2a:
- No produce filas con `source='classifier'` ni `source='fallback'` (eso es M2b).
- No produce embeddings ni modelos `.joblib` (eso es M2b).
- No predice L3 fuera del golden set (las 469k restantes tienen `l3_code = NULL`, ver `00 §7`).

---

## Estructura de archivos esperada

Árbol parcial del paquete `engine` relevante para M2a (extracto de `01 §1`):

```
engine/
├── pyproject.toml
├── README.md
├── src/engine/
│   ├── __init__.py
│   ├── taxonomy.py               # load_taxonomy(), get_l2_name() — M2a
│   ├── prompts.py                # SYSTEM_PROMPT, OUTPUT_SCHEMA, build_user_message() — M2a
│   ├── annotator.py              # run_annotation(), AnnotationCache, sample_records() — M2a
│   ├── extractors.py             # 4 extractores rule-based + extract_all() — M2a
│   ├── ui_buckets.py             # assign_ui_bucket() — definido en 01 §6 (compartido M2a/M2b)
│   ├── cli.py                    # subcomandos annotate-sample, extract-metadata
│   └── data/
│       ├── spanish_names.txt
│       ├── mexican_banks.txt
│       └── channel_keywords.txt
└── tests/
    ├── fixtures/
    │   ├── verbalizations.csv
    │   └── llm_responses/        # JSONs de ejemplo para mockear el SDK
    ├── test_taxonomy.py
    ├── test_prompts.py
    ├── test_annotator.py
    ├── test_extractors.py
    └── test_cli.py
```

`data/cache/annotations/` es un directorio en disco creado en runtime por `AnnotationCache`, no se commitea (ya cubierto por la política universal de `.gitignore`).

---

## Detalles de implementación clave

### Parseo de la taxonomía (`engine/taxonomy.py`)

- Leer `docs/taxonomia_revisada.md` como texto, encoding `utf-8`.
- Regex para extraer headings:
  - L1: `^#### \d+\.\s+\*\*(.+?)\*\*$` (captura nombre L1, el número se extrae del literal antes).
  - L2: `^- \*\*(\d+\.\d+)\s+(.+?)\*\*$` (captura código y nombre L2).
  - L3: `^\s+- (\d+\.\d+\.\d+)\s+(.+)$` (captura código y nombre L3).
- Estructura resultante:

```python
TaxonomyDict = dict[
    str,  # l1_code, e.g. "1"
    {
        "name": str,
        "l2": dict[
            str,  # l2_code, e.g. "1.1"
            {
                "name": str,
                "l3": dict[str, str],  # {l3_code: l3_name}
            },
        ],
    },
]
```

- Hacer test que cuente: **15 L1, 48 L2, ~90 L3** (ver `00 §7`). Si el parseo cuenta valores distintos, fallar el test con mensaje explícito.

### Construcción del `SYSTEM_PROMPT` (`engine/prompts.py`)

- Empezar con: *"Eres un clasificador de comentarios de clientes de un banco mexicano. Asignas etiquetas de una taxonomía jerárquica a cada verbalización."*
- Incluir la taxonomía completa formateada (puede ocupar ~1500 tokens), generada a partir de `load_taxonomy()` para mantener una sola fuente de verdad.
- Explicar reglas:
  - Multiclase permitido (hasta **5 etiquetas** por verbalización; ver `OUTPUT_SCHEMA.categories.maxItems = 5` en `01 §5`).
  - `is_classifiable = false` para texto vacío, ininteligible, o sin contenido temático.
  - L3 solo si la hoja es clara; en caso de duda devolver `l3_code = null`.
  - `confidence` honesta en [0.0, 1.0], no sesgada a 1.0.
- **Reglas de desambiguación clave** (provenientes de `docs/taxonomia_revisada.md`; se citan las pertinentes según el contenido vigente del archivo de taxonomía):
  - **1.2.2 vs 6.5.1**: distinguir trato del personal sobre producto/promoción de fricción con el producto mismo. Si el cliente se queja del personal **al ofrecer/vender** un producto, va a 1.2.2; si la queja es del producto/promoción independientemente del personal, va a 6.5.1.
  - **2.2.3 vs 10.3**: distinguir tiempo/operación de procesos/requisitos. Si la espera viene del proceso interno y los pasos exigidos, va a 10.3; si la espera es operativa (turnos, ventanilla, sistema), va a 2.2.3.
  - **8.3 vs 9.1 vs 9.2**: costos vs aclaraciones/quejas vs fraude. Si el cliente cuestiona un cobro pero no afirma error, va a 8.3; si solicita aclaración por cargo no reconocido, va a 9.1; si denuncia fraude o uso indebido, va a 9.2.

  Si al implementar resulta que estas reglas no aparecen literalmente con esos códigos en la taxonomía vigente, se anota en `contracts_issues.md` y se usa la regla más cercana en el árbol parseado.

### Cliente Ollama (`engine/annotator.py`)

- `from ollama import AsyncClient` (o `Client` sincrónico para baja concurrencia).
- Constructor: `client = AsyncClient(host=os.getenv('OLLAMA_HOST', 'http://localhost:11434'))`.
- Pre-flight: al inicio de `run_annotation`, validar con `client.list()` que el modelo esté presente. Si no, abortar con mensaje claro: `"Modelo {model} no encontrado en Ollama. Ejecuta 'ollama pull {model}' primero."`.
- Validar también versión de Ollama ≥ 0.5.0 (requerida para `format=<json_schema>`); si la versión es menor, abortar con `"Ollama >= 0.5.0 requerido para constrained decoding. Actualiza con 'brew upgrade ollama'."`.
- Llamada por verbalización:

```python
response = await client.chat(
    model=os.getenv('OLLAMA_MODEL', 'qwen2.5:7b-instruct'),
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(record_id, verbatim, nps_group)},
    ],
    format=OUTPUT_SCHEMA,                  # JSON schema constrained decoding
    options={"temperature": 0.0, "seed": 42},
)
parsed = json.loads(response["message"]["content"])
```

- **Determinismo**: `temperature=0` + `seed=42` produce salidas reproducibles (aproximadamente; cambios de versión del modelo pueden romper bit-exactness).
- **No hay caché de prompt cross-request** comparable al de Anthropic. La taxonomía se manda en `system` en cada llamada; eso es ~1500 tokens de input que el modelo procesa cada vez. Aceptable porque el costo es solo tiempo de CPU/GPU.

### Procesamiento concurrente

- En vez de Batch API (no aplica con LLM local), se procesan las 5,000 verbalizaciones con `asyncio.gather` controlado por un semáforo de concurrencia configurable (default 4). El operador puede subir/bajar la concurrencia según los recursos de su máquina.
- Cada request individual a Ollama es síncrona desde el lado del modelo (Ollama serializa las inferencias por modelo cargado), por lo que valores altos de concurrencia no aceleran significativamente más allá del paralelismo interno de Ollama. Concurrency=4 sirve principalmente para solapar I/O y deserialización.
- **Progreso**: cada N=50 verbalizaciones, imprimir línea de progreso con `structlog` (ver `00 §25`): `processed=N total=5000 elapsed=Xs ETA=Ys`.
- **Manejo de errores**: si una request falla (timeout, conexión perdida, JSON inválido), reintentar individualmente con backoff exponencial (1s, 2s, 4s). Tras 3 fallas consecutivas para el mismo `record_id`, marcarlo como no anotado, log estructurado y continuar.
- **Timeout por request**: 60 segundos (configurable). Es generoso para verbalizaciones largas en CPU.

### Muestreo estratificado (`engine.annotator.sample_records`)

- Firma: `sample_records(target_size: int = 5000, seed: int = 42) -> list[str]` (devuelve lista de `record_id`).
- Cuotas según `00 §6`: **35% Detractor (1,750), 25% Pasivo (1,250), 40% Promotor (2,000)**.
- Distribuir cada cuota uniformemente entre los **16 meses** (enero 2025 a abril 2026, según `00 §6`). Aproximadamente: 1750/16 ≈ 110 detractores por mes; 1250/16 ≈ 78 pasivos por mes; 2000/16 = 125 promotores por mes.
- Implementación con `pandas.groupby(['nps_group', 'response_year', 'response_month']).sample(n=cuota, random_state=42)`.
- **Filtro previo**: `has_verbatim == 1` y `len(verbatim_clean.strip()) >= 5` (longitud mínima del `00 §6`).
- Si una celda (grupo × mes) tiene **menos filas que la cuota**: tomar todas las disponibles y compensar el déficit con **detractores aleatorios** (decisión explícita `00 §6` "Implicación").
- Misma `seed` produce el mismo conjunto de `record_id` (determinismo verificado en tests).

### Persistencia tras anotación

Tras recibir cada respuesta del batch:

1. Validar contra `OUTPUT_SCHEMA` (defensa en profundidad además del tool use).
2. Si `is_classifiable == false`: **no insertar** en `classifications` (la verbalización queda sin clasificación; M2b la procesará con fallback vía `00 §11`).
3. Si `is_classifiable == true` y `categories` no vacío:
   - Por cada `category`, insertar una fila en `classifications` con:
     - `record_id` = el de la verbalización.
     - `l1_code`, `l1_name`, `l2_code`, `l2_name` del LLM.
     - `l3_code`, `l3_name` del LLM si no son `null`, sino `NULL`.
     - `confidence` del LLM (literal).
     - `source = 'llm_annotation'`.
     - `polarity` = mapeo desde `nps_group` (`Detractor→neg, Pasivo→neu, Promotor→pos`; `00 §8`).
     - `ui_bucket` = `assign_ui_bucket(l1_code)` (`01 §6`).
4. Idempotencia: antes de insertar, verificar si ya existen filas con `(record_id, source='llm_annotation')`. Si existen, omitir (la corrida es resumible).

### Caché en disco (`AnnotationCache`)

- Directorio: `data/cache/annotations/{record_id}.json`. Un JSON por record.
- Antes de mandar al LLM: si el archivo existe, **saltar**, leer su contenido y persistir directo a DB.
- Tras recibir respuesta válida del LLM, escribir el JSON al cache.
- Permite reanudar tras `Ctrl+C` o fallo intermedio sin re-procesar.
- Comando CLI `annotate-sample --clear-cache` borra el directorio antes de empezar (opcional).

### Tiempo y monitoreo

- Reportar `elapsed_seconds`, `verbalizations_processed`, `verbalizations_failed`, `verbalizations_cached` por corrida.
- Estimar tiempo total durante la corrida con throughput promedio acumulado.
- **Cap defensivo de tiempo**: si una corrida excede **12 horas wall-clock**, abortar con error explícito. (Es un cap defensivo contra modelos colgados o configuración degradada; en hardware razonable, 5k verbalizaciones deben procesarse en 2-4 horas).
- Persistir `runtime_seconds` final en `annotation_runs.runtime_seconds` al cerrar la corrida.

### Extractores rule-based (`engine/extractors.py`)

#### `extract_personnel(text: str) -> dict`

- Patrones regex (case-insensitive con `(?i)`):

```python
PERSONNEL_TITLES = r"(?i)\b(la\s+srita|el\s+señor|la\s+señora|la\s+srta|el\s+lic|la\s+lic|el\s+gerente|la\s+gerenta|el\s+cajero|la\s+cajera|el\s+ejecutivo|la\s+ejecutiva)\b"
```

- Nombres propios: tokens con capitalización inicial + lookup en `engine/data/spanish_names.txt`. Lista negra explícita:

```python
PERSONNEL_BLACKLIST = {
    "Banamex", "Citi", "México", "Mexico", "Banco", "Sucursal",
    "NPS", "ATM", "BBVA", "Banorte", "Santander", "HSBC",
}
```

- **Polaridad por contexto**: ventana de ±10 palabras alrededor de la mención. Contar tokens en sets:

```python
PERSONNEL_POS = {"amable", "atento", "profesional", "eficiente", "rapido", "rápido",
                 "ayuda", "resolvio", "resolvió", "excelente", "amabilidad"}
PERSONNEL_NEG = {"grosero", "malo", "lento", "descortés", "descortes",
                 "mala", "pesimo", "pésimo", "no me ayudó", "mala actitud"}
```

  Asignar polaridad por mayoría. Si hay empate o ninguna palabra-clave, `personnel_polarity = None`.

- Devuelve:

```python
{
    "personnel_named": bool,
    "personnel_name": str | None,
    "personnel_polarity": "pos" | "neg" | None,
}
```

#### `extract_explicit_recommendation(text: str) -> str | None`

- **Regex prioritario para negaciones** (debe evaluarse antes del positivo):

```python
RE_REC_NEG = r"(?i)no\s+(lo|la|se\s+lo)\s+recomend"
```

  Si matchea → devolver `'neg'`.

- Si no, regex positivo:

```python
RE_REC_POS = r"(?i)(lo\s+recomiendo|se\s+lo\s+recomendar[ií]a|recomiendo\s+ampliamente|lo\s+recomendar[ií]a)"
```

  Si matchea → devolver `'pos'`.

- Si ninguno, devolver `None`.

#### `extract_other_bank(text: str) -> list[str]`

- Diccionario explícito en `engine/data/mexican_banks.txt`:

```
BBVA
Banorte
Santander
HSBC
Scotiabank
Banregio
Inbursa
Banco Azteca
Afirme
BanBajío
Compartamos
```

- Match con `\b{nombre}\b` case-insensitive. `Banco Azteca` se trata como secuencia literal con boundaries en los extremos.
- **Excluir** si el match es parte de un nombre compuesto que identifica a Banamex (ej. `"Banamex Citi"` adyacente: si `"Banamex"` aparece ±2 tokens antes/después del match, no contar `"Citi"`).
- Devolver lista deduplicada en orden de aparición.

#### `extract_channels(text: str) -> list[str]`

- Diccionario en `engine/data/channel_keywords.txt` (canónico → keywords):

```
app: app, aplicación, aplicacion, móvil, movil, celular, banamex móvil, banamex movil
atm: atm, cajero automático, cajero automatico, cajero
telefonica: telefónica, telefonica, call center, llamada, centro de atención, centro de atencion
web: web, portal, internet, página, pagina
chat: whatsapp, chat, mensaje
sucursal: sucursal, oficina, ventanilla
```

- **Normalización**: lowercase del texto y `unicodedata.normalize('NFD', ...).encode('ascii', 'ignore').decode()` para quitar acentos **solo para la búsqueda** (no se modifica el `verbatim` persistido).
- Devolver lista deduplicada de canales canónicos en orden de aparición.
- Nota: `cajero` por sí solo cae en `atm`. Si en el futuro se necesita distinguir `cajero` (persona) de `cajero automático`, ajustar con contexto; por ahora se acepta el conflicto (lo cubrirá la lectura del verbatim por humanos).

#### `extract_all(text: str) -> Metadata`

Composición que invoca los 4 anteriores y devuelve un `TypedDict` con la forma exacta de `Metadata` definida en `01 §4`:

```python
{
    "personnel_named": bool,
    "personnel_name": str | None,
    "personnel_polarity": Literal["pos", "neg"] | None,
    "explicit_recommendation": Literal["pos", "neg"] | None,
    "mentions_other_bank": bool,
    "other_bank_names": list[str],
    "channels_mentioned": list[str],
}
```

---

## Tests requeridos

Mínimo **20 casos**. Se ejecutan con `pytest engine/tests/`.

**Taxonomía**:
1. `load_taxonomy()` cuenta exactamente **15 L1**.
2. `load_taxonomy()` cuenta exactamente **48 L2**.
3. `load_taxonomy()` cuenta ~**90 L3** (umbral entre 85 y 95).
4. `get_l2_name('1', '1.1')` devuelve `'Trato del personal'`.

**Anotador**:
5. Mock del cliente Ollama: respuesta válida con 2 categorías produce 2 filas correctas en `classifications` (con `source='llm_annotation'`, `polarity` heredada del `nps_group`, `ui_bucket` asignado).
6. Respuesta con `is_classifiable=false` **NO** produce filas en `classifications`.
7. Respuesta con JSON malformado dispara reintento individual con feedback `"tu última respuesta no fue JSON válido, reintenta"`.
8. **Caché en disco se respeta**: segunda corrida sobre los mismos `record_id` no llama al LLM (assertion: el mock del SDK se invocó 0 veces).

**Muestreo**:
9. Cuotas se respetan ±5%: en muestra de 5,000, detractores entre 1,663 y 1,838; pasivos entre 1,188 y 1,313; promotores entre 1,900 y 2,100.
10. Misma `seed=42` produce el mismo conjunto de `record_id` (lista ordenada igual entre dos invocaciones).
11. Filtra correctamente verbatim vacíos (assertion: ningún `record_id` muestreado tiene `verbatim_clean == ''` o `len(verbatim_clean.strip()) < 5`).

**Extractor `personnel`**:
12. `"la srita Diana fue muy amable"` → `{personnel_named: True, personnel_name: 'Diana', personnel_polarity: 'pos'}`.
13. `"el gerente fue grosero"` → `{personnel_named: True, personnel_name: None, personnel_polarity: 'neg'}`.
14. `"Banamex no me ayudó"` → `personnel_name != 'Banamex'` (lista negra).
15. `"En México todo es lento"` → `personnel_name != 'México'`.

**Extractor `explicit_recommendation`**:
16. `"lo recomiendo a todos"` → `'pos'`.
17. `"no lo recomiendo a nadie"` → `'neg'` (prioridad de negación verificada).
18. `"deberían recomendar la sucursal"` → `None` (sin pivote claro de primera persona).

**Extractor `other_bank`**:
19. `"tengo cuenta en BBVA también"` → `['BBVA']`.
20. `"el cajero falló"` → `[]` (no detecta nada, Banamex implícito).

**Extractor `channels`**:
21. `"la app no funciona y el cajero tampoco"` → `['app', 'atm']`.
22. `"fui a la sucursal"` → `['sucursal']`.

---

## Definition of Done

- [ ] `pytest engine/tests/test_taxonomy.py engine/tests/test_annotator.py engine/tests/test_extractors.py engine/tests/test_cli.py` pasa en verde.
- [ ] `python -m engine.cli annotate-sample --size 100 --seed 42 --dry-run` muestra el sample sin llamar al LLM (imprime los 100 `record_id` y sus `nps_group`).
- [ ] `python -m engine.cli annotate-sample --size 5000` ejecuta, persiste 5,000 anotaciones (en realidad ≥5,000 filas en `classifications` por multilabel) y **1 fila en `annotation_runs`** con `status='done'`.
- [ ] `python -m engine.cli extract-metadata --all` puebla `metadata_extractions` para todas las verbalizations existentes (1 fila por `record_id`).
- [ ] **Tiempo de la corrida reportado en stdout y persistido** en `annotation_runs.runtime_seconds`.
- [ ] Los 3 archivos `engine/data/spanish_names.txt`, `engine/data/mexican_banks.txt`, `engine/data/channel_keywords.txt` existen y tienen contenido razonable (spanish_names: ~5k líneas; mexican_banks: 11 líneas; channel_keywords: 6 grupos).
- [ ] **README del paquete (`engine/README.md`) escrito en español** con: instalación (`pip install -e ./engine`), comandos CLI, qué expone (`load_taxonomy`, `run_annotation`, `extract_all`, `classify` cuando M2b lo provea), variables de entorno requeridas.
- [ ] `pyproject.toml` del paquete `engine` con dependencias: `ollama>=0.4`, `pydantic>=2.6`, `sqlalchemy>=2.0`, `pandas`, `structlog`, `jsonschema>=4`.
- [ ] Sin secretos en archivos commiteables. (Nota: con Ollama local no hay claves API que filtrar; la validación queda como hábito para `JWT_SECRET` y similares).

---

## Riesgos específicos del módulo

- **Tiempo de procesamiento excede lo razonable** si la muestra crece, si la concurrencia está mal calibrada o si hay un bucle de reintentos defectuoso → mitigación: **cap defensivo a 12 horas wall-clock por corrida**; abortar con mensaje claro. Tiempo nominal: 2-4 horas en Apple Silicon M-series para 5,000 verbalizaciones.
- **JSON malformado del LLM** pese al tool use forzado → validar respuesta contra `OUTPUT_SCHEMA` con `jsonschema`; si falla, reintentar pidiendo `"tu última respuesta no fue JSON válido, reintenta"`. Tras 3 fallas, marcar `record_id` como no anotado y log estructurado.
- **Ollama no responde o el modelo no está descargado** → el pre-flight de `run_annotation` valida con `client.list()` antes de empezar; si falla, abortar con mensaje accionable (`'ollama pull <model>'`). Si Ollama crashea a mitad de la corrida, el caché en disco permite reanudar sin pérdida.
- **Falsos positivos en `personnel`** con nombres ambiguos (`"Carmen"` puede ser persona o ciudad, `"Mateo"` puede ser parte de un nombre de calle) → lista negra explícita + validación contra `spanish_names.txt`. Aceptar residual de FP como error tolerable para MVP.
- **Falsos negativos en `explicit_recommendation`** por frases idiomáticas no cubiertas (`"se las paso al cliente"`, `"sí vale la pena"`) → aceptar; el extractor **no es exhaustivo**, devuelve `None` y la categoría 14 de la taxonomía cubre el caso.
- **`mentions_other_bank` con typos** (`"santader"` sin 'n', `"BBVA Bancomer"` legado) → aceptar variantes comunes en `mexican_banks.txt`; typos raros no se cubren para MVP.
- **Disonancia entre L3 anotado y L2 padre**: el LLM puede devolver un `l3_code` que no pertenece al `l2_code` del mismo objeto. Validar coherencia al persistir: si `l3_code` no es hijo de `l2_code` en la taxonomía cargada, descartar `l3_code` (poner `NULL`) y registrar warning.
- **Polaridad heredada del NPS pierde matices** (un promotor puede tener queja específica) → es decisión consciente `00 §8`; M2a no la mitiga, el frontend lo señala con tooltip "Polaridad inferida del NPS del cliente".
- **`docs/taxonomia_revisada.md` puede no contener literalmente las reglas de desambiguación citadas** (1.2.2 vs 6.5.1, etc.) → si al parsear no se encuentran esos códigos, anotar en `contracts_issues.md` y usar la regla más cercana del árbol vigente; **no inventar códigos**.
- **JSON Schema constrained decoding no soportado** si Ollama < 0.5.0 → validar versión al arrancar con `client.show(model)` o llamar `/api/version`; si versión < 0.5.0, abortar con mensaje `"Ollama >= 0.5.0 requerido para constrained decoding. Actualiza con 'brew upgrade ollama'."`.
- **Calidad del modelo local inferior a Haiku 4.5** en clasificación contra taxonomía profunda → es un trade-off aceptado a cambio de aislamiento de datos. Si la calidad observada en el golden set es muy baja, anotar en `contracts_issues.md`; posibles mitigaciones (no se aplican unilateralmente): subir a `qwen2.5:14b-instruct`, o aumentar la muestra y dejar que el clasificador supervisado promedie ruido.
