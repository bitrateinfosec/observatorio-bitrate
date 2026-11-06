"""Fuentes de abuse.ch: ThreatFox (IOCs), URLhaus (URLs de malware) y
Feodo Tracker (servidores C2 de botnets). Los datos de abuse.ch son de
uso libre (CC0); ThreatFox y URLhaus requieren Auth-Key gratuita."""
from ..config import ABUSECH_AUTH_KEY, THREATFOX_DAYS, URLHAUS_LIMIT
from ..db import now_iso
from ..geo import classify
from ..http import get_json, post_json

THREATFOX_API = "https://threatfox-api.abuse.ch/api/v1/"
URLHAUS_RECENT = "https://urlhaus-api.abuse.ch/v1/urls/recent/limit/{n}/"
FEODO_JSON = "https://feodotracker.abuse.ch/downloads/ipblocklist.json"


def _auth():
    if not ABUSECH_AUTH_KEY:
        raise RuntimeError("SKIP: falta ABUSECH_AUTH_KEY")
    return {"Auth-Key": ABUSECH_AUTH_KEY}


def _ioc(source, value, ioc_type, geo, **extra):
    return {
        "id": f"{source}:{value}",
        "value": value,
        "ioc_type": ioc_type,
        "threat": extra.get("threat"),
        "malware": extra.get("malware"),
        "ip": geo.get("ip"),
        "asn": geo.get("asn"),
        "as_name": geo.get("as_name"),
        "country": geo.get("country"),
        "reason": geo.get("reason"),
        "source": source,
        "reference": extra.get("reference"),
        "first_seen": (extra.get("first_seen") or now_iso())[:19].replace(" ", "T"),
    }


def fetch_threatfox() -> list[dict]:
    data = post_json(THREATFOX_API, headers=_auth(), json={"query": "get_iocs", "days": THREATFOX_DAYS})
    if data.get("query_status") != "ok":
        return []
    out = []
    for r in data.get("data") or []:
        value, itype = r.get("ioc", ""), r.get("ioc_type", "")
        if itype.startswith("sha") or itype == "md5_hash":
            continue  # los hashes no tienen ubicación
        geo = classify(value)
        if not geo:
            continue
        out.append(_ioc("threatfox", value, itype, geo,
                        threat=r.get("threat_type"), malware=r.get("malware_printable"),
                        reference=f"https://threatfox.abuse.ch/ioc/{r.get('id')}/",
                        first_seen=r.get("first_seen")))
    return out


def fetch_urlhaus() -> list[dict]:
    data = get_json(URLHAUS_RECENT.format(n=URLHAUS_LIMIT), headers=_auth())
    out = []
    for r in data.get("urls") or []:
        url = r.get("url", "")
        geo = classify(url)
        if not geo:
            continue
        tags = r.get("tags") or []
        out.append(_ioc("urlhaus", url, "url", geo,
                        threat=r.get("threat"), malware=", ".join(tags[:3]) or None,
                        reference=r.get("urlhaus_reference"), first_seen=r.get("date_added")))
    return out


def fetch_feodo() -> list[dict]:
    """Feodo trae país y ASN en el propio feed: no necesita GeoLite2 ni key."""
    data = get_json(FEODO_JSON)
    out = []
    for r in data:
        ip = r.get("ip_address")
        if not ip:
            continue
        country = (r.get("country") or "").upper()
        geo = classify(ip) or {}
        if country != "AR" and geo.get("country") != "AR":
            continue
        geo = {"ip": ip, "asn": r.get("as_number") or geo.get("asn"),
               "as_name": r.get("as_name") or geo.get("as_name"), "country": "AR",
               "reason": geo.get("reason") or "Feodo: país AR"}
        value = f"{ip}:{r.get('port')}" if r.get("port") else ip
        out.append(_ioc("feodo", value, "ip:port", geo, threat="botnet_cc",
                        malware=r.get("malware"),
                        reference=f"https://feodotracker.abuse.ch/browse/host/{ip}/",
                        first_seen=r.get("first_seen")))
    return out
