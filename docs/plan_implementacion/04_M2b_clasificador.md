---
tipo: m-doc
modulo: M2b
estado: completado
paquete: engine
pr: 7
depende_de:
  - M2a
  - M1
tags:
  - plan-implementacion
  - modulo-m2b
---

# M2b — Motor: clasificador supervisado y pipeline público

## Responsabilidad

M2b entrena un clasificador supervisado multilabel sobre el golden set producido por M2a y lo aplica en producción al resto de las verbalizaciones y a los uploads que entren en runtime. El stack es `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` para embeddings y `OneVsRestClassifier(LogisticRegression)` sobre esos embeddings (decisiones §9 y §10 de `00_decisiones_tecnicas.md`). El clasificador predice únicamente L1 + L2 multilabel; L3 queda fuera de predicción y solo persiste en el golden set (decisión §7). Las ~469k verbalizaciones que no fueron parte del golden se clasifican en bloque por M2b durante el preprocesamiento offline.

M2b también expone la **API pública del motor**: la función `engine.pipeline.classify(record_id, text, nps_group) -> ClassificationResult` que M3, M4 y los scripts consumen. Esa función combina cuatro piezas: el clasificador entrenado, los extractores rule-based de M2a (`engine.extractors.extract_all`), el mapeo de polaridad heredada del grupo NPS (decisión §8), el lookup `engine.ui_buckets.assign_ui_bucket(l1_code)` y la lógica de fallback cuando ninguna etiqueta supera el umbral de 0.5 (decisión §11). El TypedDict `ClassificationResult` ya está definido en `01_contratos_compartidos.md §4` y M2b no lo modifica, solo lo produce.

## Entregables

- [ ] `engine.embeddings.Embedder` — clase que carga el modelo una sola vez y expone `encode(texts: list[str]) -> np.ndarray`.
- [ ] `engine.embeddings.get_default_embedder()` — singleton lazy que devuelve la instancia compartida del Embedder.
- [ ] `engine.trainer.train(annotation_run_id: int, seed: int = 42) -> ClassifierRun` — entrena el clasificador sobre el golden set de la corrida indicada y persiste el modelo.
- [ ] `engine.classifier.Classifier` — clase que carga el `.joblib` y expone `predict(texts: list[str]) -> list[list[CategoryPrediction]]`.
- [ ] `engine.classifier.get_default_classifier()` — carga `data/models/classifier.joblib` y lo cachea entre llamadas.
- [ ] `engine.pipeline.classify(record_id: str, text: str, nps_group: str) -> ClassificationResult` — API pública del motor.
- [ ] `engine.pipeline.classify_batch(items: list[tuple[str, str, str]]) -> list[ClassificationResult]` — versión batch optimizada para predict-all y para uploads.
- [ ] `engine.pipeline.persist_classification(result: ClassificationResult)` — escribe en `classifications` (una fila por categoría) y en `metadata_extractions`.
- [ ] CLI `python -m engine.cli train --annotation-run-id N` — entrena con el golden set de esa corrida y registra un `classifier_runs`.
- [ ] CLI `python -m engine.cli predict-all` — corre el clasificador sobre toda verbalization sin clasificación previa.
- [ ] CLI `python -m engine.cli predict-one --text "..." --nps-group Detractor` — utilidad de debug.
- [ ] `engine.mocks.classify_mock` — mock determinístico para que M3 y M4 no esperen al entrenamiento real.
- [ ] README del paquete (en español, ver `01_contratos_compartidos.md §14`).

## Contratos consumidos

- Filas en `classifications` con `source = 'llm_annotation'` (producidas por M2a) → dataset de entrenamiento.
- Tabla `verbalizations` (producida por M1) → universo de inferencia masiva.
- `engine.extractors.extract_all(text) -> Metadata` (de M2a) → poblar el campo `metadata` del `ClassificationResult`.
- `engine.ui_buckets.assign_ui_bucket(l1_code) -> str` (compartido, definido en `01_contratos_compartidos.md §6`) → llenar la columna `ui_bucket` de cada fila de `classifications`.
- Tabla `annotation_runs` (de M2a) → referenciada por `classifier_runs.trained_on_run_id`.
- Schemas Pydantic / TypedDict de `01_contratos_compartidos.md §4`: `CategoryPrediction`, `Metadata`, `ClassificationResult`.

