"""Normalización de sectores a un set corto en español.

ransomware.live cambió su taxonomía con el tiempo ("Healthcare", "Professional
Services", "Government & Defense"…). Se normaliza al guardar y también al
exportar, así los registros viejos de la base quedan consistentes.
"""

SIN_DATOS = "Sin datos"

_MAP = {
    # Salud
    "healthcare": "Salud", "health": "Salud", "hospital": "Salud", "pharmaceutical": "Salud",
    "pharma": "Salud", "salud": "Salud",
    # Sector público
    "public sector": "Sector público", "government": "Sector público",
    "government & defense": "Sector público", "government and defense": "Sector público",
    "defense": "Sector público", "sector público": "Sector público",
    # Educación
    "education": "Educación", "educación": "Educación",
    # Finanzas
    "financial services": "Finanzas", "finance": "Finanzas", "banking": "Finanzas",
    "insurance": "Finanzas", "finanzas": "Finanzas",
    # Industria
    "manufacturing": "Industria", "industrial": "Industria", "industria": "Industria",
    # Tecnología
    "technology": "Tecnología", "it": "Tecnología", "information technology": "Tecnología",
    "tecnología": "Tecnología",
    # Telecomunicaciones
    "telecommunication": "Telecomunicaciones", "telecommunications": "Telecomunicaciones",
    "telecomunicaciones": "Telecomunicaciones",
    # Construcción e inmobiliario
    "construction": "Construcción", "real estate": "Construcción e inmobiliario",
    "construcción": "Construcción",
    # Transporte
    "transportation/logistics": "Transporte y logística", "transportation": "Transporte y logística",
    "logistics": "Transporte y logística", "transporte y logística": "Transporte y logística",
    # Comercio
    "retail": "Comercio", "retail & e-commerce": "Comercio", "e-commerce": "Comercio",
    "wholesale": "Comercio", "comercio": "Comercio",
    # Servicios profesionales
    "business services": "Servicios profesionales", "professional services": "Servicios profesionales",
    "consulting": "Servicios profesionales", "legal": "Servicios profesionales",
    "servicios empresariales": "Servicios profesionales",
    # Servicios al consumidor
    "consumer services": "Servicios", "services": "Servicios", "servicios": "Servicios",
    # Agro
    "agriculture and food production": "Agro y alimentos", "agriculture": "Agro y alimentos",
    "food & beverage": "Agro y alimentos", "agro y alimentos": "Agro y alimentos",
    # Energía
    "energy": "Energía y servicios públicos", "energy & utilities": "Energía y servicios públicos",
    "utilities": "Energía y servicios públicos", "oil & gas": "Energía y servicios públicos",
    "energía": "Energía y servicios públicos",
    # Turismo
    "hospitality": "Turismo y gastronomía", "hospitality and tourism": "Turismo y gastronomía",
    "tourism": "Turismo y gastronomía", "turismo": "Turismo y gastronomía",
    # Medios
    "media": "Medios y entretenimiento", "media & entertainment": "Medios y entretenimiento",
    "entertainment": "Medios y entretenimiento",
    # Otros
    "other": "Otros", "others": "Otros", "otros": "Otros", "non-profit": "ONG", "nonprofit": "ONG",
    "not found": None, "unknown": None, "n/a": None, "": None,
}


def normalize_sector(raw) -> str | None:
    """Devuelve el sector en español o None si no hay dato."""
    if raw is None:
        return None
    s = str(raw).strip()
    key = s.lower()
    if key in _MAP:
        return _MAP[key]
    # Si ya viene en español o es un valor nuevo, se respeta tal cual.
    return s or None
