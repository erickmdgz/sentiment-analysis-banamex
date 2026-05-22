---
tipo: dashboard
tags:
  - dashboard
  - obsidian
---

# Dashboard del proyecto

> Vista dinámica del estado del proyecto vía **Dataview**. Las tablas debajo se regeneran automáticamente leyendo el frontmatter YAML de cada archivo. Si actualizas `estado:` en un M-doc (ej. cuando se mergea un PR), esta vista refleja el cambio sin que tengas que tocar nada aquí.
>
> Si ves los bloques como código crudo en lugar de tablas, comprueba que Dataview está activo en **Settings → Community plugins**.
>
> Para el estado textual (decisiones, PRs históricos, convenciones aprendidas), sigue siendo [[ESTADO]] la fuente. Este dashboard es complementario y se enfoca en el **grafo módulos/dependencias/estados** del plan.

---

## Módulos del plan (todos)

```dataview
TABLE WITHOUT ID
  file.link AS "M-doc",
  modulo AS "Módulo",
  estado AS "Estado",
  paquete AS "Paquete",
  pr AS "PR",
  depende_de AS "Depende de"
FROM "docs/plan_implementacion"
WHERE tipo = "m-doc"
SORT modulo ASC
```

---

## En progreso

```dataview
LIST "paquete: " + paquete + " · depende de: " + depende_de
FROM "docs/plan_implementacion"
WHERE tipo = "m-doc" AND estado = "en-progreso"
SORT modulo ASC
```

## Pendientes

```dataview
LIST "depende de: " + depende_de
FROM "docs/plan_implementacion"
WHERE tipo = "m-doc" AND estado = "pendiente"
SORT modulo ASC
```

## Completados (con PR)

```dataview
TABLE WITHOUT ID
  file.link AS "M-doc",
  modulo AS "Módulo",
  "PR #" + pr AS "PR",
  paquete AS "Paquete"
FROM "docs/plan_implementacion"
WHERE tipo = "m-doc" AND estado = "completado"
SORT modulo ASC
```

---

## Contratos congelados

```dataview
TABLE WITHOUT ID
  file.link AS "Contrato",
  seccion AS "§"
FROM "docs/plan_implementacion"
WHERE tipo = "contrato-congelado"
SORT seccion ASC
```

## Otros documentos del plan

```dataview
TABLE WITHOUT ID
  file.link AS "Documento",
  tipo AS "Tipo"
FROM #plan-implementacion
WHERE tipo != "m-doc" AND tipo != "contrato-congelado"
SORT file.name ASC
```

---

## Recientemente modificados (todo el vault)

```dataview
TABLE WITHOUT ID
  file.link AS "Archivo",
  dateformat(file.mtime, "yyyy-MM-dd HH:mm") AS "Modificado"
FROM "docs"
WHERE file.name != "DASHBOARD"
SORT file.mtime DESC
LIMIT 10
```