## Contratos producidos

- Modelo entrenado en `data/models/classifier.joblib`. Estructura dict:

  ```python
  {
      "embedder_name": "paraphrase-multilingual-MiniLM-L12-v2",
      "binarizer": MultiLabelBinarizer,        # ajustado al golden set
      "clf": OneVsRestClassifier,              # ya fitted
      "label_codes": list[str],                # ["1.1", "1.2", "2.1", ...]
      "trained_at": str,                       # ISO 8601
      "metrics": {
          "f1_micro": float,
          "f1_macro": float,
          "hamming_loss": float,
          "subset_accuracy": float,
          "n_samples_train": int,
          "n_samples_test": int,
      },
  }
  ```

- Filas nuevas en `classifications`:
  - `source = 'classifier'` cuando una o más etiquetas L2 superan el umbral.
  - `source = 'fallback'` cuando ninguna etiqueta supera el umbral y se aplica la lógica de §11.
- Fila nueva en `classifier_runs` por cada entrenamiento (`model_path`, `trained_on_run_id`, `trained_at`, `n_samples`, `n_labels`, `f1_micro`, `f1_macro`, `hamming_loss`).
- API pública `engine.pipeline.classify` / `classify_batch` / `persist_classification` — consumida por `analytics/`, `api/` (endpoint `POST /upload`) y `scripts/preprocess_corpora.py`.

## Estructura de archivos esperada

Árbol parcial del paquete `engine/` que toca M2b (ver `01_contratos_compartidos.md §1` para la estructura completa):

```
engine/
├── pyproject.toml
├── README.md
├── src/engine/
│   ├── __init__.py
│   ├── embeddings.py        # Embedder + get_default_embedder()  (M2b)
│   ├── trainer.py           # train(annotation_run_id, seed)     (M2b)
│   ├── classifier.py        # Classifier + get_default_classifier (M2b)
│   ├── pipeline.py          # classify / classify_batch / persist_classification (M2b)
│   ├── ui_buckets.py        # assign_ui_bucket (compartido)      (M2b)
│   ├── mocks.py             # classify_mock                       (M2b)
│   ├── cli.py               # subcomandos: train, predict-all, predict-one (M2b)
│   ├── extractors.py        # consumido (de M2a)
│   ├── taxonomy.py          # consumido (de M2a)
│   └── ...
└── tests/
    ├── test_embeddings.py
    ├── test_trainer.py
    ├── test_classifier.py
    ├── test_pipeline.py
    ├── test_ui_buckets.py
    └── test_mocks.py
```

## Detalles de implementación clave

### Carga del modelo de embeddings (`engine.embeddings`)

- Modelo: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (decisión §9). Dimensión 384, multilingüe, ~120 MB en disco.
- Carga con `from sentence_transformers import SentenceTransformer`. Cache local en `~/.cache/torch/sentence_transformers/` (default del paquete, no hace falta tocar).
- Inicialización **lazy y singleton**: la primera llamada a `get_default_embedder()` construye la instancia; las llamadas siguientes devuelven la misma referencia. Esto evita pagar la carga (~3-5 s en CPU) más de una vez en la API.
- Llamada estándar para encode:

  ```python
  model.encode(
      texts,
      batch_size=64,
      show_progress_bar=True,
      normalize_embeddings=True,
      convert_to_numpy=True,
  )
  ```

  `normalize_embeddings=True` produce vectores unitarios (norma ≈ 1.0), lo cual ayuda a la regresión logística downstream.

### Construcción del dataset de entrenamiento (`engine.trainer`)

- Query SQL contra el `core.db` activo:

  ```sql
  SELECT v.record_id, v.verbatim_clean, c.l1_code, c.l2_code
  FROM verbalizations v
  JOIN classifications c ON v.record_id = c.record_id
  WHERE c.source = 'llm_annotation';
  ```

- Agrupar resultados por `record_id`: cada record_id reúne una lista `[(l1_code, l2_code), ...]` (es multilabel).
- Convertir cada par a la etiqueta string concatenada `f"{l1_code}.{l2_code}"` (ej. `"1.1"`, `"2.3"`).
- Binarizar con `sklearn.preprocessing.MultiLabelBinarizer`. Resultado: matriz `Y` de forma `(n_samples, n_labels)`.
- Calcular embeddings de `verbatim_clean` con el `Embedder`. Resultado: matriz `X` de forma `(n_samples, 384)`.

