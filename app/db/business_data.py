"""
Business data queries - Access to specific views for e-commerce data
"""
import logging
from datetime import date, datetime
from typing import List, Dict, Optional, Any

from app.config import get_settings
from app.db.connection import get_connection

logger = logging.getLogger(__name__)

settings = get_settings()


def _get_first_value(row: Dict[str, Any], candidates: List[str], default=None):
    for key in candidates:
        if key in row and row.get(key) is not None:
            return row.get(key)
    return default


def _parse_date_value(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _normalize_view_name(view_name: str) -> str:
    """Normalize view names for comparison (handle schema prefixes and quotes)."""
    if not view_name:
        return ""
    normalized = view_name.strip().strip('"').strip()
    if '.' in normalized:
        normalized = normalized.split('.')[-1]
    return normalized.lower()


ENABLED_VIEWS = {_normalize_view_name(name) for name in settings.get_enabled_views()}

if ENABLED_VIEWS:
    logger.info("Database view restrictions enabled: %s", ", ".join(sorted(ENABLED_VIEWS)))


def _is_view_allowed(view_name: str) -> bool:
    """Check if a view is allowed based on configuration."""
    if not ENABLED_VIEWS:
        return True
    return _normalize_view_name(view_name) in ENABLED_VIEWS


def _filter_allowed_views(possible_names: List[str]) -> List[str]:
    """Filter a list of candidate view names by the enabled views configuration."""
    if not ENABLED_VIEWS:
        return possible_names
    filtered = [name for name in possible_names if _is_view_allowed(name)]
    if not filtered:
        logger.warning(
            "No enabled views found among candidates: %s. Allowed views: %s",
            ", ".join(possible_names),
            ", ".join(sorted(ENABLED_VIEWS))
        )
    return filtered


async def query_view(view_name: str, limit: int = 50, filters: Optional[Dict[str, Any]] = None) -> List[Dict]:
    """
    Query a specific database view
    
    Args:
        view_name: Name of the view to query
        limit: Maximum number of rows to return
        filters: Optional dictionary of filters (column: value)
    
    Returns:
        List of dictionaries with row data
    """
    try:
        # Validate view name to prevent SQL injection (only allow alphanumeric and underscores)
        if not view_name.replace('_', '').replace('.', '').isalnum():
            raise ValueError(f"Invalid view name: {view_name}")

        if not _is_view_allowed(view_name):
            raise PermissionError(f"View '{view_name}' is not enabled for querying")
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Build query with proper parameterization
                # View name is validated above, but we still use it carefully
                query = f'SELECT * FROM "{view_name}"'
                params = []
                
                # Add filters if provided
                if filters:
                    conditions = []
                    for key, value in filters.items():
                        # Validate column name
                        if not key.replace('_', '').isalnum():
                            raise ValueError(f"Invalid column name: {key}")
                        conditions.append(f'"{key}" = %s')
                        params.append(value)
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)
                
                query += " LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                # Get column names
                columns = [desc[0] for desc in cur.description] if cur.description else []
                
                # Convert to list of dictionaries
                rows = []
                for row in results:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # Convert datetime/timestamp to ISO format
                        if hasattr(value, 'isoformat'):
                            row_dict[col] = value.isoformat()
                        else:
                            row_dict[col] = value
                    rows.append(row_dict)
                
                logger.info(f"Query executed on view '{view_name}': {len(rows)} rows returned")
                return rows
                
    except Exception as e:
        logger.error(f"Error querying view '{view_name}': {e}")
        return []


async def get_products(search_term: Optional[str] = None, limit: int = 20) -> List[Dict]:
    """
    Get products from database (try common view/table names)
    
    Args:
        search_term: Optional search term for product name/description
        limit: Maximum number of products
    
    Returns:
        List of products
    """
    # Try common view/table names for products
    possible_names = [
        'v_products', 'view_products', 'products_view',
        'productos', 'v_productos',
        'products', 'product'
    ]

    possible_names = _filter_allowed_views(possible_names)
    if not possible_names:
        logger.warning("No enabled views configured for products queries")
        return []
    
    for view_name in possible_names:
        try:
            filters = {}
            if search_term:
                # Try to search in name or description
                filters = {'name': search_term}  # This might need adjustment based on actual schema
                # Note: For LIKE queries, you'd need to modify the query building
            
            results = await query_view(view_name, limit=limit, filters=filters if not search_term else None)
            if results:
                logger.info(f"Found products in view '{view_name}'")
                return results
        except Exception as e:
            logger.debug(f"View '{view_name}' not found or error: {e}")
            continue
    
    logger.warning("No products view found")
    return []


