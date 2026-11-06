"""CLI del Observatorio BitRate.

    python -m collector collect        # recolecta, alerta y exporta el sitio
    python -m collector report         # genera el reporte semanal (y lo manda a Discord)
    python -m collector export         # solo regenera los JSON del sitio
    python -m collector hide <id>      # oculta una víctima (pedido de baja/corrección)
    python -m collector demo           # carga datos FICTICIOS para probar el sitio
    python -m collector status         # últimas corridas por fuente
    python -m collector geo            # descarga/actualiza las bases DB-IP
"""
import argparse
import sys

from . import discord, geo_update, watchlist
from .config import MAX_ALERTS_PER_RUN
from .db import connect, log_run, now_iso, upsert_ioc, upsert_victim
from .export import export_site
from .geo import geo_available
from .report import weekly
from .sources import abusech, ransomware_live

RED, DIM, OK, RST = "\033[91m", "\033[2m", "\033[92m", "\033[0m"

VICTIM_SOURCES = [("ransomware.live", ransomware_live.fetch)]
IOC_SOURCES = [
    ("threatfox", abusech.fetch_threatfox),
    ("urlhaus", abusech.fetch_urlhaus),
    ("feodo", abusech.fetch_feodo),
]


def banner():
    print(f"{RED}▌{RST} OBSERVATORIO {RED}BITRATE{RST} {DIM}· threat intel AR{RST}")


def _run_source(conn, name, fn, upsert):
    try:
        items = fn()
    except RuntimeError as e:
        if str(e).startswith("SKIP"):
            print(f"  {DIM}↷ {name}: {e}{RST}")
            log_run(conn, name, "skipped", message=str(e))
            return []
        raise
    except Exception as e:  # una fuente caída no frena a las demás
        print(f"  {RED}✗ {name}: {e}{RST}")
        log_run(conn, name, "error", message=repr(e))
        return []
    new = [i for i in items if upsert(conn, i)]
    print(f"  {OK}✓{RST} {name}: {len(items)} relevantes, {len(new)} nuevos")
    log_run(conn, name, "ok", fetched=len(items), new_items=len(new))
    return new


def cmd_collect(args):
    banner()
    try:
        geo_update.update()  # baja DB-IP solo si falta o tiene más de un mes
    except Exception as e:
        print(f"  {DIM}ℹ No se pudo actualizar DB-IP: {e}{RST}")
    if not geo_available():
        print(f"  {DIM}ℹ Geolocalización no disponible: se usan dominios .ar, ASNs conocidos y el país de Feodo{RST}")
    watch = watchlist.load()
    with connect() as conn:
        first_run = conn.execute("SELECT COUNT(*) FROM victims").fetchone()[0] == 0
        new_victims, new_iocs = [], []
        for name, fn in VICTIM_SOURCES:
            new_victims += _run_source(conn, name, fn, upsert_victim)
        for name, fn in IOC_SOURCES:
            new_iocs += _run_source(conn, name, fn, upsert_ioc)

        # ---- Alertas ----
        if not args.no_alerts:
            if first_run and len(new_victims) > MAX_ALERTS_PER_RUN:
                discord.send([{"title": "🟥 Observatorio BitRate en línea",
                               "description": f"Carga inicial: {len(new_victims)} víctimas históricas "
                                              f"y {len(new_iocs)} IOCs. Desde ahora se alertan solo las novedades.",
                               "color": discord.BRAND_RED, "footer": discord.FOOTER}])
            else:
                embeds = []
                hits = [(v, watchlist.check_victim(v, watch)) for v in new_victims]
                hits.sort(key=lambda x: x[1] is None)  # watchlist primero
                for v, hit in hits[:MAX_ALERTS_PER_RUN]:
                    embeds.append(discord.victim_embed({**v, "first_seen": now_iso()}, hit))
                if new_iocs:
                    embeds.append(discord.ioc_embed(new_iocs))
                    for i in new_iocs:
                        if hit := watchlist.check_ioc(i, watch):
                            embeds.append({"title": f"⚠️ WATCHLIST ({hit}) en IOC", "color": discord.BRAND_RED,
                                           "description": f"`{discord._defang(i['value'])}`", "footer": discord.FOOTER})
                if embeds and discord.send(embeds):
                    print(f"  {OK}✓{RST} Discord: {len(embeds)} alertas enviadas")
            conn.execute("UPDATE victims SET alerted = 1 WHERE alerted = 0")
            conn.execute("UPDATE iocs SET alerted = 1 WHERE alerted = 0")

        stats = export_site(conn)
    t = stats["totals"]
    print(f"\n  Víctimas: {t['victims']} ({t['victims_30d']} en 30 días) · Grupos: {t['groups']} · IOCs: {t['iocs']}")
    print(f"  {DIM}Sitio actualizado en site/data/{RST}")


def cmd_report(args):
    banner()
    with connect() as conn:
        md, path = weekly(conn)
    print(f"  {OK}✓{RST} Reporte guardado en {path}")
    if not args.no_alerts and discord.send_report(md):
        print(f"  {OK}✓{RST} Reporte enviado a Discord")


def cmd_export(_):
    with connect() as conn:
        export_site(conn)
    print("Sitio exportado.")


def cmd_hide(args):
    with connect() as conn:
        n = conn.execute("UPDATE victims SET hidden = 1 WHERE id = ?", (args.id,)).rowcount
        export_site(conn)
    print("Ocultada." if n else "No se encontró ese id.")


def cmd_status(_):
    with connect() as conn:
        rows = conn.execute("""SELECT source, status, fetched, new_items, started_at, message FROM runs
                               WHERE id IN (SELECT MAX(id) FROM runs GROUP BY source)""").fetchall()
    for r in rows:
        print(f"{r['source']:16} {r['status']:8} {r['fetched']:>5} rel. {r['new_items']:>4} nuevos  {r['started_at']}  {r['message'] or ''}")


def cmd_geo(_):
    banner()
    print("  Bases actualizadas." if geo_update.update(force=True) else "  Hubo errores (ver arriba).")


def cmd_demo(_):
    from .demo import load_demo
    load_demo()
    print("Datos de demostración cargados (FICTICIOS). Abrí el sitio con:  python -m http.server -d site 8000")


def main(argv=None):
    p = argparse.ArgumentParser(prog="collector", description="Observatorio BitRate")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect"); c.add_argument("--no-alerts", action="store_true"); c.set_defaults(fn=cmd_collect)
    r = sub.add_parser("report"); r.add_argument("--no-alerts", action="store_true"); r.set_defaults(fn=cmd_report)
    sub.add_parser("export").set_defaults(fn=cmd_export)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("demo").set_defaults(fn=cmd_demo)
    sub.add_parser("geo").set_defaults(fn=cmd_geo)
    h = sub.add_parser("hide"); h.add_argument("id"); h.set_defaults(fn=cmd_hide)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
