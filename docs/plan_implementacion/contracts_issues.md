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

## 2026-05-21 — M2a: discrepancia entre el summary del doc y el contenido real

**Decisión/contrato afectado:** `docs/taxonomia_revisada.md` (versión autoritativa del cliente, líneas 218-223 — sección "Resumen volumétrico estimado").

**Lo que el contrato dice (resumen del doc):**

> L1: 15 categorías raíz. L2: 48 subcategorías. L3: ~90 aspectos neutrales (dentro del rango 80-100).

**Lo que el contenido real enumera al parsear:** **15 L1, 45 L2, 82 L3**. El parser determinístico (`engine.taxonomy.load_taxonomy`) cuenta ese desfase; los tests reflejan los conteos reales (`test_l2_count_matches_taxonomy_content`, `test_l3_count_matches_taxonomy_content`).

**Razón del desfase:** el resumen del doc parece haberse escrito antes de cerrar la jerarquía, o algunas hojas se colapsaron sin actualizar el conteo. No afecta funcionalidad de M2a — la prompt de Ollama se construye a partir del contenido parseado, no del summary.

**Resolución del usuario:** _(pendiente — decidir si actualizar el summary del doc a 45/82, o si faltan L2/L3 por agregar para llegar a 48/~90)._ No bloquea M2a.

---

## 2026-05-21 — M2a: verificación L1 codes vs ui_buckets/schemas (sin discrepancia)

**Decisión/contrato afectado:** `engine/src/engine/ui_buckets.py` y `core/src/core/schemas.py` (stubs congelados).

**Verificación realizada:** Los 15 L1 de la taxonomía vigente (códigos `"1"` a `"15"`) coinciden uno-a-uno con las claves de `UI_BUCKETS_BY_L1`. Los nombres canónicos de L1 (`"Atención al cliente"`, `"Tiempos y operación"`, `"Cajeros automáticos (ATM)"`, etc.) son distintos a los display-names de bucket (`"Atención del personal"`, `"Tiempos y espera"`, `"Cajeros (ATM)"`) **por diseño de `01 §6`** — el bucket es una etiqueta de UI, no el nombre del L1. No requiere acción.

`core/src/core/schemas.py` no referencia códigos L1 directamente (sólo DTOs de NPSGroup, Polarity, ClassificationSource), por lo que no hay conflicto.

**Estado:** Sin discrepancia. Anotado para trazabilidad.

---
