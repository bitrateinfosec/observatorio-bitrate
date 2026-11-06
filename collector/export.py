"""Exporta la base a JSON estáticos que consume el sitio web."""
import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from .config import SITE_DATA_DIR
from .db import now_iso


def _rows(conn, sql, *args):
    return [dict(r) for r in conn.execute(sql, args)]


def _month(d):
    return (d or "")[:7]


def build_stats(victims, iocs):
    now = datetime.now(timezone.utc)
    d30 = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    d7 = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    v_date = lambda v: v.get("published") or v.get("discovered") or v.get("first_seen") or ""

    # últimos 12 meses (incluye meses en cero)
    months = []
    y, m = now.year, now.month
    for _ in range(12):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    per_month = Counter(_month(v_date(v)) for v in victims)

    v30 = [v for v in victims if v_date(v) >= d30]
    return {
        "generated_at": now_iso(),
        "totals": {
            "victims": len(victims),
            "victims_30d": len(v30),
            "victims_7d": sum(1 for v in victims if v_date(v) >= d7),
            "groups": len({v["group_name"] for v in victims}),
            "groups_30d": len({v["group_name"] for v in v30}),
            "iocs": len(iocs),
            "iocs_7d": sum(1 for i in iocs if (i.get("first_seen") or "") >= d7),
        },
        "timeline": [{"month": mo, "count": per_month.get(mo, 0)} for mo in months],
        "top_groups": [{"name": g, "count": c} for g, c in
                       Counter(v["group_name"] for v in victims).most_common(10)],
        "top_groups_30d": [{"name": g, "count": c} for g, c in
                           Counter(v["group_name"] for v in v30).most_common(5)],
        "sectors": [{"name": s, "count": c} for s, c in
                    Counter(v.get("sector") or "Sin datos" for v in victims).most_common(10)],
        "top_asns": [{"name": f"AS{a} {n or ''}".strip(), "count": c} for (a, n), c in
                     Counter((i["asn"], i.get("as_name")) for i in iocs if i.get("asn")).most_common(8)],
        "malware": [{"name": m, "count": c} for m, c in
                    Counter(i["malware"] for i in iocs if i.get("malware")).most_common(8)],
    }


def export_site(conn):
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    victims = _rows(conn, """SELECT id, name, group_name, sector, website, published, discovered, first_seen
                              FROM victims WHERE hidden = 0
                              ORDER BY COALESCE(published, discovered, first_seen) DESC""")
    iocs = _rows(conn, """SELECT value, ioc_type, threat, malware, asn, as_name, reason, source, reference, first_seen
                           FROM iocs ORDER BY first_seen DESC LIMIT 2000""")
    stats = build_stats(victims, iocs)

    def dump(name, obj):
        (SITE_DATA_DIR / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

    dump("victims.json", victims)
    dump("iocs.json", iocs)
    dump("stats.json", stats)
    return stats
