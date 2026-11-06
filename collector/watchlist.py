"""Watchlist: dominios/organizaciones a vigilar. Si aparecen como víctima
o en un IOC, se genera una alerta prioritaria."""
from .config import WATCHLIST_PATH


def load() -> list[str]:
    if not WATCHLIST_PATH.exists():
        return []
    items = []
    for line in WATCHLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if line:
            items.append(line)
    return items


def match(text: str, watch: list[str]) -> str | None:
    t = (text or "").lower()
    for w in watch:
        if w in t:
            return w
    return None


def check_victim(v: dict, watch: list[str]) -> str | None:
    return match(f"{v.get('name')} {v.get('website') or ''}", watch)


def check_ioc(i: dict, watch: list[str]) -> str | None:
    return match(i.get("value", ""), watch)
