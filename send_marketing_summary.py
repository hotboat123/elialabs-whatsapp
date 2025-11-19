"""Send a marketing performance summary via WhatsApp."""

from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from app.db.connection import get_connection
from app.utils.phone import normalize_phone_number
from app.whatsapp.client import WhatsAppClient

logger = logging.getLogger(__name__)


@dataclass
class MarketingEntity:
    name: str
    spend: float = 0.0
    revenue: float = 0.0
    conversions: float = 0.0
    clicks: float = 0.0

    @property
    def roas(self) -> Optional[float]:
        if self.spend > 0:
            return self.revenue / self.spend
        return None

    @property
    def cpc(self) -> Optional[float]:
        if self.clicks > 0:
            return self.spend / self.clicks
        return None


@dataclass
class MarketingSummary:
    interval_label: str
    total_spend: float = 0.0
    total_revenue: float = 0.0
    total_conversions: float = 0.0
    total_clicks: float = 0.0
    campaigns: List[MarketingEntity] = field(default_factory=list)
    ads: List[MarketingEntity] = field(default_factory=list)


MARKETING_QUERY = """
    SELECT *
    FROM public.v_marketing_campaigns_daily
    WHERE fecha >= %s
      AND fecha < %s
"""


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if hasattr(value, "normalize"):
        # Decimal
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fetch_marketing_records(start_date: date, end_date: date) -> List[Dict[str, Any]]:
    logger.info(f"\n{'='*60}\nCONSULTANDO DATOS DE MARKETING\n{'='*60}")
    logger.info(f"Rango de fechas: {start_date} a {end_date}")
    logger.info(f"Query: {MARKETING_QUERY}")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(MARKETING_QUERY, (start_date, end_date))
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description] if cur.description else []
                
                logger.info(f"Columnas encontradas: {columns}")
                logger.info(f"Filas obtenidas: {len(rows)}")
                
                if rows and len(rows) > 0:
                    logger.info(f"Primera fila ejemplo: {dict(zip(columns, rows[0]))}")
    except Exception as exc:
        logger.error("No se pudieron obtener los datos de marketing: %s", exc)
        return []

    records: List[Dict[str, Any]] = []
    for db_row in rows:
        record: Dict[str, Any] = {}
        for idx, column in enumerate(columns):
            record[column] = db_row[idx]
        records.append(record)
        
    logger.info(f"Total registros procesados: {len(records)}")
    if records:
        logger.info(f"Registro ejemplo completo: {records[0]}")
    logger.info(f"{'='*60}\n")
    
    return records


def _aggregate_entities(rows: Iterable[Dict[str, Any]], key: str) -> List[MarketingEntity]:
    aggregates: Dict[str, MarketingEntity] = {}

    for row in rows:
        raw_name = row.get(key) or row.get("campaign")
        if not raw_name:
            continue

        name = str(raw_name).strip()
        entity = aggregates.setdefault(name, MarketingEntity(name=name))
        entity.spend += _to_float(row.get("spend"))
        entity.revenue += _to_float(row.get("revenue_generated"))
        entity.conversions += _to_float(row.get("conversions"))
        entity.clicks += _to_float(row.get("clicks"))

    sorted_entities = sorted(
        aggregates.values(),
        key=lambda item: (item.revenue, item.conversions, item.roas or 0.0),
        reverse=True,
    )
    return sorted_entities


def build_summary(records: List[Dict[str, Any]], interval_label: str) -> MarketingSummary:
    summary = MarketingSummary(interval_label=interval_label)

    if not records:
        logger.warning("No hay registros para procesar")
        return summary

    logger.info(f"\n{'='*60}\nAGREGANDO MÉTRICAS DE MARKETING\n{'='*60}")
    
    for idx, row in enumerate(records, 1):
        spend = _to_float(row.get("spend"))
        revenue = _to_float(row.get("revenue_generated"))
        conversions = _to_float(row.get("conversions"))
        clicks = _to_float(row.get("clicks"))
        campaign = row.get("campaign", "N/A")
        
        logger.info(f"\nFila {idx} - Campaña: {campaign}")
        logger.info(f"  Inversión: ${spend:,.0f}")
        logger.info(f"  Ingresos: ${revenue:,.0f}")
        logger.info(f"  Conversiones: {conversions}")
        logger.info(f"  Clicks: {clicks}")
        
        summary.total_spend += spend
        summary.total_revenue += revenue
        summary.total_conversions += conversions
        summary.total_clicks += clicks

    logger.info(f"\n{'='*60}\nTOTALES ACUMULADOS:\n{'='*60}")
    logger.info(f"Inversión total: ${summary.total_spend:,.0f}")
    logger.info(f"Ingresos totales: ${summary.total_revenue:,.0f}")
    logger.info(f"Conversiones totales: {summary.total_conversions}")
    logger.info(f"Clicks totales: {summary.total_clicks}")
    logger.info(f"{'='*60}\n")

    summary.campaigns = _aggregate_entities(records, "campaign")[:3]
    # No hay ads separados en v_marketing_campaigns_daily
    summary.ads = []

    return summary


