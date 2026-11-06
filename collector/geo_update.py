"""Descarga las bases DB-IP Lite (país y ASN) en formato .mmdb.

Gratis, sin registro. Licencia CC BY 4.0: requiere atribución
("IP Geolocation by DB-IP", https://db-ip.com), que ya figura en el sitio.
"""
import gzip
import shutil
import time
from datetime import date

from .config import DATA_DIR, GEO_MAX_AGE_DAYS
from .http import request

URL = "https://download.db-ip.com/free/dbip-{kind}-lite-{ym}.mmdb.gz"
KINDS = {"country": "dbip-country-lite.mmdb", "asn": "dbip-asn-lite.mmdb"}


def _months():
    """Mes actual y anterior (a principio de mes la versión nueva puede no estar)."""
    t = date.today()
    prev = date(t.year - 1, 12, 1) if t.month == 1 else date(t.year, t.month - 1, 1)
    return [t.strftime("%Y-%m"), prev.strftime("%Y-%m")]


def _fresh(path) -> bool:
    return path.exists() and (time.time() - path.stat().st_mtime) < GEO_MAX_AGE_DAYS * 86400


def update(force: bool = False, quiet: bool = False) -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ok = True
    for kind, fname in KINDS.items():
        dest = DATA_DIR / fname
        if not force and _fresh(dest):
            continue
        for ym in _months():
            try:
                r = request("GET", URL.format(kind=kind, ym=ym), retries=2, stream=True, timeout=120)
            except Exception:
                continue
            tmp = dest.with_suffix(".tmp")
            with gzip.GzipFile(fileobj=r.raw) as gz, open(tmp, "wb") as out:
                shutil.copyfileobj(gz, out)
            tmp.replace(dest)
            if not quiet:
                print(f"  ✓ DB-IP {kind} {ym} descargada → data/{fname}")
            break
        else:
            ok = False
            if not quiet:
                print(f"  ✗ No se pudo descargar DB-IP {kind}")
    return ok
