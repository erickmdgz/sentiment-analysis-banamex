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
