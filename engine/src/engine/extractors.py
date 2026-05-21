"""Extractores rule-based de los 4 metadatos transversales.

Aplicados sobre las 474k verbalizaciones (no solo el golden set).
Producen la fila de `metadata_extractions` 1:1 por record (`01 §2`).

Funciones puras: cada `extract_*` recibe un string y devuelve estructura
fija. `extract_all` compone las cuatro y devuelve `Metadata` (`01 §4`).
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

# ---------- Tipado público ----------

Polarity = Literal["pos", "neg"]


class PersonnelResult(TypedDict):
    personnel_named: bool
    personnel_name: str | None
    personnel_polarity: Polarity | None


class Metadata(TypedDict):
    personnel_named: bool
    personnel_name: str | None
    personnel_polarity: Polarity | None
    explicit_recommendation: Polarity | None
    mentions_other_bank: bool
    other_bank_names: list[str]
    channels_mentioned: list[str]


# ---------- Carga de diccionarios (resources del paquete) ----------

_DATA_DIR = Path(__file__).resolve().parent / "data"


def _read_lines(path: Path) -> list[str]:
    """Lee líneas no vacías y no comentadas (encoding utf-8)."""
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


@lru_cache(maxsize=1)
def _spanish_names() -> set[str]:
    """Devuelve nombres en forma canónica (Title Case) y sin acentos para lookup."""
    raw = _read_lines(_DATA_DIR / "spanish_names.txt")
    return {_strip_accents(n).lower() for n in raw}


@lru_cache(maxsize=1)
def _mexican_banks() -> list[str]:
    return _read_lines(_DATA_DIR / "mexican_banks.txt")


@lru_cache(maxsize=1)
def _channel_keywords() -> list[tuple[str, list[str]]]:
    """Lista ordenada de (canal_canonico, [keywords sin acentos en minúsculas])."""
    pairs: list[tuple[str, list[str]]] = []
    for line in _read_lines(_DATA_DIR / "channel_keywords.txt"):
        if ":" not in line:
            continue
        canal, kws = line.split(":", 1)
        kw_list = [
            _strip_accents(k.strip()).lower() for k in kws.split(",") if k.strip()
        ]
        # Ordenar más largas primero para que "cajero automatico" gane sobre "cajero".
        kw_list.sort(key=len, reverse=True)
        pairs.append((canal.strip().lower(), kw_list))
    return pairs


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii")


# ---------- Personnel ----------

PERSONNEL_TITLES_RE = re.compile(
    r"(?i)\b("
    r"la\s+srita|la\s+srta|la\s+señora|la\s+sra|la\s+señorita|"
    r"el\s+señor|el\s+sr|"
    r"el\s+lic|la\s+lic|"
    r"el\s+gerente|la\s+gerenta|la\s+gerente|"
    r"el\s+subgerente|la\s+subgerente|"
    r"el\s+cajero|la\s+cajera|"
    r"el\s+ejecutivo|la\s+ejecutiva|"
    r"el\s+asesor|la\s+asesora|"
    r"el\s+supervisor|la\s+supervisora|"
    r"el\s+director|la\s+directora"
    r")\b"
)

# Tokens con capitalización inicial (rastro de nombre propio).
PROPER_NAME_RE = re.compile(r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})\b")

PERSONNEL_BLACKLIST: set[str] = {
    "banamex",
    "citi",
    "citibanamex",
    "mexico",
    "banco",
    "sucursal",
    "nps",
    "atm",
    "bbva",
    "banorte",
    "santander",
    "hsbc",
    "scotiabank",
    "banregio",
    "inbursa",
    "afirme",
    "banbajio",
    "compartamos",
    "netkey",
    "ventanilla",
    "cajero",
    "cajera",
    "gerente",
    "subgerente",
    "ejecutivo",
    "ejecutiva",
    "lic",
    "asesor",
    "asesora",
    "supervisor",
    "supervisora",
    "director",
    "directora",
    "señor",
    "señora",
    "srita",
    "srta",
    "azteca",
    # Días/meses y muletillas frecuentes que aparecen capitalizadas tras puntos.
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
    "buenos",
    "buenas",
    "gracias",
    "muchas",
    "mucho",
    "todo",
    "todos",
    "siempre",
    "nunca",
}

PERSONNEL_POS: set[str] = {
    "amable",
    "amables",
    "atento",
    "atenta",
    "atentos",
    "atentas",
    "profesional",
    "profesionales",
    "eficiente",
    "eficientes",
    "rapido",
    "rapida",
    "rapidos",
    "rapidas",
    "ayuda",
    "ayudo",
    "ayudaron",
    "resolvio",
    "resolvieron",
    "excelente",
    "excelentes",
    "amabilidad",
    "atencion",
    "cordial",
    "cordiales",
    "paciente",
    "pacientes",
    "agradable",
    "agradables",
    "buena",
    "bueno",
    "buenas",
    "buenos",
}

PERSONNEL_NEG: set[str] = {
    "grosero",
    "grosera",
    "groseros",
    "groseras",
    "malo",
    "mala",
    "malos",
    "malas",
    "lento",
    "lenta",
    "lentos",
    "lentas",
    "descortes",
    "descorteses",
    "pesimo",
    "pesima",
    "pesimos",
    "pesimas",
    "prepotente",
    "prepotentes",
    "incompetente",
    "incompetentes",
    "tardado",
    "tardada",
    "negado",
    "negada",
    "indiferente",
    "indiferentes",
    "altanero",
    "altanera",
    "racista",
    "racistas",
    "discriminacion",
}

NAMED_TITLES_RE = re.compile(
    r"(?i)\b(srita|srta|señora|sra|señorita|señor|sr|lic|licenciado|licenciada"
    r"|gerente|gerenta|subgerente|cajero|cajera|ejecutivo|ejecutiva"
    r"|asesor|asesora|supervisor|supervisora|director|directora)\s+"
    r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b"
)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+", text)


def _classify_polarity(window: list[str]) -> Polarity | None:
    """Mayoría simple sobre el set de tokens normalizados (sin acentos, minúsculas)."""
    norm = [_strip_accents(t).lower() for t in window]
    pos = sum(1 for t in norm if t in PERSONNEL_POS)
    neg = sum(1 for t in norm if t in PERSONNEL_NEG)
    if pos == 0 and neg == 0:
        return None
    if pos == neg:
        return None
    return "pos" if pos > neg else "neg"


def _find_name(text: str) -> str | None:
    """Busca un nombre propio válido.

    Prioridad: nombre inmediatamente posterior a un título ("la srita Diana"),
    luego cualquier token capitalizado que esté en `spanish_names.txt` y no en
    la lista negra. Devuelve el nombre en la forma que aparece en el texto.
    """
    names = _spanish_names()

    m = NAMED_TITLES_RE.search(text)
    if m:
        candidate = m.group(2)
        if (
            _strip_accents(candidate).lower() not in PERSONNEL_BLACKLIST
            and _strip_accents(candidate).lower() in names
        ):
            return candidate

    # Fallback: cualquier token Title-case que sea nombre conocido.
    for token in PROPER_NAME_RE.findall(text):
        norm = _strip_accents(token).lower()
        if norm in PERSONNEL_BLACKLIST:
            continue
        if norm in names:
            return token

    return None


def extract_personnel(text: str) -> PersonnelResult:
    """Detecta menciones de personal, su nombre y polaridad por contexto.

    Reglas (03_M2a §Extractor personnel):
    - `personnel_named=True` si hay título genérico o nombre propio válido.
    - `personnel_name` se devuelve sólo si se valida contra spanish_names.txt
      y no cae en la blacklist (Banamex, México, días, etc.).
    - polaridad: ventana de ±10 palabras alrededor de la primera mención.
    """
    if not text:
        return {
            "personnel_named": False,
            "personnel_name": None,
            "personnel_polarity": None,
        }

    title_match = PERSONNEL_TITLES_RE.search(text)
    name = _find_name(text)
    personnel_named = bool(title_match) or name is not None

    polarity: Polarity | None = None
    if personnel_named:
        # Ubicar el anchor: por defecto el match del título; si sólo hay nombre,
        # usamos el nombre.
        anchor_start = title_match.start() if title_match else None
        anchor_end = title_match.end() if title_match else None
        if anchor_start is None and name is not None:
            nm = re.search(rf"\b{re.escape(name)}\b", text)
            if nm:
                anchor_start, anchor_end = nm.start(), nm.end()

        if anchor_start is not None and anchor_end is not None:
            tokens_before = _tokenize(text[:anchor_start])[-10:]
            tokens_after = _tokenize(text[anchor_end:])[:10]
            polarity = _classify_polarity(tokens_before + tokens_after)
        else:
            polarity = _classify_polarity(_tokenize(text))

    return {
        "personnel_named": personnel_named,
        "personnel_name": name,
        "personnel_polarity": polarity,
    }


# ---------- Explicit recommendation ----------

# `recom(?:iend|end)` cubre tanto `recomiendo` (indicativo) como `recomendaría`
# (condicional) y `recomendar` (infinitivo). El boundary `\b` excluiría la 'í',
# así que se omite al cierre.
RE_REC_NEG = re.compile(
    r"(?i)\bno\s+(lo|la|los|las|se\s+lo|se\s+la)\s+recom(?:iend|end)"
)
RE_REC_POS = re.compile(
    r"(?i)\b("
    r"lo\s+recom(?:iend|end)|"
    r"la\s+recom(?:iend|end)|"
    r"los\s+recom(?:iend|end)|"
    r"se\s+(?:lo|la)\s+recom(?:iend|end)|"
    r"recom(?:iend|end)\w*\s+ampliamente"
    r")"
)


def extract_explicit_recommendation(text: str) -> Polarity | None:
    """Devuelve 'pos' / 'neg' / None.

    La negación se evalúa primero (prioridad explícita en 03_M2a).
    Frases sin primera persona ("deberían recomendar") devuelven None.
    """
    if not text:
        return None
    if RE_REC_NEG.search(text):
        return "neg"
    if RE_REC_POS.search(text):
        return "pos"
    return None


# ---------- Other bank ----------

_NON_LETTER_RE = re.compile(r"[^a-zñ]")


def _norm_text_for_bank(text: str) -> str:
    return _strip_accents(text).lower()


def extract_other_bank(text: str) -> list[str]:
    """Devuelve la lista de bancos competidores mencionados, deduplicada en orden de aparición.

    - Match word-boundary case-insensitive.
    - Si el match aparece inmediatamente adyacente a "Banamex" (±2 tokens), se descarta:
      "Banamex Citi" no cuenta como mención a Citi.
    """
    if not text:
        return []
    norm = _norm_text_for_bank(text)
    banks_norm = [(_norm_text_for_bank(b), b) for b in _mexican_banks()]

    # Encontrar todos los tokens "banamex" en el texto normalizado para chequeo de adyacencia.
    banamex_spans = [m.span() for m in re.finditer(r"\bbanamex\b", norm)]

    seen: dict[str, None] = {}
    # Buscar bancos por orden de aparición en el texto.
    matches: list[tuple[int, str]] = []
    for bank_norm, bank_orig in banks_norm:
        pattern = re.compile(r"\b" + re.escape(bank_norm) + r"\b")
        for m in pattern.finditer(norm):
            # Chequear adyacencia con "banamex": tokenizar para distancia en tokens.
            if _is_near_banamex(norm, m.span(), banamex_spans):
                continue
            matches.append((m.start(), bank_orig))

    matches.sort(key=lambda x: x[0])
    for _, bank in matches:
        seen.setdefault(bank, None)
    return list(seen.keys())


def _is_near_banamex(
    norm_text: str, span: tuple[int, int], banamex_spans: list[tuple[int, int]]
) -> bool:
    """True si el span del match está a ≤2 tokens de un span 'banamex'."""
    if not banamex_spans:
        return False
    start, end = span
    for bstart, bend in banamex_spans:
        if bstart < start:
            between = norm_text[bend:start]
        else:
            between = norm_text[end:bstart]
        # Tokens en el segmento intermedio.
        n_tokens = len([t for t in re.split(r"\W+", between) if t])
        if n_tokens <= 2:
            return True
    return False


# ---------- Channels ----------


def extract_channels(text: str) -> list[str]:
    """Devuelve canales canónicos mencionados, deduplicados, en orden de aparición.

    Normalización para búsqueda: lowercase + sin acentos. El texto original
    NO se modifica.
    """
    if not text:
        return []
    norm = _strip_accents(text).lower()

    # Para evitar doble-conteo, marcamos posiciones cubiertas por keywords más largas.
    covered = [False] * len(norm)
    hits: list[tuple[int, str]] = []  # (posición, canal)

    for canal, keywords in _channel_keywords():
        for kw in keywords:
            pattern = re.compile(r"(?<!\w)" + re.escape(kw) + r"(?!\w)")
            for m in pattern.finditer(norm):
                s, e = m.span()
                if any(covered[s:e]):
                    continue
                for i in range(s, e):
                    covered[i] = True
                hits.append((s, canal))

    hits.sort(key=lambda x: x[0])
    seen: dict[str, None] = {}
    for _, canal in hits:
        seen.setdefault(canal, None)
    return list(seen.keys())


# ---------- Compose ----------


def extract_all(text: str) -> Metadata:
    """Composición de los 4 extractores. Firma exigida por `01 §7`."""
    personnel = extract_personnel(text)
    other_banks = extract_other_bank(text)
    return {
        "personnel_named": personnel["personnel_named"],
        "personnel_name": personnel["personnel_name"],
        "personnel_polarity": personnel["personnel_polarity"],
        "explicit_recommendation": extract_explicit_recommendation(text),
        "mentions_other_bank": bool(other_banks),
        "other_bank_names": other_banks,
        "channels_mentioned": extract_channels(text),
    }
