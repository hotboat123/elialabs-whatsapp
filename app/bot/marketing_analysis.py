"""Utilities to build structured marketing performance reports."""

from __future__ import annotations

import logging
import math
import unicodedata
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

SCOPE_ALIASES = {
    "campaign": "campaigns",
    "campaigns": "campaigns",
    "campana": "campaigns",
    "campanas": "campaigns",
    "campana publicitaria": "campaigns",
    "campanas publicitarias": "campaigns",
    "nivel 1": "campaigns",
    "adset": "adsets",
    "adsets": "adsets",
    "conjunto": "adsets",
    "conjuntos": "adsets",
    "conjunto de anuncios": "adsets",
    "conjuntos de anuncios": "adsets",
    "nivel 2": "adsets",
    "ad": "ads",
    "ads": "ads",
    "anuncio": "ads",
    "anuncios": "ads",
    "nivel 3": "ads",
}

SCOPE_CONFIG = {
    "campaigns": {
        "label": "campañas",
        "singular": "campaña",
        "group_keys": [
            "campaign_name",
            "name_campaign",
            "campaign",
            "campaign_nombre",
            "nombre_campana",
            "nombre_campaña",
            "campaign_title",
            "titulo_campana",
        ],
        "id_keys": [
            "campaign_id",
            "id_campaign",
            "id_campana",
            "id_campaña",
            "campaignid",
            "campana_id",
        ],
    },
    "adsets": {
        "label": "conjuntos de anuncios",
        "singular": "conjunto de anuncios",
        "group_keys": [
            "adset_name",
            "ad_set_name",
            "name_adset",
            "adset",
            "conjunto",
            "conjunto_de_anuncios",
            "nombre_conjunto",
            "nombre_conjunto_de_anuncios",
        ],
        "id_keys": [
            "adset_id",
            "id_adset",
            "conjunto_id",
            "conjunto_anuncios_id",
            "adsetid",
        ],
    },
    "ads": {
        "label": "anuncios",
        "singular": "anuncio",
        "group_keys": [
            "ad_name",
            "name_ad",
            "ad",
            "nombre_anuncio",
            "ad_title",
            "titulo_anuncio",
        ],
        "id_keys": [
            "ad_id",
            "id_ad",
            "id_anuncio",
            "anuncio_id",
            "adid",
            "creative_id",
        ],
    },
}

SPEND_KEYS = [
    "amount_spent",
    "spend",
    "gasto",
    "gasto_total",
    "inversion",
    "investment",
    "inversion_total",
    "costo",
    "cost",
    "coste",
    "monto_gastado",
    "spent",
]

REVENUE_KEYS = [
    "revenue",
    "ingresos",
    "income",
    "ventas",
    "total_revenue",
    "return",
    "retorno",
    "valor",
    "value",
    "compras_valor",
]

CONVERSION_KEYS = [
    "conversions",
    "conversiones",
    "purchases",
    "compras",
    "sales",
    "ventas_realizadas",
    "resultados",
    "results",
    "leads",
]

CPC_KEYS = [
    "cpc",
    "cost_per_click",
    "costo_por_click",
    "costo_por_clic",
    "coste_por_clic",
    "coste_por_click",
]

CLICKS_KEYS = [
    "clicks",
    "link_clicks",
    "click",
    "clics",
    "clics_enlace",
    "clicks_enlace",
]

DATE_START_KEYS = [
    "start_date",
    "fecha_inicio",
    "period_start",
    "inicio",
    "fecha",
    "date",
    "created_at",
]

DATE_END_KEYS = [
    "end_date",
    "fecha_fin",
    "period_end",
    "fin",
    "updated_at",
]


def normalize_scope(scope: str) -> Optional[str]:
    """Normalize textual scope into canonical key."""

    if not scope:
        return None

    cleaned = _clean_text(scope)
    if not cleaned:
        return None

    if cleaned in SCOPE_ALIASES:
        return SCOPE_ALIASES[cleaned]

    # Try to match via contains logic
    for alias, canonical in SCOPE_ALIASES.items():
        if alias in cleaned:
            return canonical

    return None


