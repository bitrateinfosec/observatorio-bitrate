"""Geolocalización de IPs y reglas para decidir si algo "es de Argentina"."""
import ipaddress
import re
import socket
from urllib.parse import urlparse

from .config import AR_ASNS, COUNTRY_CODE, GEOIP_ASN_DB, GEOIP_COUNTRY_DB

try:
    import maxminddb  # pip install maxminddb
except ImportError:  # el colector funciona igual, con menos precisión
    maxminddb = None

_country_reader = None
_asn_reader = None


def _readers():
    global _country_reader, _asn_reader
    if maxminddb is None:
        return None, None
    if _country_reader is None and GEOIP_COUNTRY_DB.exists():
        _country_reader = maxminddb.open_database(str(GEOIP_COUNTRY_DB))
    if _asn_reader is None and GEOIP_ASN_DB.exists():
        _asn_reader = maxminddb.open_database(str(GEOIP_ASN_DB))
    return _country_reader, _asn_reader


def geo_available() -> bool:
    c, _ = _readers()
    return c is not None


def is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def lookup_ip(ip: str) -> dict:
    """Devuelve {'country', 'asn', 'as_name'} (lo que se pueda resolver)."""
    out = {"country": None, "asn": None, "as_name": None}
    if not is_ip(ip):
        return out
    c, a = _readers()
    if c:
        rec = c.get(ip) or {}
        out["country"] = (rec.get("country") or rec.get("registered_country") or {}).get("iso_code")
    if a:
        rec = a.get(ip) or {}
        out["asn"] = rec.get("autonomous_system_number")
        out["as_name"] = rec.get("autonomous_system_organization")
    if out["asn"] in AR_ASNS and not out["as_name"]:
        out["as_name"] = AR_ASNS[out["asn"]]
    return out


def host_from(value: str) -> str:
    """Extrae el host de una URL, 'ip:puerto' o dominio."""
    v = value.strip()
    if "://" in v:
        return (urlparse(v).hostname or "").lower()
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}:\d+$", v):
        return v.split(":")[0]
    return v.split("/")[0].split(":")[0].lower()


def is_ar_domain(host: str) -> bool:
    return host.endswith(".ar") or host == "ar"


def classify(value: str, resolve_dns: bool = False) -> dict | None:
    """Decide si un IOC está vinculado a Argentina.

    Devuelve dict con ip/asn/as_name/country/reason, o None si no aplica.
    Criterios (en orden): dominio .ar → IP geolocalizada en AR → ASN argentino.
    """
    host = host_from(value)
    info = {"ip": None, "asn": None, "as_name": None, "country": None, "reason": None}

    if is_ar_domain(host):
        info.update(country=COUNTRY_CODE, reason="dominio .ar")
        return info

    ip = host if is_ip(host) else None
    if ip is None and resolve_dns:
        try:
            ip = socket.gethostbyname(host)
        except OSError:
            ip = None
    if ip is None:
        return None

    info["ip"] = ip
    geo = lookup_ip(ip)
    info.update({k: v for k, v in geo.items() if v})
    if geo["country"] == COUNTRY_CODE:
        info["reason"] = "IP geolocalizada en AR"
        return info
    if geo["asn"] in AR_ASNS:
        info.update(country=COUNTRY_CODE, reason=f"ASN argentino (AS{geo['asn']})")
        return info
    return None
