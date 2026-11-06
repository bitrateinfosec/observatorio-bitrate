"""Configuración central del Observatorio BitRate.

Todo lo sensible (API keys, webhooks) se lee de variables de entorno.
En GitHub Actions se cargan como *Secrets* del repositorio.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"
SITE_DATA_DIR = SITE_DIR / "data"
REPORTS_DIR = ROOT / "reports"
DB_PATH = DATA_DIR / "observatorio.db"
WATCHLIST_PATH = ROOT / "watchlist.txt"

# --- Credenciales (vacías = la fuente o función se saltea) ---
ABUSECH_AUTH_KEY = os.getenv("ABUSECH_AUTH_KEY", "")          # https://auth.abuse.ch (gratis)
RANSOMWARELIVE_API_KEY = os.getenv("RANSOMWARELIVE_API_KEY", "")  # opcional (API PRO)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
DISCORD_WEBHOOK_REPORTS = os.getenv("DISCORD_WEBHOOK_REPORTS", "")  # opcional: canal aparte para reportes

# Geolocalización: DB-IP Lite (gratis, sin registro, CC BY 4.0).
# Se descarga sola con `python -m collector geo` o al correr `collect`.
# Si preferís MaxMind, poné GeoLite2-*.mmdb en data/ y se usan esas.
def _pick_db(*names):
    for n in names:
        if (DATA_DIR / n).exists():
            return DATA_DIR / n
    return DATA_DIR / names[-1]

GEOIP_COUNTRY_DB = Path(os.getenv("GEOIP_COUNTRY_DB") or _pick_db("GeoLite2-Country.mmdb", "dbip-country-lite.mmdb"))
GEOIP_ASN_DB = Path(os.getenv("GEOIP_ASN_DB") or _pick_db("GeoLite2-ASN.mmdb", "dbip-asn-lite.mmdb"))
GEO_MAX_AGE_DAYS = 35  # DB-IP publica una versión nueva cada mes

# URL pública del sitio (con barra final). Se usa en el feed RSS.
SITE_URL = os.getenv("SITE_URL", "https://bitrateinfosec.github.io/observatorio-bitrate/")

# --- Parámetros ---
COUNTRY_CODE = "AR"
USER_AGENT = "ObservatorioBitRate/1.0 (+https://github.com/bitrateinfosec/observatorio-bitrate) threat-intel comunitario"
HTTP_TIMEOUT = 30
THREATFOX_DAYS = 2          # ventana de consulta (1–7)
URLHAUS_LIMIT = 1000        # máx. permitido por la API "recent"
MAX_ALERTS_PER_RUN = 15     # evita inundar Discord en la primera corrida

# ASNs argentinos relevantes (respaldo cuando no hay GeoLite2).
# Lista orientativa: ampliala según necesites.
AR_ASNS = {
    7303: "Telecom Argentina",
    22927: "Telefónica de Argentina",
    11664: "Techtel / Claro",
    27747: "Telecentro",
    10318: "Cablevisión / Fibertel",
    10481: "Prima / Fibertel",
    3449: "Universidad de Buenos Aires",
    4270: "Red de Interconexión Universitaria (RIU)",
    52361: "ARSAT",
    16814: "NSS / IPLAN",
    11315: "Telefónica Móviles Argentina",
    27983: "Red Intercable",
    262186: "Telecentro Móviles",
}

BRAND_RED = 0xFF0000  # rojo de marca Bitrate