def build_marketing_report(data: List[Dict], scope: str) -> str:
    """Build a structured marketing report string for the given scope."""

    config = SCOPE_CONFIG.get(scope)
    if not config:
        return (
            "⚠️ No pude identificar el nivel de análisis solicitado. "
            "Indica si prefieres campañas, conjuntos de anuncios o anuncios."
        )

    aggregates, overall = _aggregate_marketing_data(data, config)

    if not aggregates:
        return (
            f"⚠️ No encontré datos para {config['label']} en el período disponible. "
            "Verifica que la vista incluya columnas con nombres y métricas."
        )

    sorted_entities = sorted(
        aggregates.values(),
        key=lambda entry: (
            entry.get("revenue", 0.0),
            entry.get("conversions", 0.0),
            entry.get("roi", 0.0),
        ),
        reverse=True,
    )

    best_entity = sorted_entities[0]
    top_entities = sorted_entities[: min(3, len(sorted_entities))]

    header = _build_header(config, overall)
    summary = _build_summary_lines(overall)
    standout = _build_standout(best_entity, config)
    top_list = _build_top_list(top_entities, config)
    coverage = _build_coverage(overall)

    sections = [header, summary, standout, top_list]
    if coverage:
        sections.append(coverage)

    sections.append(
        "¿Quieres revisar otro nivel de detalle? Puedes pedir *campañas*, "
        "*conjuntos de anuncios* o *anuncios*."
    )

    return "\n\n".join(filter(None, sections))


def _aggregate_marketing_data(data: List[Dict], config: Dict) -> Tuple[Dict[str, Dict], Dict]:
    aggregates: Dict[str, Dict] = {}
    overall = {
        "total_records": len(data),
        "spend": 0.0,
        "revenue": 0.0,
        "conversions": 0.0,
        "clicks": 0.0,
        "cpc_samples": [],
        "start_date": None,
        "end_date": None,
    }

    for row in data:
        name = _get_first_non_empty(row, config["group_keys"])
        if not name:
            logger.debug("Skipping row without %s name: %s", config["label"], row)
            continue

        key = str(name).strip()
        entry = aggregates.setdefault(
            key,
            {
                "name": key,
                "ids": set(),
                "spend": 0.0,
                "revenue": 0.0,
                "conversions": 0.0,
                "clicks": 0.0,
                "cpc_samples": [],
            },
        )

        entity_id = _get_first_non_empty(row, config["id_keys"])
        if entity_id:
            entry["ids"].add(str(entity_id))

        spend = _extract_numeric(row, SPEND_KEYS)
        revenue = _extract_numeric(row, REVENUE_KEYS)
        conversions = _extract_numeric(row, CONVERSION_KEYS)
        clicks = _extract_numeric(row, CLICKS_KEYS)
        cpc_value = _extract_numeric(row, CPC_KEYS)

        entry["spend"] += spend
        entry["revenue"] += revenue
        entry["conversions"] += conversions
        entry["clicks"] += clicks

        if cpc_value:
            entry["cpc_samples"].append(cpc_value)

        overall["spend"] += spend
        overall["revenue"] += revenue
        overall["conversions"] += conversions
        overall["clicks"] += clicks
        if cpc_value:
            overall["cpc_samples"].append(cpc_value)

        overall["start_date"] = _min_date(
            overall["start_date"], _extract_date(row, DATE_START_KEYS)
        )
        overall["end_date"] = _max_date(
            overall["end_date"], _extract_date(row, DATE_END_KEYS)
        )

    for entry in aggregates.values():
        entry["roi"] = _safe_div(entry["revenue"], entry["spend"])
        if entry["clicks"] > 0:
            entry["cpc"] = _safe_div(entry["spend"], entry["clicks"])
        elif entry["cpc_samples"]:
            entry["cpc"] = sum(entry["cpc_samples"]) / len(entry["cpc_samples"])
        else:
            entry["cpc"] = None
        entry["ids"] = sorted(entry["ids"])

    overall["roi"] = _safe_div(overall["revenue"], overall["spend"])
    if overall["clicks"] > 0:
        overall["cpc"] = _safe_div(overall["spend"], overall["clicks"])
    elif overall["cpc_samples"]:
        overall["cpc"] = sum(overall["cpc_samples"]) / len(overall["cpc_samples"])
    else:
        overall["cpc"] = None

    return aggregates, overall


def _build_header(config: Dict, overall: Dict) -> str:
    label = config["label"].capitalize()
    date_range = _format_date_range(overall.get("start_date"), overall.get("end_date"))
    if date_range:
        return f"📊 Análisis de {label} {date_range}"
    return f"📊 Análisis de {label}"