async def get_orders_by_phone(phone_number: str, limit: int = 10) -> List[Dict]:
    """
    Get orders for a specific phone number
    
    Args:
        phone_number: Customer phone number
        limit: Maximum number of orders
    
    Returns:
        List of orders
    """
    # Try common view/table names for orders
    possible_names = [
        'v_orders', 'view_orders', 'orders_view',
        'pedidos', 'v_pedidos',
        'orders', 'order'
    ]

    possible_names = _filter_allowed_views(possible_names)
    if not possible_names:
        logger.warning("No enabled views configured for order queries")
        return []
    
    for view_name in possible_names:
        try:
            filters = {'phone': phone_number}
            results = await query_view(view_name, limit=limit, filters=filters)
            if results:
                logger.info(f"Found orders in view '{view_name}' for {phone_number}")
                return results
        except Exception as e:
            logger.debug(f"View '{view_name}' not found or error: {e}")
            continue
    
    logger.warning(f"No orders found for phone {phone_number}")
    return []


async def get_order_by_id(order_id: str) -> Optional[Dict]:
    """
    Get a specific order by ID
    
    Args:
        order_id: Order ID
    
    Returns:
        Order dictionary or None
    """
    possible_names = [
        'v_orders', 'view_orders', 'orders_view',
        'pedidos', 'v_pedidos',
        'orders', 'order'
    ]

    possible_names = _filter_allowed_views(possible_names)
    if not possible_names:
        logger.warning("No enabled views configured for order detail queries")
        return None
    
    for view_name in possible_names:
        try:
            filters = {'id': order_id}
            results = await query_view(view_name, limit=1, filters=filters)
            if results:
                return results[0]
        except Exception as e:
            logger.debug(f"View '{view_name}' not found or error: {e}")
            continue
    
    return None


async def get_stock_info(product_id: Optional[str] = None) -> List[Dict]:
    """
    Get stock information
    
    Args:
        product_id: Optional product ID to filter
    
    Returns:
        List of stock information
    """
    possible_names = [
        'v_stock', 'view_stock', 'stock_view',
        'inventario', 'v_inventario',
        'stock', 'inventory'
    ]

    possible_names = _filter_allowed_views(possible_names)
    if not possible_names:
        logger.warning("No enabled views configured for stock queries")
        return []
    
    for view_name in possible_names:
        try:
            filters = {}
            if product_id:
                filters = {'product_id': product_id}
            
            results = await query_view(view_name, limit=100, filters=filters if product_id else None)
            if results:
                logger.info(f"Found stock info in view '{view_name}'")
                return results
        except Exception as e:
            logger.debug(f"View '{view_name}' not found or error: {e}")
            continue
    
    logger.warning("No stock view found")
    return []


async def get_customer_info(phone_number: str) -> Optional[Dict]:
    """
    Get customer information
    
    Args:
        phone_number: Customer phone number
    
    Returns:
        Customer dictionary or None
    """
    possible_names = [
        'v_customers', 'view_customers', 'customers_view',
        'clientes', 'v_clientes',
        'customers', 'customer'
    ]

    possible_names = _filter_allowed_views(possible_names)
    if not possible_names:
        logger.warning("No enabled views configured for customer queries")
        return None
    
    for view_name in possible_names:
        try:
            filters = {'phone': phone_number}
            results = await query_view(view_name, limit=1, filters=filters)
            if results:
                return results[0]
        except Exception as e:
            logger.debug(f"View '{view_name}' not found or error: {e}")
            continue
    
    return None