### Split y entrenamiento

- Split 80 / 10 / 10 train / val / test con `sklearn.model_selection.train_test_split` (dos llamadas anidadas para llegar al 10/10).
- Stratify por **L1 dominante** (la primera etiqueta de la lista de cada fila); esto basta para mantener la distribución del eje grueso.
- Modelo:

  ```python
  from sklearn.linear_model import LogisticRegression
  from sklearn.multiclass import OneVsRestClassifier
  from sklearn.pipeline import Pipeline

  pipe = Pipeline([
      ("clf", OneVsRestClassifier(
          LogisticRegression(
              max_iter=1000,
              C=1.0,
              class_weight="balanced",
              random_state=seed,
          )
      )),
  ])
  ```

- Métricas sobre el test set: `f1_micro`, `f1_macro`, `hamming_loss`, `subset_accuracy`. Se persisten en `classifier_runs` y dentro del dict del `.joblib`.
- **No son KPIs del reto** (decisión §8 de `00_decisiones_tecnicas.md`): son informativas; los KPIs del reto se evalúan en M3 (cobertura, NPS, etc.).

### Persistencia del modelo

- `joblib.dump({"embedder_name": ..., "binarizer": mlb, "clf": clf, "label_codes": list(mlb.classes_), "trained_at": iso_now(), "metrics": metrics_dict}, "data/models/classifier.joblib")`.
- Lectura con `joblib.load(path)`.
- La ruta `data/models/` ya está reservada en la estructura del proyecto (`01_contratos_compartidos.md §1`).

### Inferencia (`engine.classifier.Classifier`)

`Classifier.predict(texts: list[str]) -> list[list[CategoryPrediction]]`:

1. Calcular embeddings de `texts` con el `Embedder` del paquete.
2. `proba = self.clf.predict_proba(embeddings)` → matriz `(n, n_labels)` con probabilidades por etiqueta.
3. Para cada fila, seleccionar las etiquetas con `proba > 0.5` (decisión §11). Si no hay ninguna, la fila devuelve `[]` y el pipeline aplica fallback.
4. Cada etiqueta seleccionada (string `"l1.l2"`) se convierte en un `CategoryPrediction`:
   - `l1_code` y `l2_code`: tomados del string.
   - `l1_name`, `l2_name`: lookup en `engine.taxonomy.load_taxonomy()`.
   - `l3_code` y `l3_name`: siempre `None` en inferencia (decisión §7).
   - `confidence`: `proba[label_idx]`, redondeado a 4 decimales.
5. Devolver `list[list[CategoryPrediction]]`, una lista por cada texto de entrada.

### Pipeline público (`engine.pipeline.classify`)

Firma exacta (ver `01_contratos_compartidos.md §7`):

```python
def classify(record_id: str, text: str, nps_group: str) -> ClassificationResult: ...
```

Lógica:

1. Normalizar `text` (`text.strip() if text else ""`).
2. Polaridad heredada del NPS (decisión §8):

   ```python
   polarity = {"Detractor": "neg", "Pasivo": "neu", "Promotor": "pos"}[nps_group]
   ```

3. Si `text` es `None` o `len(text) < 5`:
   - `is_classifiable = False`, `categories = []`, `metadata = extractors.extract_all("")`.
   - Aplicar fallback con `len(text) < 10` para decidir entre `L1=15` (Otros) y `L1=14` (Genérico).
4. Si `text` es procesable:
   - `categories = classifier.predict([text])[0]`.
   - Si `categories == []` (ninguna `proba > 0.5`), aplicar fallback (§11):
     - `len(text) < 10` → `L1=15. Otros / No clasificable`, `L2=15.1 No clasificable`.
     - `nps_group in {"Promotor", "Pasivo"}` → `L1=14`, `L2=14.1 Elogio genérico`.
     - `nps_group == "Detractor"` → `L1=14`, `L2=14.2 Queja genérica`.
     - En los tres casos: `confidence = 0.0`, fuente `'fallback'` cuando se persista.
5. `metadata = engine.extractors.extract_all(text)`.
6. Devolver el `ClassificationResult` (TypedDict de `01_contratos_compartidos.md §4`).

Notas importantes:

- `classify_batch` hace lo mismo en bloque: encode de todos los textos en una sola pasada, una llamada a `predict_proba`, luego itera para aplicar fallback / metadata por fila. Es la versión que usan `predict-all` y el endpoint `POST /upload`.
- `classify` y `classify_batch` **no escriben en la base**. La persistencia está en `persist_classification` para que el consumidor decida cuándo y en qué transacción.

### Persistencia de resultados (`persist_classification`)

- Itera sobre `result["categories"]`. Para cada categoría:
  - Inserta una fila en `classifications` con:
    - `record_id`, `l1_code`, `l1_name`, `l2_code`, `l2_name`, `l3_code=None`, `l3_name=None`.
    - `confidence` de la categoría.
    - `source = 'classifier'` si `confidence > 0`, `'fallback'` si vino de la rama de fallback.
    - `polarity = result["polarity"]`.
    - `ui_bucket = assign_ui_bucket(l1_code)`.
- Upsert sobre `metadata_extractions` con el contenido de `result["metadata"]` (clave única `record_id`).
- Si `result["categories"] == []` y no se llegó por fallback (caso teóricamente imposible), no inserta nada en `classifications` pero sí en `metadata_extractions`.

### Mock determinístico (`engine.mocks.classify_mock`)

- Firma idéntica a `classify` (`record_id`, `text`, `nps_group`) y mismo tipo de retorno.
- Hash MD5 de `text`, módulo 10 → índice de bucket UI mock; mapea a un L1 fijo plausible (ej. índice 0 → L1="1", índice 1 → L1="2", etc.).
- Polaridad: usa el mismo mapeo que la versión real (Detractor → neg, etc.).
- Metadata mock: detección sencilla con `in text.lower()` para keywords representativas (`"bbva"`, `"app"`, `"recomiendo"`, `"sr"`, `"srita"`). Sin depender de los archivos `spanish_names.txt`, `mexican_banks.txt`, `channel_keywords.txt`.
- Determinístico: misma entrada → misma salida exacta. Útil para que M3 y M4 escriban tests reproducibles sin haber entrenado el clasificador.

### Procesamiento masivo (`predict-all`)

- Query para descubrir pendientes:

  ```sql
  SELECT v.record_id, v.verbatim_clean, v.nps_group
  FROM verbalizations v
  LEFT JOIN classifications c ON v.record_id = c.record_id
  WHERE c.id IS NULL;
  ```

- Procesar en batches de 1000 verbalizations. Encode en una sola pasada por batch (en GPU es casi instantáneo; en CPU moderna ~10 s / 1000 textos).
- Persistir cada batch en una sola transacción SQLAlchemy.
- Reportar progreso cada 10,000 filas procesadas: timestamp, total procesado, ETA basada en throughput acumulado.
- Tiempo estimado total para 469k verbalizations en CPU moderna: **~3 horas** (consistente con decisión §21).

## Tests requeridos

Mínimo 15 tests, repartidos entre los archivos del árbol de arriba:

1. `test_embeddings.py`: `encode([])` no falla y devuelve shape `(0, 384)`.
2. `test_embeddings.py`: `encode(["hola", "hola"])` produce dos vectores **bit-idénticos**.
3. `test_embeddings.py`: con `normalize_embeddings=True`, cada vector devuelto tiene norma L2 ≈ 1.0 (tolerancia 1e-5).
4. `test_trainer.py`: con dataset sintético de 200 filas y 5 etiquetas plausibles, `f1_micro` reportado > 0.4.
5. `test_trainer.py`: tras `train(...)`, el archivo `data/models/classifier.joblib` existe y se carga con `joblib.load` sin error.
6. `test_trainer.py`: tras `train(...)`, hay exactamente una fila nueva en `classifier_runs` con `model_path`, `n_samples`, `n_labels`, `f1_micro` poblados.
7. `test_classifier.py`: misma entrada (lista de textos) llamada dos veces produce la **misma** salida (determinismo, incluido el orden de las categorías).
8. `test_classifier.py`: al menos una etiqueta con `confidence > 0.5` se devuelve para textos del dataset sintético; textos completamente fuera de distribución pueden devolver `[]` (válido).
9. `test_pipeline.py`: `classify(record_id, text="", nps_group="Detractor")` → `is_classifiable=False`, `categories=[]` y se dispara la rama de fallback al persistir.
10. `test_pipeline.py`: `classify(...)` con un verbatim normal devuelve `categories` no vacía **o** una sola categoría de fallback (nunca queda sin etiqueta).
11. `test_pipeline.py`: la polaridad de `ClassificationResult` siempre coincide con el mapeo `{Detractor: neg, Pasivo: neu, Promotor: pos}`.
12. `test_pipeline.py`: `result["metadata"]` siempre incluye las 4 claves del TypedDict `Metadata` (`personnel_named`, `explicit_recommendation`, `mentions_other_bank`, `channels_mentioned`).
13. `test_pipeline.py`: verbatim corto (`"x"`) + `nps_group="Detractor"` → categoría de fallback con `l1_code="15"`.
14. `test_pipeline.py`: verbatim normal sin match (forzar `classifier` a devolver `[]`) → fallback con `l1_code="14"`.
15. `test_mocks.py`: `classify_mock(...)` devuelve una estructura que valida contra `ClassificationResult` sin necesidad de modelo entrenado ni de embeddings cargados.

