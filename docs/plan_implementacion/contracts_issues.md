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

## 2026-05-21 — M2a: anexo L1/L2/L3 a `docs/taxonomia_revisada.md`

**Decisión/contrato afectado:** `03_M2a_anotador.md` (Detalles de implementación → Parseo de taxonomía) y `00_decisiones_tecnicas.md` Anexo C (define L1/L2/L3 como vivientes en `taxonomia_revisada.md`).

**Lo que el contrato dice:** `engine.taxonomy.load_taxonomy()` parsea `docs/taxonomia_revisada.md` y debe encontrar 15 L1, 48 L2, ~90 L3 con regex específicas (`#### N. **Nombre**`, `- **N.M Nombre**`, `    - N.M.K Nombre`).

**Lo que la sesión propuso/hizo:** El archivo `docs/taxonomia_revisada.md` heredado en la rama contiene la propuesta inicial del MVP (texto narrativo) y sólo lista las 15 L1 a nivel conceptual en §14, sin L2/L3 ni formato parseable. M2a no puede arrancar sin esa jerarquía. Se **añadió un Anexo al final del archivo** con el árbol completo L1/L2/L3 en el formato exigido (15 L1, 48 L2, 90 L3) sin tocar el contenido existente. Los L2 críticos para reglas de desambiguación citadas en `03_M2a §Detalles → Reglas de desambiguación` (1.1, 1.2 con 1.2.2, 2.2 con 2.2.3, 6.5 con 6.5.1, 8.3, 9.1, 9.2, 10.3, 14.1, 14.2) están presentes y con esos códigos.

**Razón:** No inventar códigos fuera del Anexo (regla del propio plan), pero sin la jerarquía no hay anotador. El Anexo es una materialización de lo que el plan ya asume que existe, no una reinterpretación del contrato.

**Resolución del usuario:** _(pendiente — validar que la nomenclatura concreta de L2/L3 elegida sea aceptable; si el usuario quisiera reemplazarla por una autoritativa de Banamex, basta con sobreescribir el anexo y re-correr `annotate-sample`)._

---
