"""
Shared utilities to build business context snippets from the database.
"""
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from app.config import get_settings
from app.db import business_data

logger = logging.getLogger(__name__)

settings = get_settings()


async def build_business_context(message: Optional[str], phone_number: Optional[str] = None) -> Optional[str]:
    """
    Retrieve relevant analytics context from the database based on the message intent.

    Args:
        message: Incoming user message (used to infer which views to query)
        phone_number: Optional phone to personalize queries

    Returns:
        String with formatted context or None if no data is available.
    """
    if not message:
        return None

    message_lower = message.lower()
    context_parts: List[str] = []

    try:
        # Sales / revenue / financial words (including numeric shortcuts)
        if any(
            word in message_lower
            for word in [
                "ventas",
                "venta",
                "ingresos",
                "revenue",
                "facturación",
                "facturacion",
                "mes",
                "meses",
                "día",
                "dia",
                "semana",
                "costos",
                "gastos",
            ]
        ) or message_lower.strip() in ["1", "uno"]:
            context_parts.append(await _build_sales_context())

        # Marketing intent
        if (
            any(
                word in message_lower
                for word in [
                    "marketing",
                    "anuncios",
                    "anuncio",
                    "publicidad",
                    "ads",
                    "campaña",
                    "campana",
                    "roi",
                ]
            )
            or message_lower.strip() in ["2", "dos"]
        ):
            context_parts.append(await _build_marketing_context())

        # Product analytics
        if (
            any(
                word in message_lower
                for word in [
                    "productos más vendidos",
                    "top productos",
                    "productos vendidos",
                    "productos populares",
                    "productos",
                ]
            )
            or message_lower.strip() in ["4", "cuatro"]
        ):
            context_parts.append(await _build_products_context())

        # Financial metrics
        if (
            any(
                word in message_lower
                for word in [
                    "financiero",
                    "financieros",
                    "gastos",
                    "costos",
                    "margen",
                    "ganancia",
                    "utilidad",
                ]
            )
            or message_lower.strip() in ["5", "cinco"]
        ):
            context_parts.append(await _build_financial_context())

        # General analytics / dashboard intent
        if (
            any(
                word in message_lower
                for word in [
                    "reporte",
                    "reportes",
                    "análisis",
                    "analisis",
                    "métricas",
                    "metricas",
                    "estadísticas",
                    "estadisticas",
                    "dashboard",
                ]
            )
            or message_lower.strip() in ["6", "seis"]
        ):
            context_parts.append(await _build_general_context())

        # Orders by phone (if phone provided)
        if phone_number and any(word in message_lower for word in ["pedido", "orden", "compra"]):
            context_parts.append(await _build_orders_context(phone_number))

        # Clean empty sections
        context_parts = [part for part in context_parts if part]
        access_summary = await _build_db_access_summary()
        if access_summary:
            context_parts.append(access_summary)
        if context_parts:
            return "\n".join(context_parts)

    except Exception as exc:
        logger.warning("Error building business context (non-critical): %s", exc)

    return None


async def _build_sales_context() -> str:
    try:
        sales_data = await business_data.get_monthly_sales_costs(limit=50)
        if not sales_data:
            sales_data = await business_data.get_sales_report(limit=50)

        if sales_data:
            insights = _build_sales_insights(sales_data)
            sections = []
            if insights:
                sections.append(insights)
            sections.append(
                _format_records(
                    header=f"REPORTE DE VENTAS Y COSTOS ({len(sales_data)} registros):",
                    records=sales_data,
                )
            )
            return "\n\n".join(sections)
        return "⚠️ No se encontraron datos de ventas en la base de datos."
    except Exception as exc:
        logger.warning("Error getting sales data: %s", exc)
        return "⚠️ No se pudo consultar la base de datos en este momento."


async def _build_marketing_context() -> str:
    try:
        marketing_data = await business_data.get_marketing_report(limit=50)
        if marketing_data:
            return _format_records(
                header=f"REPORTE DE MARKETING ({len(marketing_data)} registros):",
                records=marketing_data,
            )
        return "⚠️ No se encontraron datos de marketing en la base de datos."
    except Exception as exc:
        logger.error("Error getting marketing data: %s", exc)
        return f"❌ Error consultando marketing: {exc}"


async def _build_products_context() -> str:
    try:
        products = await business_data.get_top_products(limit=20)
        if products:
            return _format_records(
                header=f"PRODUCTOS MÁS VENDIDOS ({len(products)} encontrados):",
                records=products,
            )
        return "⚠️ No se encontraron datos de productos en la base de datos."
    except Exception as exc:
        logger.error("Error getting products data: %s", exc)
        return f"❌ Error consultando productos: {exc}"


async def _build_financial_context() -> str:
    try:
        financial_data = await business_data.get_financial_report(limit=50)
        if financial_data:
            return _format_records(
                header=f"REPORTE FINANCIERO ({len(financial_data)} registros):",
                records=financial_data,
            )
        return "⚠️ No se encontraron datos financieros en la base de datos."
    except Exception as exc:
        logger.error("Error getting financial data: %s", exc)
        return f"❌ Error consultando datos financieros: {exc}"