async def list_available_views() -> List[str]:
    """
    List all available views in the database
    
    Returns:
        List of view names
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # PostgreSQL query to get all views
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.views 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                results = cur.fetchall()
                views = [row[0] for row in results]
                if ENABLED_VIEWS:
                    views = [view for view in views if _is_view_allowed(view)]
                logger.info(f"Found {len(views)} views in database")
                return views
    except Exception as e:
        logger.error(f"Error listing views: {e}")
        return []


async def get_custom_view_data(view_name: str, filters: Optional[Dict] = None, limit: int = 50) -> List[Dict]:
    """
    Query a custom view with optional filters
    
    Args:
        view_name: Name of the view
        filters: Optional filters
        limit: Maximum rows
    
    Returns:
        List of dictionaries
    """
    return await query_view(view_name, limit=limit, filters=filters)


async def get_monthly_sales_costs(limit: int = 100) -> List[Dict]:
    """
    Build monthly sales/cost metrics. Prefers `v_sales_dashboard_planilla`
    (mismatching columns handled igual que `send_daily_sales_summary.py`), and falls
    back to `v_monthly_sales_costs` if available.
    """
    dashboard_view = 'v_sales_dashboard_planilla'
    if _is_view_allowed(dashboard_view):
        aggregated = await _aggregate_sales_dashboard(dashboard_view, limit)
        if aggregated:
            return aggregated
    
    legacy_view = 'v_monthly_sales_costs'

    if not _is_view_allowed(legacy_view):
        logger.warning("View '%s' is not enabled for monthly sales and costs queries", legacy_view)
        return []

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                query = f'''
                    SELECT month, revenue, costs, profit, margin_pct 
                    FROM "{legacy_view}"
                    ORDER BY month DESC
                    LIMIT %s
                '''
                cur.execute(query, (limit,))
                results = cur.fetchall()
                
                columns = [desc[0] for desc in cur.description] if cur.description else []
                
                rows = []
                for row in results:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        if hasattr(value, 'isoformat'):
                            row_dict[col] = value.isoformat()
                        else:
                            row_dict[col] = value
                    rows.append(row_dict)
                
                if rows:
                    logger.info(f"Found monthly sales and costs in view '{legacy_view}': {len(rows)} records")
                    return rows
                else:
                    logger.warning(f"View '{legacy_view}' exists but has no data")
                    return []
    except Exception as e:
        logger.error(f"Error querying view '{legacy_view}': {e}")
        return []


async def _aggregate_sales_dashboard(view_name: str, limit: int) -> List[Dict]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    SELECT *
                    FROM "{view_name}"
                    ORDER BY 1 DESC
                    LIMIT %s
                    ''',
                    (5000,),
                )
                rows = cur.fetchall()
                if not rows or not cur.description:
                    logger.warning("View '%s' exists but returned no rows for aggregation", view_name)
                    return []
                
                columns = [desc[0].lower() for desc in cur.description]
                monthly_data: Dict[date, Dict[str, Any]] = {}
                
                for record in rows:
                    row_dict = {columns[idx]: record[idx] for idx in range(len(columns))}
                    
                    day_value = _get_first_value(row_dict, ["dia", "fecha", "day"])
                    day = _parse_date_value(day_value)
                    if not day:
                        continue
                    month_key = day.replace(day=1)
                    
                    bucket = monthly_data.setdefault(
                        month_key,
                        {
                            "month": month_key.isoformat(),
                            "revenue": 0.0,
                            "product_cost": 0.0,
                            "shipping_cost": 0.0,
                            "orders": set(),
                        },
                    )
                    
                    revenue = float(
                        _get_first_value(
                            row_dict,
                            ["precio_venta", "revenue_bruto", "revenue", "precio_total", "precio"],
                            0.0,
                        )
                        or 0.0
                    )
                    shipping = float(
                        _get_first_value(
                            row_dict,
                            ["costo_envio", "shipping_cost", "envio_total"],
                            0.0,
                        )
                        or 0.0
                    )
                    unit_cost = float(
                        _get_first_value(
                            row_dict,
                            ["costo_unitario", "unit_cost", "costo", "costo_producto"],
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
                    
                    bucket["revenue"] += revenue
                    bucket["product_cost"] += unit_cost
                    bucket["shipping_cost"] += shipping
                    if order_id is not None:
                        text_id = str(order_id).strip()
                        if text_id:
                            bucket["orders"].add(text_id)
                
                summaries = []
                for month_key, bucket in monthly_data.items():
                    revenue = bucket["revenue"]
                    costs = bucket["product_cost"] + bucket["shipping_cost"]
                    profit = revenue - costs
                    margin_pct = (profit / revenue * 100) if revenue else None
                    
                    summaries.append({
                        "month": bucket["month"],
                        "revenue": revenue,
                        "costs": costs,
                        "profit": profit,
                        "margin_pct": margin_pct,
                        "orders": len(bucket["orders"]),
                    })
                
                summaries.sort(key=lambda item: item["month"], reverse=True)
                return summaries[:limit]
    except Exception as exc:
        logger.error("Error aggregating '%s': %s", view_name, exc)
    return []


async def get_sales_report(limit: int = 100) -> List[Dict]:
    """
    Get sales report data for analytics
    
    Args:
        limit: Maximum number of records
    
    Returns:
        List of sales records
    """
    # First try the specific monthly sales costs view
    monthly_data = await get_monthly_sales_costs(limit=limit)
    if monthly_data:
        return monthly_data
    
    # Then try other common view names
    possible_names = [
        'v_sales_report', 'view_sales_report', 'sales_report_view',
        'v_ventas', 'view_ventas', 'ventas_view',
        'v_sales', 'view_sales', 'sales_view',
        'v_revenue', 'view_revenue', 'revenue_view',
        'v_facturacion', 'facturacion_view'
    ]

    possible_names = _filter_allowed_views(possible_names)
    if not possible_names:
        logger.warning("No enabled views configured for sales reports")
        return []
    
    for view_name in possible_names:
        try:
            results = await query_view(view_name, limit=limit)
            if results:
                logger.info(f"Found sales report in view '{view_name}'")
                return results
        except Exception as e:
            logger.debug(f"View '{view_name}' not found or error: {e}")
            continue
    
    logger.warning("No sales report view found")
    return []


async def get_marketing_report(limit: int = 100) -> List[Dict]:
    """
    Get marketing and advertising spend/revenue data
    
    Args:
        limit: Maximum number of records
    
    Returns:
        List of marketing records
    """
    possible_names = [
        'v_marketing_performance_analysis',
        'v_marketing_report', 'view_marketing_report', 'marketing_report_view',
        'v_marketing', 'view_marketing', 'marketing_view',
        'v_ads', 'view_ads', 'ads_view',
        'v_publicidad', 'view_publicidad', 'publicidad_view',
        'v_campaigns', 'view_campaigns', 'campaigns_view',
        'v_campanas', 'view_campanas', 'campanas_view'
    ]

    possible_names = _filter_allowed_views(possible_names)
    if not possible_names:
        logger.warning("No enabled views configured for marketing reports")
        return []
    
    for view_name in possible_names:
        try:
            results = await query_view(view_name, limit=limit)
            if results:
                logger.info(f"Found marketing report in view '{view_name}'")
                return results
        except Exception as e:
            logger.debug(f"View '{view_name}' not found or error: {e}")
            continue
    
    logger.warning("No marketing report view found")
    return []


async def get_top_products(limit: int = 20) -> List[Dict]:
    """
    Get top selling products analytics
    
    Args:
        limit: Maximum number of products
    
    Returns:
        List of top products with sales data
    """
    possible_names = [
        'v_top_products', 'view_top_products', 'top_products_view',
        'v_productos_mas_vendidos', 'view_productos_mas_vendidos',
        'v_best_sellers', 'view_best_sellers', 'best_sellers_view',
        'v_product_sales', 'view_product_sales', 'product_sales_view'
    ]

    possible_names = _filter_allowed_views(possible_names)
    if not possible_names:
        logger.warning("No enabled views configured for top products analytics")
        return []
    
    for view_name in possible_names:
        try:
            results = await query_view(view_name, limit=limit)
            if results:
                logger.info(f"Found top products in view '{view_name}'")
                return results
        except Exception as e:
            logger.debug(f"View '{view_name}' not found or error: {e}")
            continue
    
    logger.warning("No top products view found")
    return []


async def get_financial_report(limit: int = 100) -> List[Dict]:
    """
    Get financial report (income, expenses, margins)
    
    Args:
        limit: Maximum number of records
    
    Returns:
        List of financial records
    """
    possible_names = [
        'v_financial_report', 'view_financial_report', 'financial_report_view',
        'v_financiero', 'view_financiero', 'financiero_view',
        'v_ingresos_gastos', 'view_ingresos_gastos', 'ingresos_gastos_view',
        'v_expenses', 'view_expenses', 'expenses_view',
        'v_gastos', 'view_gastos', 'gastos_view'
    ]

    possible_names = _filter_allowed_views(possible_names)
    if not possible_names:
        logger.warning("No enabled views configured for financial reports")
        return []
    
    for view_name in possible_names:
        try:
            results = await query_view(view_name, limit=limit)
            if results:
                logger.info(f"Found financial report in view '{view_name}'")
                return results
        except Exception as e:
            logger.debug(f"View '{view_name}' not found or error: {e}")
            continue
    
    logger.warning("No financial report view found")
    return []


async def get_general_analytics(limit: int = 100) -> List[Dict]:
    """
    Get general analytics/dashboard data
    
    Args:
        limit: Maximum number of records
    
    Returns:
        List of analytics records
    """
    possible_names = [
        'v_analytics', 'view_analytics', 'analytics_view',
        'v_dashboard', 'view_dashboard', 'dashboard_view',
        'v_metricas', 'view_metricas', 'metricas_view',
        'v_estadisticas', 'view_estadisticas', 'estadisticas_view',
        'v_kpis', 'view_kpis', 'kpis_view'
    ]

    possible_names = _filter_allowed_views(possible_names)
    if not possible_names:
        logger.warning("No enabled views configured for general analytics")
        return []
    
    for view_name in possible_names:
        try:
            results = await query_view(view_name, limit=limit)
            if results:
                logger.info(f"Found analytics in view '{view_name}'")
                return results
        except Exception as e:
            logger.debug(f"View '{view_name}' not found or error: {e}")
            continue
    
    logger.warning("No analytics view found")
    return []

