"""Send a daily sales summary via the configured WhatsApp Business API."""

from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional

try:
    # Python 3.9+
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from app.db.connection import get_connection
from app.utils.phone import normalize_phone_number
from app.whatsapp.client import WhatsAppClient


logger = logging.getLogger(__name__)


@dataclass
class DailySalesMetrics:
    day: date
    orders: Optional[int] = 0
    revenue: Optional[float] = 0.0
    product_cost: Optional[float] = 0.0
    marketing_spend: Optional[float] = 0.0
    notes: List[str] = field(default_factory=list)

    @property
    def gross_margin(self) -> float:
        revenue = self.revenue or 0.0
        product_cost = self.product_cost or 0.0
        return revenue - product_cost

    @property
    def profit(self) -> float:
        revenue = self.revenue or 0.0
        product_cost = self.product_cost or 0.0
        marketing = self.marketing_spend or 0.0
        return revenue - (product_cost + marketing)

    @property
    def average_order_value(self) -> Optional[float]:
        if not self.orders or self.orders <= 0:
            return None
        revenue = self.revenue or 0.0
        return revenue / self.orders


def _get_first_value(row: dict, candidates: List[str], default=None):
    for key in candidates:
        if key in row and row.get(key) is not None:
            return row.get(key)
    return default


def fetch_sales_metrics(target_day: date) -> DailySalesMetrics:
    metrics = DailySalesMetrics(day=target_day)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # First try the requested dashboard view
                row = None
                columns: List[str] = []
                try:
                    cur.execute(
                        """
                        SELECT *
                        FROM public.v_sales_dashboard
                        WHERE fecha = %s
                        LIMIT 1
                        """,
                        (target_day,),
                    )
                    row = cur.fetchone()
                    if row:
                        columns = [desc[0] for desc in cur.description]
                except Exception as exc_dash:
                    # If the view does not exist or fails, we'll fallback below
                    logger.debug("Fallo al consultar v_sales_dashboard: %s", exc_dash)

                # Fallback to the legacy daily costs view if needed
                used_fallback = False
                if not row:
                    used_fallback = True
                    cur.execute(
                        """
                        SELECT *
                        FROM public.v_sales_costs_daily
                        WHERE day = %s
                        LIMIT 1
                        """,
                        (target_day,),
                    )
                    row = cur.fetchone()
                    if row:
                        columns = [desc[0] for desc in cur.description]
                if row:
                    row_dict = {column: row[idx] for idx, column in enumerate(columns)}

                    orders_val = _get_first_value(
                        row_dict,
                        ["orders", "num_ordenes", "num_orders", "total_orders"],
                    )
                    if orders_val is not None:
                        metrics.orders = int(orders_val or 0)

                    metrics.revenue = float(
                        _get_first_value(
                            row_dict,
                            ["revenue", "revenue_bruto", "ingresos", "gross_revenue"],
                            0.0,
                        )
                        or 0.0
                    )
                    product_cost_val = _get_first_value(
                        row_dict,
                        ["sales_cost", "costo_productos", "costo_producto", "cogs", "costo_mercancia"],
                    )
                    if product_cost_val is not None:
                        metrics.product_cost = float(product_cost_val or 0.0)

                    marketing_val = _get_first_value(
                        row_dict,
                        ["marketing_cost", "marketing_spend", "ad_spend", "costo_marketing", "gasto_marketing"],
                    )
                    if marketing_val is not None:
                        metrics.marketing_spend = float(marketing_val or 0.0)

                    # If product cost wasn't provided directly, try to derive it from unit cost and quantity.
                    if not metrics.product_cost:
                        unit_cost = _get_first_value(row_dict, ["costo_unitario"])
                        quantity = _get_first_value(row_dict, ["cantidad_vendida", "cantidad", "unidades"])
                        shipping_cost = _get_first_value(
                            row_dict, ["costo_envio", "shipping_cost", "envio_total"], 0.0
                        )
                        try:
                            if unit_cost is not None and quantity is not None:
                                metrics.product_cost = (float(unit_cost) * float(quantity)) + float(
                                    shipping_cost or 0.0
                                )
                        except Exception:
                            pass

                    reported_profit = _get_first_value(
                        row_dict, ["profit", "utilidad", "ganancia_neta"]
                    )
                    reported_margin = _get_first_value(
                        row_dict, ["margin_pct", "margen_pct", "margen_porcentaje"]
                    )

                    if reported_profit is not None:
                        expected_profit = metrics.revenue - (metrics.product_cost + metrics.marketing_spend)
                        if abs(expected_profit - float(reported_profit or 0.0)) > 0.01:
                            metrics.product_cost = max(
                                metrics.revenue - float(reported_profit) - metrics.marketing_spend,
                                0.0,
                            )
                        if used_fallback:
                            metrics.notes.append("Utilidad basada en v_sales_costs_daily (fallback).")
                        else:
                            metrics.notes.append("Utilidad basada en v_sales_dashboard.")

                    if reported_margin is not None:
                        metrics.notes.append(f"Margen reportado: {reported_margin}%")
                else:
                    metrics.notes.append(
                        "No se encontraron datos en v_sales_dashboard ni en v_sales_costs_daily."
                    )
    except Exception as exc:
        warning = f"No se pudo obtener el resumen diario desde las vistas configuradas: {exc}"
        logger.error(warning)
        metrics.notes.append(warning)

    return metrics