def _format_currency(value: Optional[float]) -> str:
    if value is None:
        return "$0"
    try:
        # Redondear a entero y usar punto como separador de miles
        value_int = int(round(float(value or 0)))
        formatted = f"{value_int:,}".replace(",", ".")
        return f"${formatted}"
    except (TypeError, ValueError):
        return "$0"


def _format_number(value: Optional[float]) -> str:
    if value is None:
        return "0"
    try:
        # Redondear a entero y usar punto como separador de miles
        value_int = int(round(float(value)))
        return f"{value_int:,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def _format_roas(value: Optional[float]) -> str:
    if value and value > 0:
        return f"{value:.2f}x"
    return "n/d"


def _format_cpc(value: Optional[float]) -> str:
    if value and value > 0:
        return _format_currency(value)
    return "n/d"


def build_message(summary: MarketingSummary) -> str:
    lines = [
        f"Resumen marketing {summary.interval_label}",
        "",
        f"Inversión: {_format_currency(summary.total_spend)}",
        f"Ingresos generados: {_format_currency(summary.total_revenue)}",
        f"Conversiones: {_format_number(summary.total_conversions)}",
        f"Clicks: {_format_number(summary.total_clicks)}",
    ]
    
    # Calcular ROAS total
    total_roas = summary.total_revenue / summary.total_spend if summary.total_spend > 0 else 0
    lines.append(f"ROAS: {_format_roas(total_roas)}")
    
    # Calcular CPC total
    total_cpc = summary.total_spend / summary.total_clicks if summary.total_clicks > 0 else 0
    lines.append(f"CPC promedio: {_format_currency(total_cpc)}")

    if summary.campaigns:
        lines.append("")
        lines.append("Campañas:")
        for idx, campaign in enumerate(summary.campaigns, start=1):
            lines.append(
                f"{idx}. {campaign.name}\n"
                f"   Inversión: {_format_currency(campaign.spend)}\n"
                f"   Conversiones: {_format_number(campaign.conversions)}\n"
                f"   ROAS: {_format_roas(campaign.roas)}\n"
                f"   CPC: {_format_cpc(campaign.cpc)}"
            )

    if not summary.campaigns:
        lines.append("")
        lines.append("No se encontraron campañas de marketing para esta fecha.")

    lines.append("")
    lines.append("¿Necesitas otro detalle? Avísame.")
    return "\n".join(lines)


async def send_marketing_summary(to_number: str, target_day: date) -> None:
    start_date = target_day
    end_date = target_day + timedelta(days=1)
    records = await asyncio.to_thread(fetch_marketing_records, start_date, end_date)
    summary = build_summary(records, target_day.strftime("%d/%m/%Y"))
    message = build_message(summary)

    client = WhatsAppClient()
    response = await client.send_text_message(to=to_number, message=message)
    logger.info("WhatsApp API response: %s", response)


async def send_monthly_summary(to_number: str, month_start: date) -> None:
    start_date = month_start.replace(day=1)
    end_date = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    records = await asyncio.to_thread(fetch_marketing_records, start_date, end_date)
    summary = build_summary(records, start_date.strftime("%m/%Y"))
    message = build_message(summary)

    client = WhatsAppClient()
    response = await client.send_text_message(to=to_number, message=message)
    logger.info("WhatsApp API response: %s", response)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a marketing summary via WhatsApp using the configured Business API credentials.",
    )
    parser.add_argument(
        "--to",
        required=True,
        help="Número de destino con código de país (acepta '+', espacios o guiones).",
    )
    parser.add_argument(
        "--date",
        help="Fecha objetivo en formato YYYY-MM-DD. Si no se indica, se usa la fecha de hoy.",
    )
    parser.add_argument(
        "--frequency",
        choices=["daily", "monthly"],
        default="daily",
        help="Tipo de resumen de marketing a enviar (daily o monthly).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Nivel de logging (ej. INFO, DEBUG).",
    )
    return parser.parse_args()


def resolve_target_date(arg_date: Optional[str]) -> date:
    if not arg_date:
        return date.today()
    try:
        return datetime.strptime(arg_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("El parámetro --date debe tener formato YYYY-MM-DD.") from exc


def main() -> None:
    args = parse_args()
    to_number = normalize_phone_number(args.to)

    if not to_number:
        raise ValueError("El número de destino quedó vacío después de normalizarlo. Verifica el formato.")

    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s %(message)s")
    logger.info("Enviando resumen de marketing (%s) a %s", args.frequency, to_number)

    if args.frequency == "daily":
        target_date = resolve_target_date(args.date)
        asyncio.run(send_marketing_summary(to_number, target_date))
    else:
        summary_month = resolve_target_date(args.date).replace(day=1)
        asyncio.run(send_monthly_summary(to_number, summary_month))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(__name__).error("Error al enviar el resumen de marketing: %s", exc)
        raise


