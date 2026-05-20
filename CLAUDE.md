# sentiment-analysis-banamex

## Descripción

Reto de hackathon del Tec de Monterrey con caso real de **Banamex**: análisis de sentimientos sobre experiencia de cliente (CX) en sucursales, basado en corpora de texto entregados por el cliente del caso.

No es un contrato facturable directo con Banamex — es un reto académico/competitivo con datos reales. Si llegara a derivar en un contrato, migrar a `clients/banamex/sentiment-analysis/`.

## Stack y versiones

- Lenguaje: <por definir — probable Python 3.12>
- Framework principal: <por definir>
- Base de datos: <no aplica por ahora>
- Dependencias clave: <por definir — probable pandas, scikit-learn / transformers, etc.>

## Comandos

```bash
# Instalar dependencias
<por definir>

# Correr en desarrollo
<por definir>

# Tests
<por definir>

# Build
<por definir>
```

## Estructura interna

```
sentiment-analysis-banamex/
├── CLAUDE.md
├── .gitignore                # data/raw/ ignorado (corpora pesados)
├── docs/
│   ├── contexto_estrategico_reto_sentimientos_banamex.md  # contexto estratégico del reto
│   ├── taxonomia_revisada.md                              # taxonomía de categorías de sentimiento
│   ├── 20260514_CX_Sucursales_Tec_Monterrey_Hackathon_Caso_CX.pptx  # presentación del caso
│   └── originales/
│       └── Sentiment_analysis_original.zip                # entregable tal como llegó (respaldo)
└── data/raw/                 # corpora del reto (no versionados)
    ├── 1_mitad_2025c.txt     # ~19 MB
    ├── 2_mitad_2025.txt      # ~17 MB
    └── 1_mitad_2026.txt      # ~10 MB
```

## Pendientes activos

- [ ] Definir stack y crear estructura de código (src/, tests/, notebooks/).
- [ ] Leer y resumir `docs/contexto_estrategico_reto_sentimientos_banamex.md` y `docs/taxonomia_revisada.md`.
- [ ] Inspección inicial de los corpora (formato, encoding, volumen real).
- [ ] Definir baseline de clasificación según la taxonomía revisada.

## Notas para Claude

- Los datos son **reales de Banamex** entregados en el marco del reto. Tratarlos como sensibles: nunca commitear los `.txt` de `data/raw/`, nunca pegarlos en herramientas externas.
- El `.zip` original en `docs/originales/` es el entregable inmutable — no modificar, solo conservar.
- El nombre de los corpora (`1_mitad_2025c.txt`, etc.) se preservó tal como vino del entregable para mantener trazabilidad con la presentación. No renombrar sin razón fuerte.
- Idioma: docs en español, código/identificadores en inglés (regla global del usuario).
