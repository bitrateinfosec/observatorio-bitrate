"""Fuente: ransomware.live — agregador de publicaciones de sitios de filtración.

Solo se toman METADATOS (nombre, grupo, fechas, sector). El observatorio
nunca accede a sitios .onion ni descarga datos filtrados.

⚠ Revisá los Términos y Condiciones de ransomware.live antes de publicar
sus datos en un sitio público y mantené siempre la atribución.
"""
import hashlib
import os

from ..config import COUNTRY_CODE, RANSOMWARELIVE_API_KEY
from ..http import get_json
from ..sectors import normalize_sector

NAME = "ransomware.live"

# Endpoints configurables por si la API cambia de versión.
FREE_URL = os.getenv("RL_FREE_URL", "https://api.ransomware.live/v2/countryvictims/{cc}")
PRO_URL = os.getenv("RL_PRO_URL", "https://api-pro.ransomware.live/victims/?country={cc}")



def _pick(d: dict, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return None


def _date(v):
    return str(v)[:19].replace(" ", "T") if v else None


def normalize(raw: dict) -> dict | None:
    name = _pick(raw, "post_title", "victim", "name", "title")
    group = _pick(raw, "group_name", "group", "gang")
    if not name or not group:
        return None
    sector_raw = str(_pick(raw, "activity", "sector", "industry") or "").strip()
    sector = normalize_sector(sector_raw)
    vid = hashlib.sha1(f"{group.lower()}|{name.lower().strip()}".encode()).hexdigest()[:16]
    return {
        "id": vid,
        "name": name.strip(),
        "group_name": group.strip().lower(),
        "sector": sector,
        "website": _pick(raw, "website", "domain"),
        "country": (_pick(raw, "country") or COUNTRY_CODE).upper(),
        "published": _date(_pick(raw, "published", "attackdate", "date")),
        "discovered": _date(_pick(raw, "discovered", "discovery_date")),
        "source": NAME,
    }


def fetch() -> list[dict]:
    if RANSOMWARELIVE_API_KEY:
        data = get_json(PRO_URL.format(cc=COUNTRY_CODE), headers={"X-API-KEY": RANSOMWARELIVE_API_KEY})
    else:
        data = get_json(FREE_URL.format(cc=COUNTRY_CODE))
    if isinstance(data, dict):  # algunas versiones envuelven la lista
        data = data.get("victims") or data.get("data") or []
    out = []
    for raw in data:
        v = normalize(raw)
        if v and v["country"] == COUNTRY_CODE:
            out.append(v)
    return out
