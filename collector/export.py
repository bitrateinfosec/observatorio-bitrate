"""Exporta la base a JSON estáticos que consume el sitio web, más el feed RSS."""
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

from .config import SITE_DATA_DIR, SITE_DIR, SITE_URL
from .db import now_iso
from .sectors import SIN_DATOS, normalize_sector


def _rows(conn, sql, *args):
    return [dict(r) for r in conn.execute(sql, args)]


def _month(d):
    return (d or "")[:7]


def _v_date(v):
    return v.get("published") or v.get("discovered") or v.get("first_seen") or ""


def _top(counter, n):
    return [{"name": k, "count": c} for k, c in counter.most_common(n)]


def build_stats(victims, iocs):
    now = datetime.now(timezone.utc)
    day = lambda n: (now - timedelta(days=n)).strftime("%Y-%m-%d")
    d7, d14, d30, d60, d365 = day(7), day(14), day(30), day(60), day(365)

    # últimos 12 meses (incluye meses en cero)
    months = []
    y, m = now.year, now.month
    for _ in range(12):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    per_month = Counter(_month(_v_date(v)) for v in victims)
    current = f"{now.year:04d}-{now.month:02d}"

    in_range = lambda d, a, b=None: d >= a and (b is None or d < b)
    v30 = [v for v in victims if in_range(_v_date(v), d30)]
    v_prev30 = [v for v in victims if in_range(_v_date(v), d60, d30)]
    v12m = [v for v in victims if in_range(_v_date(v), d365)]
    sector = lambda v: v.get("sector") or SIN_DATOS

    return {
        "generated_at": now_iso(),
        "totals": {
            "victims": len(victims),
            "victims_30d": len(v30),
            "victims_prev_30d": len(v_prev30),
            "victims_7d": sum(1 for v in victims if in_range(_v_date(v), d7)),
            "victims_prev_7d": sum(1 for v in victims if in_range(_v_date(v), d14, d7)),
            "groups": len({v["group_name"] for v in victims}),
            "groups_30d": len({v["group_name"] for v in v30}),
            "groups_prev_30d": len({v["group_name"] for v in v_prev30}),
            "iocs": len(iocs),
            "iocs_7d": sum(1 for i in iocs if in_range(i.get("first_seen") or "", d7)),
            "iocs_prev_7d": sum(1 for i in iocs if in_range(i.get("first_seen") or "", d14, d7)),
        },
        "timeline": [{"month": mo, "count": per_month.get(mo, 0), **({"partial": True} if mo == current else {})}
                     for mo in months],
        "top_groups": _top(Counter(v["group_name"] for v in victims), 10),
        "top_groups_12m": _top(Counter(v["group_name"] for v in v12m), 10),
        "top_groups_30d": _top(Counter(v["group_name"] for v in v30), 5),
        "sectors": _top(Counter(sector(v) for v in victims), 10),
        "sectors_12m": _top(Counter(sector(v) for v in v12m), 10),
        "top_asns": [{"name": f"AS{a} {n or ''}".strip(), "count": c} for (a, n), c in
                     Counter((i["asn"], i.get("as_name")) for i in iocs if i.get("asn")).most_common(8)],
        "malware": _top(Counter(i["malware"] for i in iocs if i.get("malware")), 8),
    }


def _rfc822(d: str) -> str:
    try:
        dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return format_datetime(dt)


def build_feed(victims, limit=50) -> str:
    """RSS 2.0 con las últimas víctimas reivindicadas."""
    items = []
    for v in victims[:limit]:
        d = _v_date(v)
        title = f"{v['name']} · reivindicado por {v['group_name'].upper()}"
        desc = (f"Grupo: {v['group_name'].upper()}. Sector: {v.get('sector') or SIN_DATOS}. "
                f"Fecha de publicación del grupo: {d[:10] or '—'}. "
                "Una reivindicación no confirma por sí sola que el incidente haya ocurrido.")
        items.append(
            "<item>"
            f"<title>{escape(title)}</title>"
            f"<link>{escape(SITE_URL)}#victimas</link>"
            f"<guid isPermaLink=\"false\">bitrate-victim-{escape(v['id'])}</guid>"
            f"<pubDate>{_rfc822(d)}</pubDate>"
            f"<category>{escape(v.get('sector') or SIN_DATOS)}</category>"
            f"<description>{escape(desc)}</description>"
            "</item>")
    now = format_datetime(datetime.now(timezone.utc))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
            "<title>Observatorio BitRate · Víctimas de ransomware en Argentina</title>"
            f"<link>{escape(SITE_URL)}</link>"
            f"<atom:link href=\"{escape(SITE_URL)}feed.xml\" rel=\"self\" type=\"application/rss+xml\"/>"
            "<description>Reivindicaciones de grupos de ransomware sobre organizaciones argentinas. "
            "Un proyecto de Bitrate Infosec.</description>"
            "<language>es-AR</language>"
            f"<lastBuildDate>{now}</lastBuildDate>"
            + "".join(items) +
            "</channel></rss>\n")


def export_site(conn):
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    victims = _rows(conn, """SELECT id, name, group_name, sector, website, published, discovered, first_seen
                              FROM victims WHERE hidden = 0
                              ORDER BY COALESCE(published, discovered, first_seen) DESC""")
    for v in victims:
        v["sector"] = normalize_sector(v["sector"])
    iocs = _rows(conn, """SELECT value, ioc_type, threat, malware, asn, as_name, reason, source, reference, first_seen
                           FROM iocs ORDER BY first_seen DESC LIMIT 2000""")
    stats = build_stats(victims, iocs)

    def dump(name, obj):
        (SITE_DATA_DIR / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

    dump("victims.json", victims)
    dump("iocs.json", iocs)
    dump("stats.json", stats)
    (SITE_DIR / "feed.xml").write_text(build_feed(victims), encoding="utf-8")
    return stats