(Tests adicionales sugeridos: `test_ui_buckets.py` cubre que todos los L1 del 1 al 15 mapean a un bucket válido; ver `01_contratos_compartidos.md §6`.)

## Definition of Done

- `pytest engine/tests/test_trainer.py engine/tests/test_classifier.py engine/tests/test_pipeline.py engine/tests/test_embeddings.py engine/tests/test_mocks.py` pasa en verde.
- `python -m engine.cli train --annotation-run-id 1` produce `data/models/classifier.joblib`, registra una fila en `classifier_runs` y reporta métricas por stdout.
- `python -m engine.cli predict-all` procesa todas las verbalizations sin clasificación previa, en batches de 1000, con reporte de progreso cada 10k.
- Tras `predict-all`, el conteo de filas en `classifications` con `source IN ('classifier', 'fallback')` ≈ 469k (las verbalizations sin verbatim útil van por la rama de fallback; ninguna verbalization queda sin alguna fila en `classifications`).
- **Cobertura ≥ 95 %**: el porcentaje de verbalizations con al menos una fila en `classifications` ≥ 95 % del total de la tabla `verbalizations` (KPI duro del reto, consistente con `01_contratos_compartidos.md` y decisión §11).
- README del paquete escrito en español (instalación, comandos CLI, qué expone públicamente, ejemplo de uso de `classify`).
- `engine.mocks.classify_mock` funciona sin necesidad de tener `data/models/classifier.joblib` en disco (M3 y M4 lo verifican en sus propios tests).
- Sin secrets ni rutas absolutas hardcoded en el código.

## Riesgos específicos del módulo

- **Class imbalance en L2 raras**: hay etiquetas L2 con muy pocos ejemplos en el golden set. `class_weight="balanced"` compensa parcialmente; las etiquetas con menos de ~30 ejemplos probablemente no se aprendan bien y caerán por debajo del umbral 0.5. Documentar en README como **comportamiento aceptable** del MVP; el reentrenamiento con más golden data lo resuelve.
- **Memoria al hacer encode de 469k de golpe**: no cargar todos los textos en RAM. La implementación de `predict-all` debe iterar en batches de 1000 y liberar el batch anterior antes de pedir el siguiente.
- **Tiempo de inferencia (~3 h en CPU)**: incompatible con corridas durante la demo. Por eso se ejecuta offline desde `scripts/preprocess_corpora.py` (decisión §21). El endpoint `POST /upload` solo procesa archivos pequeños inline (decisión §22).
- **El `.joblib` no se carga por mismatch de versión de scikit-learn**: fijar versión mínima en `engine/pyproject.toml` (`scikit-learn>=1.4`, ver Anexo B de `00_decisiones_tecnicas.md`). Si el `.joblib` se generó con una versión y se intenta cargar con otra incompatible, fallar con mensaje claro y sugerir re-entrenar.
- **El fallback dispara demasiado seguido (cobertura real baja)**: si tras `predict-all` la cobertura de filas `source='classifier'` (no fallback) está muy por debajo del esperado, puede ser señal de que el umbral 0.5 es demasiado estricto o que el golden set no representa bien el corpus. Analizar después del primer entrenamiento; si es necesario, anotar la incidencia en `contracts_issues.md` y proponer ajuste de umbral al usuario en lugar de cambiar la decisión §11 unilateralmente.
