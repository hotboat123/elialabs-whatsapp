"""
Shared utilities to build business context snippets from the database.
"""
import logging
from typing import Optional, List, Dict

from app.db import business_data

logger = logging.getLogger(__name__)


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
            return _format_records(
                header=f"REPORTE DE VENTAS Y COSTOS ({len(sales_data)} registros):",
                records=sales_data,
            )
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


