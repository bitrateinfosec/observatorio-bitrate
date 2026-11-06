"""Reporte semanal en Markdown (para Discord, el repo y Bitrate Infosec)."""
from collections import Counter
from datetime import datetime, timedelta, timezone

from .config import REPORTS_DIR


def weekly(conn) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    victims = [dict(r) for r in conn.execute(
        """SELECT name, group_name, sector, COALESCE(published, discovered, first_seen) AS d
           FROM victims WHERE hidden = 0 AND COALESCE(published, discovered, first_seen) >= ?
           ORDER BY d DESC""", (since,))]
    iocs = [dict(r) for r in conn.execute(
        "SELECT malware, asn, as_name, source FROM iocs WHERE first_seen >= ?", (since,))]

    groups = Counter(v["group_name"] for v in victims)
    sectors = Counter(v["sector"] or "Sin datos" for v in victims)
    malware = Counter(i["malware"] for i in iocs if i["malware"])
    asns = Counter(f"AS{i['asn']} {i['as_name'] or ''}".strip() for i in iocs if i["asn"])

    week = now.strftime("%G-W%V")
    L = [f"# Observatorio BitRate · Reporte semanal {week}",
         f"_Período: {since} → {now:%Y-%m-%d}_", "",
         "## Resumen",
         f"- **{len(victims)}** víctimas argentinas reivindicadas por grupos de ransomware",
         f"- **{len(groups)}** grupos activos contra organizaciones del país",
         f"- **{len(iocs)}** IOCs nuevos vinculados a infraestructura argentina", ""]
    if groups:
        g, c = groups.most_common(1)[0]
        L += [f"## Grupo de la semana: {g.upper()} ({c} víctimas)", ""]
    if victims:
        L += ["## Víctimas reivindicadas", "| Fecha | Organización | Grupo | Sector |", "|---|---|---|---|"]
        L += [f"| {v['d'][:10]} | {v['name']} | {v['group_name']} | {v['sector'] or '—'} |" for v in victims[:25]]
        L.append("")
    if sectors:
        L += ["## Sectores más afectados"] + [f"- {s}: {c}" for s, c in sectors.most_common(5)] + [""]
    if malware:
        L += ["## Familias de malware con infraestructura en AR"] + [f"- {m}: {c}" for m, c in malware.most_common(5)] + [""]
    if asns:
        L += ["## Redes (ASN) con más IOCs"] + [f"- {a}: {c}" for a, c in asns.most_common(5)] + [""]
    L += ["## Recomendaciones",
          "- Verificá que tus accesos remotos (VPN, RDP) tengan MFA y estén actualizados.",
          "- Bloqueá en tu perímetro los IOCs publicados en el observatorio.",
          "- Probá la restauración de tus backups offline: es lo que te salva ante un ransomware.", "",
          "---",
          "_Una reivindicación en un sitio de filtración no confirma por sí sola un incidente. "
          "Fuentes: ransomware.live, abuse.ch (ThreatFox, URLhaus, Feodo Tracker)._"]
    md = "\n".join(L)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{week}.md"
    path.write_text(md, encoding="utf-8")
    return md, str(path)