async def _build_general_context() -> str:
    try:
        analytics_data = await business_data.get_general_analytics(limit=50)
        if analytics_data:
            return _format_records(
                header=f"ANÁLISIS GENERAL ({len(analytics_data)} registros):",
                records=analytics_data,
            )
        return "⚠️ No se encontraron datos de analytics en la base de datos."
    except Exception as exc:
        logger.error("Error getting analytics data: %s", exc)
        return f"❌ Error consultando analytics: {exc}"


async def _build_orders_context(phone_number: str) -> str:
    try:
        orders = await business_data.get_orders_by_phone(phone_number, limit=5)
        if orders:
            return _format_records(
                header=f"ÚLTIMOS PEDIDOS PARA {phone_number}:",
                records=orders,
            )
        return f"⚠️ No se encontraron pedidos para {phone_number}."
    except Exception as exc:
        logger.error("Error getting orders for %s: %s", phone_number, exc)
        return f"❌ Error consultando pedidos para {phone_number}: {exc}"


def _format_records(header: str, records: List[Dict]) -> str:
    lines = [header]
    for record in records[:10]:
        record_info = ", ".join(
            [f"{k}: {v}" for k, v in record.items() if v is not None][:5]
        )
        lines.append(f"- {record_info}")
    return "\n".join(lines)


def _build_sales_insights(records: List[Dict]) -> Optional[str]:
    best_month = None
    earliest_month = None
    best_revenue = -1.0
    best_margin: Optional[float] = None

    for row in records:
        month_value = _pick_value(row, ["month", "mes", "fecha", "dia"])
        month_date = _parse_month_value(month_value)

        revenue = _safe_float(
            _pick_value(
                row,
                ["revenue", "ingresos", "precio_venta", "precio_total", "revenue_bruto"],
                0.0,
            )
        )
        costs = _safe_float(
            _pick_value(
                row,
                ["costs", "costo", "gastos_totales", "costos"],
                0.0,
            )
        )
        profit = _safe_float(
            _pick_value(
                row,
                ["profit", "utilidad", "ganancia"],
                revenue - costs,
            )
        )
        margin_raw = _pick_value(
            row,
            ["margin_pct", "margen_pct", "margen"],
        )
        margin_pct = _safe_float(margin_raw) if margin_raw is not None else None
        if margin_pct is None and revenue:
            margin_pct = (profit / revenue * 100) if revenue else None

        if month_date:
            if earliest_month is None or month_date < earliest_month:
                earliest_month = month_date

            if revenue is not None and revenue > best_revenue:
                best_revenue = revenue
                best_month = month_date
                best_margin = margin_pct

    insights_lines = []
    if best_month:
        month_label = _format_month(best_month)
        if best_margin is not None:
            insights_lines.append(
                f"🏆 Mejor mes histórico: {month_label} con ingresos de {_format_currency(best_revenue)} "
                f"y margen {best_margin:.1f}%."
            )
        else:
            insights_lines.append(
                f"🏆 Mejor mes histórico: {month_label} con ingresos de {_format_currency(best_revenue)}."
            )

    if earliest_month:
        insights_lines.append(
            f"📅 Primer registro disponible: {_format_month(earliest_month)}."
        )

    if not insights_lines:
        return None

    return "INSIGHTS HISTÓRICOS:\n" + "\n".join(f"- {line}" for line in insights_lines)


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _format_currency(value: float) -> str:
    try:
        return "$" + f"{float(value):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def _pick_value(row: Dict, candidates: List[str], default: Any = None) -> Any:
    for key in candidates:
        if key in row and row.get(key) is not None:
            return row.get(key)
    return default


def _parse_month_value(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value.replace(day=1)
    if isinstance(value, datetime):
        return value.date().replace(day=1)
    if isinstance(value, str):
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                parsed = datetime.strptime(value, fmt).date()
                return parsed.replace(day=1)
            except ValueError:
                continue
        # Try simple YYYY-MM format
        try:
            parsed = datetime.strptime(value[:7], "%Y-%m").date()
            return parsed.replace(day=1)
        except Exception:
            return None
    return None


async def _build_db_access_summary() -> Optional[str]:
    earliest, latest = await business_data.get_sales_dashboard_date_range()
    lines: List[str] = []
    enabled_views = settings.get_enabled_views()
    if enabled_views:
        lines.append(f"Vistas habilitadas: {', '.join(enabled_views)}.")
    else:
        lines.append("El bot puede consultar todas las vistas que tus credenciales permiten.")

    if earliest:
        lines.append(f"El historial en v_sales_dashboard_planilla empieza el {earliest.strftime('%Y-%m-%d')}.")
    if latest:
        lines.append(f"Último registro disponible: {latest.strftime('%Y-%m-%d')}.")

    if not lines:
        return None

    return "BASE DE DATOS:\n" + "\n".join(f"- {line}" for line in lines)


def _format_month(value: date) -> str:
    try:
        return value.strftime("%Y-%m")
    except Exception:
        return value.isoformat()