def _build_summary_lines(overall: Dict) -> str:
    spend = _format_currency(overall.get("spend"))
    revenue = _format_currency(overall.get("revenue"))
    conversions = overall.get("conversions", 0)
    conversions_text = _format_number(conversions)
    roas = overall.get("roi")
    roas_text = f"ROAS {roas:.2f}x" if roas and roas > 0 else "ROAS n/d"
    cpc = overall.get("cpc")
    cpc_text = _format_currency(cpc) if cpc and cpc > 0 else "n/d"

    lines = [
        "🔎 Resumen rápido:",
        f"- Inversión total: {spend}",
        f"- Ingresos generados: {revenue} ({roas_text})",
        f"- Conversiones registradas: {conversions_text}",
        f"- CPC promedio: {cpc_text}",
    ]

    return "\n".join(lines)


def _build_standout(best: Dict, config: Dict) -> str:
    label = config["singular"].capitalize()
    spend = _format_currency(best.get("spend"))
    revenue = _format_currency(best.get("revenue"))
    conversions = _format_number(best.get("conversions", 0))
    roas = best.get("roi")
    roas_text = f"ROAS {roas:.2f}x" if roas and roas > 0 else "ROAS n/d"
    cpc = best.get("cpc")
    cpc_text = _format_currency(cpc) if cpc and cpc > 0 else "n/d"
    ids = ", ".join(best.get("ids", []))
    id_text = f" | IDs: {ids}" if ids else ""

    return (
        f"🥇 {label} destacada: *{best.get('name', 'Sin nombre')}*"
        f" — {revenue} ({roas_text}), {conversions} conv., CPC {cpc_text}, inversión {spend}{id_text}"
    )


def _build_top_list(top_entities: List[Dict], config: Dict) -> str:
    lines = [f"📌 Top {len(top_entities)} {config['label']}:"]
    for idx, entry in enumerate(top_entities, start=1):
        spend = _format_currency(entry.get("spend"))
        revenue = _format_currency(entry.get("revenue"))
        conversions = _format_number(entry.get("conversions", 0))
        roas = entry.get("roi")
        roas_text = f"ROAS {roas:.2f}x" if roas and roas > 0 else "ROAS n/d"
        cpc = entry.get("cpc")
        cpc_text = _format_currency(cpc) if cpc and cpc > 0 else "n/d"
        lines.append(
            f"{idx}. *{entry.get('name', 'Sin nombre')}* — {revenue} | conv. {conversions} | {roas_text} | CPC {cpc_text} | gasto {spend}"
        )
    return "\n".join(lines)


def _build_coverage(overall: Dict) -> Optional[str]:
    total = overall.get("total_records", 0)
    if total <= 0:
        return None
    date_range = _format_date_range(overall.get("start_date"), overall.get("end_date"))
    detail = f"Se analizaron {total} registros de la vista."
    if date_range:
        detail += f" Cobertura: {date_range.replace('(', '').replace(')', '')}."
    return detail


def _extract_numeric(row: Dict, keys: Iterable[str]) -> float:
    for key in keys:
        if key in row and row[key] is not None:
            value = _to_float(row[key])
            if value is not None:
                return value
    return 0.0


def _extract_date(row: Dict, keys: Iterable[str]) -> Optional[datetime]:
    for key in keys:
        if key in row and row[key]:
            parsed = _parse_date(row[key])
            if parsed:
                return parsed
    return None


def _get_first_non_empty(row: Dict, keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        value = row.get(key)
        if value:
            return str(value)
    return None


def _parse_date(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        for fmt in (
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ):
            try:
                return datetime.strptime(text[: len(fmt)], fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            logger.debug("Could not parse date value: %s", value)
            return None
    return None


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isfinite(float(value)):
            return float(value)
        return None
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").replace("%", "").strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _format_currency(value: Optional[float]) -> str:
    if value is None:
        return "$0.00"
    try:
        return f"${value:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"


def _format_number(value: Optional[float]) -> str:
    if value is None:
        return "0"
    if abs(value - round(value)) < 1e-6:
        return f"{int(round(value)):,}"
    return f"{value:,.2f}"


def _safe_div(numerator: float, denominator: float) -> Optional[float]:
    if denominator and denominator != 0:
        return numerator / denominator
    return None


def _format_date_range(start: Optional[datetime], end: Optional[datetime]) -> str:
    if start and end:
        return f"({start.date()} – {end.date()})"
    if start:
        return f"(desde {start.date()})"
    if end:
        return f"(hasta {end.date()})"
    return ""


def _clean_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(stripped.lower().strip().split())


def _min_date(current: Optional[datetime], candidate: Optional[datetime]) -> Optional[datetime]:
    if current and candidate:
        return min(current, candidate)
    return candidate or current


def _max_date(current: Optional[datetime], candidate: Optional[datetime]) -> Optional[datetime]:
    if current and candidate:
        return max(current, candidate)
    return candidate or current


