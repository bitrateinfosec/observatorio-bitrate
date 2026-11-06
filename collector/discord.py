"""Alertas a Discord vía webhook (sin bot). Cada evento se manda como embed
con los colores de la marca."""
import time

from .config import BRAND_RED, DISCORD_WEBHOOK_REPORTS, DISCORD_WEBHOOK_URL
from .http import request
from .sectors import normalize_sector

FOOTER = {"text": "Observatorio BitRate · Datos públicos · bitrate infosec"}
WHITE = 0xFFFFFF


def _defang(value: str) -> str:
    """Evita que Discord convierta IOCs en links clickeables."""
    return value.replace("http", "hxxp").replace(".", "[.]")


def send(embeds: list[dict], webhook: str | None = None, content: str | None = None) -> bool:
    url = webhook or DISCORD_WEBHOOK_URL
    if not url:
        return False
    # Discord admite hasta 10 embeds por mensaje
    for i in range(0, len(embeds), 10):
        payload = {"username": "Observatorio BitRate", "embeds": embeds[i:i + 10]}
        if content and i == 0:
            payload["content"] = content
        r = request("POST", url, json=payload, retries=3)
        if r.status_code == 429:
            time.sleep(float(r.json().get("retry_after", 2)))
        time.sleep(0.5)
    return True


def victim_embed(v: dict, watch_hit: str | None = None) -> dict:
    fields = [
        {"name": "Grupo", "value": v["group_name"].upper(), "inline": True},
        {"name": "Sector", "value": normalize_sector(v.get("sector")) or "Sin datos", "inline": True},
        {"name": "Publicado", "value": (v.get("published") or "—")[:10], "inline": True},
    ]
    if v.get("website"):
        fields.append({"name": "Sitio", "value": _defang(v["website"]), "inline": False})
    title = "🚨 Nueva víctima reivindicada en Argentina"
    if watch_hit:
        title = f"⚠️ WATCHLIST ({watch_hit}) · víctima reivindicada"
    return {
        "title": title,
        "description": f"**{v['name']}**\nReivindicado por el grupo **{v['group_name']}**. "
                       "_La reivindicación no confirma el incidente._",
        "color": BRAND_RED,
        "fields": fields,
        "footer": FOOTER,
        "timestamp": v.get("first_seen") or None,
    }


def ioc_embed(items: list[dict]) -> dict:
    lines = []
    for i in items[:15]:
        mal = f" · {i['malware']}" if i.get("malware") else ""
        asn = f" · AS{i['asn']}" if i.get("asn") else ""
        lines.append(f"`{_defang(i['value'])[:70]}`{mal}{asn}")
    extra = f"\n…y {len(items) - 15} más" if len(items) > 15 else ""
    return {
        "title": f"🛰️ {len(items)} IOCs nuevos vinculados a Argentina",
        "description": "\n".join(lines) + extra,
        "color": WHITE,
        "footer": FOOTER,
    }


def send_report(markdown: str) -> bool:
    url = DISCORD_WEBHOOK_REPORTS or DISCORD_WEBHOOK_URL
    body = markdown if len(markdown) <= 4000 else markdown[:3990] + "\n…"
    return send([{"title": "📊 Reporte semanal · Observatorio BitRate",
                  "description": body, "color": BRAND_RED, "footer": FOOTER}], webhook=url)
