"""Send a daily sales summary via the configured WhatsApp Business API."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
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
    shipping_cost: Optional[float] = 0.0
    marketing_spend: Optional[float] = 0.0
    notes: List[str] = field(default_factory=list)

    @property
    def gross_margin(self) -> float:
        revenue = self.revenue or 0.0
        product_cost = self.product_cost or 0.0
        shipping_cost = self.shipping_cost or 0.0
        return revenue - product_cost - shipping_cost

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
                    # Leer filas del día desde la nueva vista 'v_sales_dashboard_planilla'
                    # Toleramos distintos nombres de columna de fecha (dia/fecha/day).
                    cur.execute(
                        """
                        SELECT *
                        FROM public.v_sales_dashboard_planilla
                        WHERE dia = %s
                        """,
                        (target_day,),
                    )
                    columns = [desc[0] for desc in cur.description] if cur.description else []
                    fetched_rows = cur.fetchall()
                    if fetched_rows:
                        # Convertir a dicts por fila
                        columns_lower = [c.lower() for c in columns]
                        rows_dicts = [
                            {columns_lower[idx]: value for idx, value in enumerate(row_tuple)}
                            for row_tuple in fetched_rows
                        ]

                        logger.debug(f"Columnas encontradas: {columns_lower}")
                        if rows_dicts:
                            logger.debug(f"Primera fila ejemplo: {rows_dicts[0]}")
                        logger.info(f"\n{'='*60}\nPROCESANDO {len(rows_dicts)} FILAS PARA {target_day}\n{'='*60}")

                        # Acumular métricas desde filas
                        revenue_total = 0.0
                        shipping_total = 0.0
                        order_ids: set = set()
                        sku_to_sum: dict = {}
                        sku_to_count: dict = {}

                        for idx, row_dict in enumerate(rows_dicts, 1):
                            # Extraer valores de la fila
                            precio_venta = float(
                                _get_first_value(
                                    row_dict,
                                    ["precio_venta", "revenue_bruto", "revenue", "precio_total", "precio"],
                                    0.0,
                                )
                                or 0.0
                            )
                            costo_envio = float(
                                _get_first_value(
                                    row_dict,
                                    ["costo_envio", "shipping_cost", "envio_total"],
                                    0.0,
                                )
                                or 0.0
                            )
                            order_id = _get_first_value(
                                row_dict,
                                [
                                    "order_id",
                                    "orden_id",
                                    "id_orden",
                                    "order",
                                    "id_order",
                                    "orderid",
                                    "order_number",
                                    "numero_orden",
                                ],
                            )
                            sku = _get_first_value(row_dict, ["sku"])
                            costo_unitario = _get_first_value(row_dict, ["costo_unitario", "unit_cost", "costo"])
                            producto = _get_first_value(row_dict, ["producto", "product", "product_name"])
                            
                            # Log detallado de cada fila
                            logger.info(f"\nFila {idx}:")
                            logger.info(f"  Producto: {producto}")
                            logger.info(f"  SKU: {sku}")
                            logger.info(f"  Order ID: {order_id}")
                            logger.info(f"  Precio venta: ${precio_venta:,.0f}")
                            logger.info(f"  Costo unitario: ${float(costo_unitario or 0):,.0f}")
                            logger.info(f"  Costo envío: ${costo_envio:,.0f}")
                            
                            # Acumular
                            revenue_total += precio_venta
                            shipping_total += costo_envio
                            
                            if order_id is not None:
                                text_id = str(order_id).strip()
                                if text_id:
                                    order_ids.add(text_id)
                                    logger.info(f"  ✓ Order ID agregado: {text_id[:20]}...")
                            
                            if sku is not None and costo_unitario is not None:
                                # Acumular el costo por cada unidad vendida (cada fila = 1 unidad)
                                sku_to_sum[sku] = sku_to_sum.get(sku, 0.0) + float(costo_unitario or 0.0)
                                sku_to_count[sku] = sku_to_count.get(sku, 0) + 1

                        # Asignar métricas agregadas
                        logger.info(f"\n{'='*60}\nRESUMEN DE CÁLCULOS:\n{'='*60}")
                        logger.info(f"Total filas procesadas: {len(rows_dicts)}")
                        logger.info(f"Ingresos acumulados: ${revenue_total:,.0f}")
                        logger.info(f"Envíos acumulados: ${shipping_total:,.0f}")
                        logger.info(f"Order IDs únicos encontrados: {len(order_ids)}")
                        logger.info(f"  -> {list(order_ids)}")
                        
                        metrics.revenue = revenue_total
                        metrics.shipping_cost = shipping_total
                        
                        # Costo productos: suma total del costo de todas las unidades vendidas
                        logger.info(f"\nCálculo de Costo Productos:")
                        product_cost_total = 0.0
                        for sku, total_cost in sku_to_sum.items():
                            count = sku_to_count.get(sku, 1)
                            product_cost_total += total_cost
                            logger.info(f"  SKU {sku}: ${float(total_cost/count):,.0f} × {count} unidades = ${total_cost:,.0f}")
                        
                        logger.info(f"Costo productos TOTAL: ${product_cost_total:,.0f}")
                        metrics.product_cost = product_cost_total
                        metrics.orders = len(order_ids) if order_ids else 0
                        
                        # Cálculo de margen y ticket
                        margen = revenue_total - product_cost_total - shipping_total
                        ticket = revenue_total / len(order_ids) if len(order_ids) > 0 else 0
                        logger.info(f"\nMétricas finales:")
                        logger.info(f"  Margen bruto: ${revenue_total:,.0f} - ${product_cost_total:,.0f} - ${shipping_total:,.0f} = ${margen:,.0f}")
                        logger.info(f"  Ticket promedio: ${revenue_total:,.0f} / {len(order_ids)} pedidos = ${ticket:,.0f}")
                        logger.info(f"{'='*60}\n")
                        # Fallback: si no detectamos order_id, intentar deducir desde columnas que contengan "order"
                        if metrics.orders == 0 and rows_dicts:
                            dynamic_order_ids = set()
                            order_like_columns = [c for c in columns_lower if "order" in c or "orden" in c]
                            for row_dict in rows_dicts:
                                for col in order_like_columns:
                                    val = row_dict.get(col)
                                    if val is not None:
                                        tid = str(val).strip()
                                        if tid:
                                            dynamic_order_ids.add(tid)
                                            break
                            if dynamic_order_ids:
                                metrics.orders = len(dynamic_order_ids)
                            else:
                                # Como último recurso, sumar num_ordenes si existe en filas
                                try:
                                    metrics.orders = int(
                                        sum(
                                            int(row_dict.get("num_ordenes") or 0)
                                            for row_dict in rows_dicts
                                        )
                                    )
                                except Exception:
                                    pass
                        # Logs de depuración para entender el ticket promedio
                        try:
                            logger.debug(
                                "DEBUG resumen %s -> ingresos=%s, pedidos=%s, order_ids=%s",
                                target_day,
                                revenue_total,
                                metrics.orders,
                                sorted(list(order_ids))[:10],
                            )
                        except Exception:
                            pass
                        metrics.notes.append("Cálculo basado en v_sales_dashboard_planilla.")
                        # Señalamos que se obtuvo data, asignando row truthy:
                        row = True  # marcador para saltar fallback
                except Exception as exc_dash:
                    # If the view does not exist or fails, we'll fallback below
                    logger.debug("Fallo al consultar v_sales_dashboard_planilla: %s", exc_dash)
                    try:
                        # Asegurar que la transacción no quede abortada antes del fallback
                        conn.rollback()
                    except Exception:
                        pass

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
                if row and isinstance(row, tuple):
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

                    shipping_val = _get_first_value(
                        row_dict,
                        ["shipping_cost", "costo_envio", "envio_total"],
                    )
                    if shipping_val is not None:
                        metrics.shipping_cost = float(shipping_val or 0.0)

                    marketing_val = _get_first_value(
                        row_dict,
                        ["marketing_cost", "marketing_spend", "ad_spend", "costo_marketing", "gasto_marketing"],
                    )
                    if marketing_val is not None:
                        metrics.marketing_spend = float(marketing_val or 0.0)

                    # If product cost wasn't provided directly, try to derive it from unit cost and quantity (excluding shipping).
                    if not metrics.product_cost:
                        unit_cost = _get_first_value(row_dict, ["costo_unitario"])
                        quantity = _get_first_value(row_dict, ["cantidad_vendida", "cantidad", "unidades"])
                        try:
                            if unit_cost is not None and quantity is not None:
                                metrics.product_cost = float(unit_cost) * float(quantity)
                        except Exception:
                            pass

                    reported_profit = _get_first_value(
                        row_dict, ["profit", "utilidad", "ganancia_neta"]
                    )
                    reported_margin = _get_first_value(
                        row_dict, ["margin_pct", "margen_pct", "margen_porcentaje"]
                    )

                    if reported_profit is not None:
                        expected_profit = metrics.revenue - (
                            (metrics.product_cost or 0.0)
                            + (metrics.shipping_cost or 0.0)
                            + (metrics.marketing_spend or 0.0)
                        )
                        if abs(expected_profit - float(reported_profit or 0.0)) > 0.01:
                            # Ajustar costo de producto preservando envío y marketing
                            metrics.product_cost = max(
                                metrics.revenue
                                - float(reported_profit or 0.0)
                                - (metrics.marketing_spend or 0.0)
                                - (metrics.shipping_cost or 0.0),
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
        return "$0"
    try:
        # Redondear a entero y usar punto como separador de miles
        value_int = int(round(float(amount or 0)))
        formatted = f"{value_int:,}".replace(",", ".")
        return f"${formatted}"
    except (TypeError, ValueError):
        return "$0"


def format_integer(value: int) -> str:
    try:
        # Usar punto como separador de miles
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def build_summary_message(metrics: DailySalesMetrics) -> str:
    lines = [
        f"Resumen de ventas {metrics.day.strftime('%d/%m/%Y')}",
        "",
        f"Pedidos: {format_integer(metrics.orders)}",
        f"Ingresos: {format_currency(metrics.revenue)}",
        f"Costo productos: {format_currency(metrics.product_cost)}",
        f"Costo envíos: {format_currency(metrics.shipping_cost)}",
        f"Margen bruto: {format_currency(metrics.gross_margin)}",
    ]

    avg_order = metrics.average_order_value
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
        "--daemon-schedule",
        action="store_true",
        help="Ejecuta como proceso en segundo plano y envía todos los días a la hora indicada.",
    )
    parser.add_argument(
        "--at",
        default="08:00",
        help="Hora local HH:MM para --daemon-schedule (por defecto 08:00).",
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


def parse_hhmm(value: str) -> tuple[int, int]:
    try:
        parts = value.strip().split(":")
        if len(parts) != 2:
            raise ValueError
        hour = int(parts[0])
        minute = int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        return hour, minute
    except Exception as exc:
        raise ValueError("El parámetro --at debe tener formato HH:MM de 24 horas.") from exc


def get_recipients_from_args_or_env(arg_to: Optional[List[str]]) -> List[str]:
    # Permitir múltiples --to y también listas separadas por comas
    raw_targets: List[str] = []
    if arg_to:
        for entry in arg_to:
            raw_targets.extend([p.strip() for p in str(entry).split(",") if p.strip()])
    if not raw_targets:
        env_targets = os.getenv("DAILY_SUMMARY_TO", "")
        if env_targets:
            raw_targets.extend([p.strip() for p in env_targets.split(",") if p.strip()])

    normalized_numbers: List[str] = []
    for raw in raw_targets:
        normalized = normalize_phone_number(raw)
        if normalized:
            normalized_numbers.append(normalized)
    # Eliminar duplicados preservando orden
    seen = set()
    return [x for x in normalized_numbers if not (x in seen or seen.add(x))]


def run_daemon_schedule(to_numbers: List[str], tz_name: str, at_hhmm: str) -> None:
    hour, minute = parse_hhmm(at_hhmm)
    logger.info("Iniciando scheduler diario interno a las %02d:%02d %s", hour, minute, tz_name)
    if not ZoneInfo:
        logger.warning("zoneinfo no disponible; se usará UTC para el cálculo de hora.")
    while True:
        # Hora actual en zona indicada (o UTC si no hay zoneinfo)
        now_local = datetime.now(ZoneInfo(tz_name)) if ZoneInfo else datetime.utcnow()
        next_run_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run_local <= now_local:
            next_run_local += timedelta(days=1)

        # Calcular tiempo de espera en segundos usando UTC para precisión
        now_utc = datetime.utcnow()
        # Convertir next_run_local a UTC si hay zoneinfo, sino ya es UTC-like
        if ZoneInfo:
            next_run_utc = next_run_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        else:
            next_run_utc = next_run_local
        sleep_seconds = max(1, int((next_run_utc - now_utc).total_seconds()))
        logger.info("Próxima ejecución local: %s, esperando %d segundos", next_run_local.isoformat(), sleep_seconds)
        try:
            time.sleep(sleep_seconds)
            # Fecha objetivo: AYER respecto de la zona local en el momento programado
            run_local_now = datetime.now(ZoneInfo(tz_name)) if ZoneInfo else datetime.utcnow()
            target_date = (run_local_now - timedelta(days=1)).date()
            logger.info("Ejecutando envío diario para %s a %s", target_date, ", ".join(to_numbers))
            asyncio.run(send_bulk_summaries(to_numbers, target_date))
        except Exception as exc:
            logger.error("Error durante ejecución programada: %s", exc)
            # Esperar un minuto y reintentar el bucle para no entrar en spin si hay fallos repetidos
            time.sleep(60)


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s %(message)s")
    to_numbers = get_recipients_from_args_or_env(args.to)

    if args.daemon_schedule:
        if not to_numbers:
            raise ValueError(
                "Debes indicar destinatarios con --to (puede repetirse o comas) "
                "o definir la variable de entorno DAILY_SUMMARY_TO."
            )
        run_daemon_schedule(to_numbers, args.tz, args.at)
        return

    target_date = resolve_target_date(args.date, args.yesterday, args.tz)
    if not to_numbers:
        raise ValueError(
            "Los números de destino quedaron vacíos después de normalizarlos. "
            "Verifica --to o la variable de entorno DAILY_SUMMARY_TO."
        )
    logger.info("Enviando resumen de ventas de %s a %s", target_date, ", ".join(to_numbers))
    asyncio.run(send_bulk_summaries(to_numbers, target_date))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(__name__).error("Error al enviar el resumen diario: %s", exc)
        raise


