# Demo — Análisis de sentimientos Banamex

MVP que procesa verbalizaciones de encuestas NPS de Banamex, las clasifica en una
taxonomía de causas de experiencia (CX) y las presenta en un dashboard ejecutivo
con vista nacional y por sucursal.

Este documento está pensado para el **jurado** del reto o para una persona del
área de CX que necesite levantar la demo en su laptop. No requiere conocimiento
de programación más allá de saber abrir una terminal.

---

## 1. ¿Qué vas a ver?

- **Vista nacional**: NPS year-to-date, brecha vs. objetivo, top causas de
  detracción, top fortalezas, sucursales críticas.
- **Vista por sucursal**: comentarios representativos, personal mencionado,
  palabras más frecuentes.
- **Comparación de meses**: cómo cambian los indicadores entre periodos.
- **Sección admin** (POC): muestra los archivos cargados y las corridas de
  anotación / entrenamiento del clasificador, para evidenciar la trazabilidad.

---

## 2. Requisitos

- **Docker Desktop** instalado y corriendo (macOS, Linux, o Windows con WSL2).
- ~10 GB libres en disco.
- Una terminal (Terminal.app en macOS, PowerShell en Windows, etc.).

Opcional, solo si quieres **regenerar las anotaciones LLM desde cero**:

- [Ollama](https://ollama.com) instalado y el modelo `qwen2.5:7b-instruct` descargado.

---

## 3. Quick start con DB pre-generada (≈ 2 minutos)

Esta es la ruta **recomendada para la demo**. Asume que el equipo te entregó el
archivo `banamex.db.gz` por separado.

```bash
git clone <repo> sentiment-analysis-banamex
cd sentiment-analysis-banamex

# Copiar plantilla de variables de entorno.
cp .env.example .env

# Colocar el archivo entregado por el equipo en data/processed/
mkdir -p data/processed
cp /ruta/donde/recibiste/banamex.db.gz data/processed/

# Extraer la DB.
python scripts/seed_db.py

# Levantar todo el stack (API + Web) en un solo comando.
bash scripts/start.sh
```

> El script `start.sh` se encarga de lanzar Docker Desktop si está apagado,
> hacer `docker compose up -d`, esperar a que la API esté lista y validar
> que el clasificador esté cargado. Alternativa equivalente: `docker compose
> up --build` (más verbose; útil si quieres ver los logs en vivo).

Cuando veas en los logs algo como:

```
banamex-api  | INFO:     Uvicorn running on http://0.0.0.0:8000
banamex-web  | ... ready to handle connections
```

Abre en el navegador:

```
http://localhost:3000
```

Haz login con **cualquier usuario y contraseña** (el MVP no valida credenciales
contra ninguna base; cualquier combinación devuelve un token válido). Llegarás
directo a la vista nacional con datos cargados.

Para detener el stack: `bash scripts/start.sh --stop` (o `docker compose down`).

---

## 4. Quick start desde cero (≈ 5–7 horas, requiere Ollama)

Solo si quieres regenerar todo el pipeline a partir de los corpora `.txt`
crudos. Útil para verificar la trazabilidad completa o para re-ejecutar
sobre datos nuevos.

```bash
# 1. Ollama corriendo en el host (NO dentro de Docker).
brew install ollama        # o instalador oficial en otras plataformas
ollama serve &
ollama pull qwen2.5:7b-instruct

# 2. Variables de entorno.
cp .env.example .env

# 3. Instalar paquetes Python en modo editable.
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ./core ./engine ./analytics ./api

# 4. Colocar los corpora en data/raw/  (ver CLAUDE.md para la lista de archivos).

# 5. Ejecutar el pipeline completo. Reportes intermedios en stdout.
python scripts/preprocess_corpora.py

# 6. Levantar el stack como en el Quick start anterior.
bash scripts/start.sh
```

El script `preprocess_corpora.py` es **idempotente**: si lo cortas a la mitad y
lo vuelves a correr, salta las fases que ya están hechas. Usa `--help` para ver
las flags de `--skip-*` y `--force-*`.

---

## 5. Flujo sugerido para presentar la demo (5–7 minutos)

1. **Login** (≈ 15 s) — Mencionar que en MVP cualquier credencial vale; en
   producción se integraría con el SSO corporativo.
2. **Pantalla de upload** (≈ 30 s) — El sistema ya tiene los 3 corpora del reto
   cargados; mostrar el carrusel ilustrativo de la carga.
3. **Vista nacional YTD** (≈ 90 s) — Explicar NPS actual vs. objetivo, los top
   topics de detracción y de fortalezas, y la lista de sucursales críticas.
4. **Click en una sucursal crítica** (≈ 90 s) — Explicar comentarios
   representativos, personal mencionado, palabras top. Insistir en que cada
   bullet es **trazable a un comentario real**, no inferencia.
5. **Volver a vista nacional → Comparación de meses** (≈ 60 s) — Mostrar cómo
   cambian los indicadores entre periodos (endpoint `/national/compare`).
6. **Sección admin** (≈ 30 s) — Evidencia de trazabilidad: archivos cargados,
   sha256, corridas del anotador LLM, corridas del entrenamiento del
   clasificador.

---

## 6. Solución de problemas

**El navegador dice “No se puede establecer conexión”.**
Espera ~30 s después de `docker compose up`. El frontend depende de que la API
pase su healthcheck. Si persiste, revisa `docker compose logs api`.

**El frontend carga pero los datos vienen vacíos.**
Verifica que la DB esté en su lugar:

```bash
ls -lh data/processed/banamex.db
```

Si el archivo no existe o pesa < 1 KB, corre `python scripts/seed_db.py`
de nuevo o vuelve a ejecutar `python scripts/preprocess_corpora.py`.

**Puerto 8000 o 3000 ocupado.**
Edita `.env` y cambia `API_PORT` y/o el mapeo `3000:80` en `docker-compose.yml`.
Importante: si cambias `API_PORT`, también actualiza `VITE_API_URL` antes de
volver a hacer `docker compose build`, porque Vite inyecta esa URL **en build**,
no en runtime.

**`docker compose build` falla en el paso de instalación de Python.**
Suele ser falta de espacio en disco. Libera al menos 5 GB y reintenta.

**`ollama serve` no corre o falta el modelo.**
Solo aplica si estás regenerando las anotaciones (Quick start desde cero). Para
la demo con DB pre-generada, **Ollama no es necesario**. Verifica con:

```bash
curl http://localhost:11434/api/tags
ollama list
```

**El smoke test falla.**
Asegúrate de que el stack esté arriba (`docker compose ps` debe mostrar ambos
servicios `running`/`healthy`), y corre `bash scripts/smoke_test.sh`. Requiere
`curl` y `jq` instalados localmente.

---

## 7. Datos del reto — aviso de uso

Los corpora son **reales de Banamex**, entregados en el marco del reto del Tec
de Monterrey. No los compartas externamente, no los subas a ningún servicio en
la nube ni a herramientas web de terceros. Están listados en `.gitignore` para
evitar accidentes de versionado.

---

## 8. Referencias rápidas

| Archivo                                       | Para qué sirve                                          |
|-----------------------------------------------|---------------------------------------------------------|
| `docker-compose.yml`                          | Define los servicios `api` y `web`.                     |
| `scripts/preprocess_corpora.py`               | Pipeline offline completo (idempotente).                |
| `scripts/seed_db.py`                          | Extrae la DB pre-generada.                              |
| `scripts/smoke_test.sh`                       | Verifica los endpoints clave de la API.                 |
| `scripts/generate_openapi_client.sh`          | Regenera el cliente TS del frontend.                    |
| `.env.example`                                | Plantilla de variables de entorno.                      |
| `docs/ESTADO.md`                              | Estado vivo del proyecto entre etapas.                  |
| `CLAUDE.md`                                   | Spec estable del proyecto.                              |