def format_currency(amount: Optional[float]) -> str:
    if amount is None:
        return "$0.00"
    try:
        return f"${amount:,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def format_integer(value: int) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def build_summary_message(metrics: DailySalesMetrics) -> str:
    lines = [
        f"Resumen de ventas {metrics.day.strftime('%d/%m/%Y')}",
        "",
        f"Pedidos: {format_integer(metrics.orders)}",
        f"Ingresos: {format_currency(metrics.revenue)}",
        f"Costo productos: {format_currency(metrics.product_cost)}",
        f"Inversión marketing: {format_currency(metrics.marketing_spend)}",
        f"Margen bruto: {format_currency(metrics.gross_margin)}",
        f"Utilidad neta aprox.: {format_currency(metrics.profit)}",
    ]

    avg_order = metrics.average_order_value
    if avg_order:
        lines.append(f"Ticket promedio: {format_currency(avg_order)}")

    lines.append("\n¿Necesitas otro detalle? Avísame.")

    if metrics.notes:
        lines.append("")
        for note in metrics.notes:
            lines.append(f"Nota: {note}")

    return "\n".join(lines)


async def send_daily_summary(to_number: str, target_day: date) -> None:
    metrics = await asyncio.to_thread(fetch_sales_metrics, target_day)
    message = build_summary_message(metrics)

    client = WhatsAppClient()
    response = await client.send_text_message(to=to_number, message=message)
    logger.info("WhatsApp API response: %s", response)

async def send_bulk_summaries(to_numbers: List[str], target_day: date) -> None:
    tasks = [send_daily_summary(number, target_day) for number in to_numbers]
    if tasks:
        await asyncio.gather(*tasks)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send the daily sales summary via WhatsApp using configured credentials.",
    )
    parser.add_argument(
        "--to",
        required=True,
        action="append",
        help="Número(s) de destino con código de país. Puede repetirse o usar comas. Acepta '+', espacios o guiones.",
    )
    parser.add_argument(
        "--date",
        help="Fecha objetivo en formato YYYY-MM-DD. Si no se indica, se usa la fecha de hoy.",
    )
    parser.add_argument(
        "--yesterday",
        action="store_true",
        help="Si se indica, usa la fecha de AYER. Ignorado si se provee --date.",
    )
    parser.add_argument(
        "--tz",
        default="America/Santiago",
        help="Zona horaria para calcular AYER cuando se usa --yesterday (por defecto America/Santiago).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Nivel de logging (ej. INFO, DEBUG).",
    )
    return parser.parse_args()


def resolve_target_date(arg_date: Optional[str], use_yesterday: bool, tz_name: str) -> date:
    if not arg_date:
        if use_yesterday:
            if ZoneInfo:
                try:
                    now_local = datetime.now(ZoneInfo(tz_name))
                except Exception:
                    now_local = datetime.utcnow()
            else:
                now_local = datetime.utcnow()
            return (now_local - timedelta(days=1)).date()
        return date.today()
    try:
        return datetime.strptime(arg_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("El parámetro --date debe tener formato YYYY-MM-DD.") from exc


def main() -> None:
    args = parse_args()
    target_date = resolve_target_date(args.date, args.yesterday, args.tz)

    # Permitir múltiples --to y también listas separadas por comas
    raw_targets: List[str] = []
    for entry in args.to:
        raw_targets.extend([p.strip() for p in str(entry).split(",") if p.strip()])
    normalized_numbers: List[str] = []
    for raw in raw_targets:
        normalized = normalize_phone_number(raw)
        if normalized:
            normalized_numbers.append(normalized)
    # Eliminar duplicados preservando orden
    seen = set()
    to_numbers = [x for x in normalized_numbers if not (x in seen or seen.add(x))]

    if not to_numbers:
        raise ValueError("Los números de destino quedaron vacíos después de normalizarlos. Verifica el formato.")

    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s %(message)s")
    logger.info("Enviando resumen de ventas de %s a %s", target_date, ", ".join(to_numbers))

    asyncio.run(send_bulk_summaries(to_numbers, target_date))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(__name__).error("Error al enviar el resumen diario: %s", exc)
        raise


