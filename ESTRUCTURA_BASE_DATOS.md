# 📊 Estructura de Base de Datos - Marketing y Shopify

## 📑 Índice
1. [Tablas Base](#tablas-base)
2. [Vistas de Análisis](#vistas-de-análisis)
3. [Relaciones y Cruces](#relaciones-y-cruces)
4. [Consultas Útiles](#consultas-útiles)

---

## 🗂️ Tablas Base

### 1. **`order_summary`** - Órdenes de Shopify

Tabla principal que contiene todas las órdenes/ventas de Shopify.

#### Columnas Principales:
| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | SERIAL | ID único de la orden |
| `order_date` | DATE/TIMESTAMP | **Fecha de la orden** (por día) |
| `order_number` | VARCHAR | Número de orden de Shopify |
| `customer_phone` | VARCHAR | Teléfono del cliente |
| `customer_name` | VARCHAR | Nombre del cliente |
| `total_revenue` | DECIMAL | **Ingreso total de la orden** (precio de venta) |
| `product_cost` | DECIMAL | **Costo del producto** vendido |
| `status` | VARCHAR | Estado de la orden (completed, pending, etc.) |
| `product_name` | VARCHAR | **Nombre del producto comprado** |
| `quantity` | INTEGER | Cantidad de productos |

#### Ejemplo de Consulta:
```sql
-- Obtener ventas diarias con productos
SELECT 
    order_date::DATE AS fecha,
    product_name AS producto_comprado,
    product_cost AS costo_producto,
    total_revenue AS precio_venta,
    quantity AS cantidad
FROM order_summary
WHERE order_date >= '2024-01-01'
ORDER BY order_date DESC;
```

---

### 2. **`ad_performance`** - Rendimiento de Anuncios (Marketing)

Tabla que contiene el rendimiento diario de los anuncios de Facebook/Meta Ads.

#### Columnas Principales:
| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | SERIAL | ID único del registro |
| `event_date` | DATE | **Fecha del evento** (por día) |
| `campaign_id` | VARCHAR | ID de la campaña |
| `campaign_name` | VARCHAR | **Nombre de la campaña** |
| `adset_id` | VARCHAR | ID del conjunto de anuncios |
| `adset_name` | VARCHAR | **Nombre del conjunto de anuncios** |
| `ad_id` | VARCHAR | ID del anuncio |
| `ad_name` | VARCHAR | **Nombre del anuncio** |
| `spend` | DECIMAL | **Monto gastado** (inversión publicitaria) |
| `revenue` | DECIMAL | Ingresos atribuidos al anuncio |
| `conversions` | INTEGER | **Número de conversiones** (ventas) |
| `clicks` | INTEGER | Número de clics |
| `impressions` | INTEGER | Número de impresiones |

#### Cálculos Derivados:
- **ROAS** (Return on Ad Spend) = `revenue / spend`
- **CPC** (Costo Por Clic) = `spend / clicks`
- **CPM** (Costo Por Mil Impresiones) = `(spend / impressions) * 1000`
- **CVR** (Conversion Rate) = `(conversions / clicks) * 100`

#### Ejemplo de Consulta:
```sql
-- Obtener datos de marketing diarios
SELECT 
    event_date AS fecha,
    campaign_name AS campaña,
    adset_name AS conjunto_anuncios,
    ad_name AS anuncio,
    spend AS monto_gastado,
    clicks AS clics,
    conversions AS conversiones,
    CASE 
        WHEN clicks > 0 THEN spend / clicks 
        ELSE NULL 
    END AS costo_por_clic,
    CASE 
        WHEN spend > 0 THEN revenue / spend 
        ELSE NULL 
    END AS roas
FROM ad_performance
WHERE event_date >= '2024-01-01'
ORDER BY event_date DESC, spend DESC;
```

---

## 📈 Vistas de Análisis

Las vistas son consultas SQL guardadas que agrupan y calculan métricas automáticamente.

### 3. **`v_marketing_performance_analysis`** - Vista de Marketing

Vista que agrega datos de marketing por día, campaña, conjunto y anuncio.

#### Definición:
```sql
CREATE OR REPLACE VIEW public.v_marketing_performance_analysis AS
SELECT
    date_trunc('day', ap.event_date) AS report_date,
    ap.campaign_id,
    ap.campaign_name,
    ap.adset_id,
    ap.adset_name,
    ap.ad_id,
    ap.ad_name,
    SUM(ap.spend) AS spend,
    SUM(ap.revenue) AS revenue,
    SUM(ap.conversions) AS conversions,
    SUM(ap.clicks) AS clicks,
    CASE
        WHEN SUM(ap.spend) > 0 THEN SUM(ap.revenue) / NULLIF(SUM(ap.spend), 0)
        ELSE NULL
    END AS roas,
    CASE
        WHEN SUM(ap.clicks) > 0 THEN SUM(ap.spend) / NULLIF(SUM(ap.clicks), 0)
        ELSE NULL
    END AS cpc,
    SUM(ap.impressions) AS impressions
FROM public.ad_performance AS ap
GROUP BY
    report_date,
    ap.campaign_id,
    ap.campaign_name,
    ap.adset_id,
    ap.adset_name,
    ap.ad_id,
    ap.ad_name
ORDER BY
    report_date DESC,
    ap.campaign_name,
    ap.adset_name,
    ap.ad_name;
```

#### Columnas:
| Columna | Descripción |
|---------|-------------|
| `report_date` | **Fecha del reporte** (día) |
| `campaign_name` | **Nombre de la campaña** |
| `adset_name` | **Nombre del conjunto de anuncios** |
| `ad_name` | **Nombre del anuncio** |
| `spend` | **Gasto total** del día |
| `revenue` | Ingresos atribuidos |
| `conversions` | **Total de conversiones** |
| `clicks` | Total de clics |
| `roas` | **ROAS calculado** (revenue/spend) |
| `cpc` | **CPC calculado** (spend/clicks) |
| `impressions` | Total de impresiones |

#### Ejemplo de Consulta:
```sql
-- Obtener datos de marketing con métricas calculadas
SELECT 
    report_date AS fecha,
    campaign_name AS campaña,
    adset_name AS conjunto_anuncios,
    ad_name AS anuncio,
    spend AS monto_gastado,
    cpc AS costo_por_clic,
    roas,
    conversions AS conversiones
FROM v_marketing_performance_analysis
WHERE report_date >= '2024-01-01'
ORDER BY report_date DESC, spend DESC;
```

---

### 4. **`v_sales_costs_daily`** - Vista Diaria de Ventas y Costos

Vista que combina ventas de Shopify con costos de marketing por día.

#### Columnas Esperadas:
| Columna | Descripción |
|---------|-------------|
| `day` | **Fecha** (día) |
| `orders` | Número de órdenes |
| `revenue` | **Ingresos totales** de ventas |
| `sales_cost` | **Costo de productos** vendidos |
| `marketing_cost` | **Gasto en marketing** del día |
| `profit` | Utilidad neta (revenue - sales_cost - marketing_cost) |
| `margin_pct` | Margen de ganancia (%) |

#### Ejemplo de Consulta:
```sql
SELECT 
    day AS fecha,
    orders AS pedidos,
    revenue AS ingresos,
    sales_cost AS costo_productos,
    marketing_cost AS gasto_marketing,
    profit AS utilidad,
    margin_pct AS margen_porcentaje
FROM v_sales_costs_daily
WHERE day >= '2024-01-01'
ORDER BY day DESC;
```

---

### 5. **`v_monthly_sales_costs`** - Vista Mensual de Ventas y Costos

Vista que agrega datos por mes, combinando ventas y marketing.

#### Definición:
```sql
CREATE OR REPLACE VIEW public.v_monthly_sales_costs AS
WITH sales AS (
    SELECT
        date_trunc('month', o.order_date)::date AS month,
        SUM(o.total_revenue) AS revenue,
        SUM(o.product_cost) AS product_cost
    FROM public.order_summary o
    GROUP BY 1
),
marketing AS (
    SELECT
        date_trunc('month', v.report_date)::date AS month,
        SUM(v.spend) AS marketing_cost
    FROM public.v_marketing_performance_analysis v
    GROUP BY 1
)
SELECT
    s.month,
    s.revenue,
    s.product_cost,
    COALESCE(m.marketing_cost, 0) AS marketing_cost,
    s.product_cost + COALESCE(m.marketing_cost, 0) AS costs,
    s.revenue - (s.product_cost + COALESCE(m.marketing_cost, 0)) AS profit,
    CASE
        WHEN s.revenue > 0
            THEN (s.revenue - (s.product_cost + COALESCE(m.marketing_cost, 0))) / s.revenue * 100
        ELSE NULL
    END AS margin_pct
FROM sales s
LEFT JOIN marketing m USING (month)
ORDER BY s.month DESC;
```

#### Columnas:
| Columna | Descripción |
|---------|-------------|
| `month` | Mes (YYYY-MM-01) |
| `revenue` | Ingresos totales del mes |
| `product_cost` | Costo de productos del mes |
| `marketing_cost` | Gasto en marketing del mes |
| `costs` | Costos totales (productos + marketing) |
| `profit` | Utilidad neta |
| `margin_pct` | Margen de ganancia (%) |

---

## 🔗 Relaciones y Cruces

### Diagrama de Relaciones

```
┌─────────────────────┐
│  order_summary      │
│  (Shopify Orders)   │
├─────────────────────┤
│ • order_date        │──┐
│ • product_name      │  │
│ • product_cost      │  │
│ • total_revenue     │  │
│ • customer info     │  │
└─────────────────────┘  │
                         │  Agrupación por fecha
                         │
                         ├──────────────────────────────┐
                         │                              │
                         ▼                              ▼
        ┌─────────────────────────┐    ┌──────────────────────────┐
        │ v_sales_costs_daily     │◄───┤ v_monthly_sales_costs    │
        │ (Vista Diaria)          │    │ (Vista Mensual)          │
        ├─────────────────────────┤    ├──────────────────────────┤
        │ • day                   │    │ • month                  │
        │ • revenue               │    │ • revenue                │
        │ • sales_cost            │    │ • product_cost           │
        │ • marketing_cost ◄──────┼────┤ • marketing_cost         │
        │ • profit                │    │ • profit                 │
        └─────────────────────────┘    │ • margin_pct             │
                         ▲              └──────────────────────────┘
                         │                              ▲
                         │  Cruce por fecha             │
                         │                              │
┌─────────────────────┐ │              ┌───────────────┴──────────┐
│  ad_performance     │ │              │ v_marketing_performance_ │
│  (Marketing/Ads)    │ │              │ analysis (Vista)         │
├─────────────────────┤ │              ├──────────────────────────┤
│ • event_date        │─┘              │ • report_date            │
│ • campaign_name     │────────────────┤ • campaign_name          │
│ • adset_name        │   Agrupación   │ • adset_name             │
│ • ad_name           │   por día      │ • ad_name                │
│ • spend             │                │ • spend (SUM)            │
│ • conversions       │                │ • conversions (SUM)      │
│ • clicks            │                │ • clicks (SUM)           │
│ • revenue           │                │ • roas (calculado)       │
└─────────────────────┘                │ • cpc (calculado)        │
                                       └──────────────────────────┘
```

### Cómo se Relacionan

1. **Cruce por Fecha**: Las tablas `order_summary` y `ad_performance` se relacionan a través de la fecha:
   - `order_summary.order_date` ↔ `ad_performance.event_date`
   
2. **Vista Integrada**: `v_sales_costs_daily` y `v_monthly_sales_costs` combinan ambas fuentes:
   ```sql
   -- Ventas del día
   FROM order_summary
   WHERE order_date = '2024-01-15'
   
   -- + Marketing del día
   FROM v_marketing_performance_analysis
   WHERE report_date = '2024-01-15'
   ```

3. **No hay relación directa** entre órdenes individuales y anuncios específicos (sin UTM tracking), pero se agrupan por período de tiempo.

---

## 🔍 Consultas Útiles

### 1. Datos Completos de Ventas Shopify (Por Día)

```sql
-- Información completa de ventas por día
SELECT 
    order_date::DATE AS fecha,
    product_name AS producto_comprado,
    product_cost AS costo_producto,
    total_revenue AS precio_venta,
    quantity AS cantidad,
    customer_name AS cliente,
    order_number AS numero_orden
FROM order_summary
WHERE order_date >= '2024-01-01'
ORDER BY order_date DESC;
```

### 2. Datos Completos de Marketing (Por Día)

```sql
-- Información completa de marketing por día
SELECT 
    report_date AS fecha,
    campaign_name AS campaña,
    adset_name AS conjunto_anuncios,
    ad_name AS anuncio,
    spend AS monto_gastado,
    cpc AS costo_por_clic,
    roas,
    conversions AS conversiones,
    clicks AS clics,
    impressions AS impresiones
FROM v_marketing_performance_analysis
WHERE report_date >= '2024-01-01'
ORDER BY report_date DESC, spend DESC;
```

### 3. Resumen Diario Combinado (Ventas + Marketing)

```sql
-- Vista completa del día: ventas y marketing
SELECT 
    day AS fecha,
    orders AS pedidos,
    revenue AS ingresos,
    sales_cost AS costo_productos,
    marketing_cost AS gasto_marketing,
    revenue - (sales_cost + marketing_cost) AS utilidad_neta,
    CASE 
        WHEN revenue > 0 
        THEN ((revenue - (sales_cost + marketing_cost)) / revenue * 100)::NUMERIC(10,2)
        ELSE 0 
    END AS margen_porcentaje
FROM v_sales_costs_daily
WHERE day >= '2024-01-01'
ORDER BY day DESC;
```

### 4. Top Productos por Período

```sql
-- Productos más vendidos en un período
SELECT 
    product_name AS producto,
    COUNT(*) AS numero_ordenes,
    SUM(quantity) AS unidades_vendidas,
    SUM(total_revenue) AS ingresos_totales,
    SUM(product_cost) AS costo_total,
    SUM(total_revenue - product_cost) AS ganancia_bruta,
    AVG(total_revenue) AS precio_promedio
FROM order_summary
WHERE order_date >= '2024-01-01' AND order_date < '2024-02-01'
GROUP BY product_name
ORDER BY ingresos_totales DESC
LIMIT 10;
```

### 5. Top Campañas por ROI

```sql
-- Mejores campañas por retorno de inversión
SELECT 
    campaign_name AS campaña,
    SUM(spend) AS inversion_total,
    SUM(revenue) AS ingresos_atribuidos,
    SUM(conversions) AS conversiones_totales,
    SUM(clicks) AS clics_totales,
    CASE 
        WHEN SUM(spend) > 0 
        THEN (SUM(revenue) / SUM(spend))::NUMERIC(10,2)
        ELSE 0 
    END AS roas,
    CASE 
        WHEN SUM(clicks) > 0 
        THEN (SUM(spend) / SUM(clicks))::NUMERIC(10,2)
        ELSE 0 
    END AS cpc_promedio
FROM v_marketing_performance_analysis
WHERE report_date >= '2024-01-01' AND report_date < '2024-02-01'
GROUP BY campaign_name
ORDER BY roas DESC
LIMIT 10;
```

### 6. Análisis Diario Detallado con Productos y Marketing

```sql
-- Cruce completo: ventas detalladas + gasto marketing del día
WITH ventas_dia AS (
    SELECT 
        order_date::DATE AS fecha,
        COUNT(*) AS total_ordenes,
        STRING_AGG(DISTINCT product_name, ', ') AS productos_vendidos,
        SUM(total_revenue) AS ingresos,
        SUM(product_cost) AS costo_productos
    FROM order_summary
    GROUP BY order_date::DATE
),
marketing_dia AS (
    SELECT 
        report_date AS fecha,
        SUM(spend) AS gasto_marketing,
        SUM(conversions) AS conversiones,
        STRING_AGG(DISTINCT campaign_name, ', ') AS campañas_activas
    FROM v_marketing_performance_analysis
    GROUP BY report_date
)
SELECT 
    COALESCE(v.fecha, m.fecha) AS fecha,
    v.total_ordenes AS pedidos,
    v.productos_vendidos,
    v.ingresos,
    v.costo_productos,
    m.gasto_marketing,
    m.conversiones,
    m.campañas_activas,
    (v.ingresos - v.costo_productos - COALESCE(m.gasto_marketing, 0)) AS utilidad_neta
FROM ventas_dia v
FULL OUTER JOIN marketing_dia m ON v.fecha = m.fecha
WHERE COALESCE(v.fecha, m.fecha) >= '2024-01-01'
ORDER BY fecha DESC;
```

### 7. Performance por Conjunto de Anuncios

```sql
-- Análisis detallado por adset (conjunto de anuncios)
SELECT 
    campaign_name AS campaña,
    adset_name AS conjunto_anuncios,
    SUM(spend) AS gasto,
    SUM(conversions) AS conversiones,
    SUM(clicks) AS clics,
    CASE 
        WHEN SUM(conversions) > 0 
        THEN (SUM(spend) / SUM(conversions))::NUMERIC(10,2)
        ELSE NULL 
    END AS costo_por_conversion,
    CASE 
        WHEN SUM(spend) > 0 
        THEN (SUM(revenue) / SUM(spend))::NUMERIC(10,2)
        ELSE 0 
    END AS roas,
    CASE 
        WHEN SUM(clicks) > 0 
        THEN (SUM(spend) / SUM(clicks))::NUMERIC(10,2)
        ELSE 0 
    END AS cpc
FROM v_marketing_performance_analysis
WHERE report_date >= '2024-01-01'
GROUP BY campaign_name, adset_name
ORDER BY gasto DESC;
```

### 8. Análisis por Anuncio Individual

```sql
-- Performance de cada anuncio individual
SELECT 
    campaign_name AS campaña,
    adset_name AS conjunto,
    ad_name AS anuncio,
    SUM(spend) AS gasto,
    SUM(conversions) AS conversiones,
    SUM(clicks) AS clics,
    SUM(impressions) AS impresiones,
    CASE 
        WHEN SUM(spend) > 0 
        THEN (SUM(revenue) / SUM(spend))::NUMERIC(10,2)
        ELSE 0 
    END AS roas,
    CASE 
        WHEN SUM(clicks) > 0 
        THEN (SUM(spend) / SUM(clicks))::NUMERIC(10,2)
        ELSE 0 
    END AS cpc,
    CASE 
        WHEN SUM(clicks) > 0 
        THEN (SUM(conversions)::FLOAT / SUM(clicks) * 100)::NUMERIC(10,2)
        ELSE 0 
    END AS tasa_conversion
FROM v_marketing_performance_analysis
WHERE report_date >= '2024-01-01'
GROUP BY campaign_name, adset_name, ad_name
HAVING SUM(spend) > 0
ORDER BY roas DESC;
```

---

## 📊 Resumen de Campos Clave

### Para Ventas Shopify:
✅ **Fecha**: `order_summary.order_date`  
✅ **Producto comprado**: `order_summary.product_name`  
✅ **Costo del producto**: `order_summary.product_cost`  
✅ Precio de venta: `order_summary.total_revenue`  
✅ Cantidad: `order_summary.quantity`

### Para Marketing (Ads):
✅ **Fecha**: `ad_performance.event_date` o `v_marketing_performance_analysis.report_date`  
✅ **Campaña**: `campaign_name`  
✅ **Conjunto de anuncios**: `adset_name`  
✅ **Anuncio**: `ad_name`  
✅ **Monto gastado**: `spend`  
✅ **Costo por clic**: `cpc` (calculado: spend/clicks)  
✅ **ROAS**: `roas` (calculado: revenue/spend)  
✅ **Conversiones**: `conversions`

---

## 🎯 Mejores Prácticas

1. **Usar Vistas en lugar de Tablas Base**: Las vistas ya tienen cálculos y agregaciones optimizadas.
   - ✅ Usa: `v_marketing_performance_analysis`
   - ❌ Evita: `ad_performance` directo (a menos que necesites datos sin agregar)

2. **Filtrar por Fechas**: Siempre limita tus consultas a rangos de fechas específicos para mejor performance.
   ```sql
   WHERE report_date >= '2024-01-01' AND report_date < '2024-02-01'
   ```

3. **Agrupar según Nivel de Detalle**:
   - **Diario**: Usar `date_trunc('day', ...)`
   - **Semanal**: Usar `date_trunc('week', ...)`
   - **Mensual**: Usar `date_trunc('month', ...)`

4. **Manejar Valores NULL**: Usar `COALESCE()` para evitar errores en cálculos:
   ```sql
   COALESCE(marketing_cost, 0)
   ```

5. **Verificar Divisiones por Zero**: Usar `NULLIF()` en divisiones:
   ```sql
   spend / NULLIF(clicks, 0)
   ```

---

## 🚀 Acceso desde Python

El código ya está configurado para acceder a estas vistas:

```python
# En send_daily_sales_summary.py
from app.db.connection import get_connection

# Consulta vista de ventas diarias
query = """
    SELECT *
    FROM public.v_sales_costs_daily
    WHERE day = %s
"""

# En send_marketing_summary.py
query = """
    SELECT *
    FROM public.v_marketing_performance
    WHERE metric_date >= %s AND metric_date < %s
"""
```

---

## 📞 Soporte

Si necesitas crear nuevas vistas o consultas personalizadas, revisa:
- `sql/update_v_marketing_performance_analysis.sql` - Ejemplo de vista de marketing
- `sql/update_v_monthly_sales_costs.sql` - Ejemplo de vista combinada
- `app/db/business_data.py` - Funciones de consulta en Python

---

**Documentación actualizada**: Noviembre 2024

