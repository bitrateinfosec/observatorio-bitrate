"""Datos de DEMOSTRACIÓN 100% ficticios para probar el sitio sin API keys.
Usa una base separada para no mezclarse nunca con datos reales."""
import random
from datetime import datetime, timedelta, timezone

from . import config

GROUPS = ["akira", "ransomhub", "lockbit3", "medusa", "play", "qilin", "8base", "hunters"]
SECTORS = ["Salud", "Sector público", "Industria", "Educación", "Agro y alimentos",
           "Comercio", "Finanzas", "Transporte y logística", "Tecnología", "Construcción"]
MALWARE = ["Cobalt Strike", "QakBot", "Mirai", "AsyncRAT", "Remcos", "Emotet", "Lumma Stealer"]


def load_demo(seed: int = 7):
    config.DB_PATH = config.DATA_DIR / "demo.db"
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    from . import db
    from .export import export_site
    db.DB_PATH = config.DB_PATH

    rnd = random.Random(seed)
    now = datetime.now(timezone.utc)
    with db.connect() as conn:
        for n in range(1, 96):
            d = now - timedelta(days=int(rnd.triangular(0, 360, 20)), hours=rnd.randint(0, 23))
            g = rnd.choices(GROUPS, weights=[9, 7, 6, 4, 4, 3, 2, 2])[0]
            db.upsert_victim(conn, {
                "id": f"demo{n:03d}", "name": f"Organización Demo {n:02d} S.A.", "group_name": g,
                "sector": rnd.choice(SECTORS), "website": f"demo{n:02d}.example",
                "country": "AR", "published": d.strftime("%Y-%m-%dT%H:%M:%S"),
                "discovered": d.strftime("%Y-%m-%dT%H:%M:%S"), "source": "demo"})
        asns = list(config.AR_ASNS.items())[:6]
        for n in range(1, 61):
            a, name = rnd.choice(asns)
            ip = f"198.51.100.{n}"  # rango TEST-NET-2 (RFC 5737): no es una IP real
            d = now - timedelta(days=rnd.randint(0, 25), hours=rnd.randint(0, 23))
            kind = rnd.choice(["ip:port", "url"])
            value = f"{ip}:{rnd.choice([443, 8080, 4444, 2222])}" if kind == "ip:port" else f"http://{ip}/bins/demo{n}"
            db.upsert_ioc(conn, {
                "id": f"demo:{value}", "value": value, "ioc_type": kind,
                "threat": "botnet_cc" if kind == "ip:port" else "payload_delivery",
                "malware": rnd.choice(MALWARE), "ip": ip, "asn": a, "as_name": name, "country": "AR",
                "reason": f"ASN argentino (AS{a})", "source": rnd.choice(["threatfox", "urlhaus", "feodo"]),
                "reference": None, "first_seen": d.strftime("%Y-%m-%dT%H:%M:%S")})
        export_site(conn)
    import json
    p = config.SITE_DATA_DIR / "stats.json"
    s = json.loads(p.read_text()); s["demo"] = True
    p.write_text(json.dumps(s, ensure_ascii=False, indent=1))
