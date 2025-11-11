# 🚀 Cheat Sheet - Consultas SQL Rápidas

## 📋 Tablas y Vistas Principales

| Nombre | Tipo | Para qué sirve |
|--------|------|----------------|
| `order_summary` | **Tabla** | Órdenes de Shopify (ventas) |
| `ad_performance` | **Tabla** | Datos crudos de anuncios |
| `v_marketing_performance_analysis` | **Vista** | 👍 Marketing con métricas calculadas |
| `v_sales_costs_daily` | **Vista** | 👍 Ventas + Marketing por día |
| `v_monthly_sales_costs` | **Vista** | Resumen mensual |

---

## ⚡ Consultas Copy-Paste

### 🛒 Ventas Shopify

#### Ventas del día
```sql
SELECT 
    order_date::DATE AS fecha,
    product_name AS producto,
    product_cost AS costo,
    total_revenue AS precio_venta,
    quantity AS cantidad
FROM order_summary
WHERE order_date = '2024-01-15'
ORDER BY order_date DESC;
```

#### Ventas del mes
```sql
SELECT 
    order_date::DATE AS fecha,
    product_name AS producto,
    product_cost AS costo
FROM order_summary
WHERE order_date >= '2024-01-01' 
  AND order_date < '2024-02-01'
ORDER BY order_date DESC;
```

#### Top productos
```sql
SELECT 
    product_name AS producto,
    COUNT(*) AS num_ventas,
    SUM(quantity) AS unidades,
    SUM(total_revenue) AS ingresos,
    SUM(product_cost) AS costo_total
FROM order_summary
WHERE order_date >= '2024-01-01'
GROUP BY product_name
ORDER BY ingresos DESC
LIMIT 10;
```

---

### 📢 Marketing

#### Marketing del día
```sql
SELECT 
    report_date AS fecha,
    campaign_name AS campaña,
    adset_name AS conjunto,
    ad_name AS anuncio,
    spend AS gasto,
    cpc AS costo_por_clic,
    roas,
    conversions AS conversiones
FROM v_marketing_performance_analysis
WHERE report_date = '2024-01-15'
ORDER BY spend DESC;
```

#### Marketing del mes
```sql
SELECT 
    report_date AS fecha,
    campaign_name AS campaña,
    adset_name AS conjunto,
    ad_name AS anuncio,
    spend AS gasto,
    conversions AS conversiones
FROM v_marketing_performance_analysis
WHERE report_date >= '2024-01-01' 
  AND report_date < '2024-02-01'
ORDER BY report_date DESC, spend DESC;
```

#### Top campañas
```sql
SELECT 
    campaign_name AS campaña,
    SUM(spend) AS gasto_total,
    SUM(conversions) AS conversiones,
    ROUND(AVG(roas)::NUMERIC, 2) AS roas_promedio,
    ROUND(AVG(cpc)::NUMERIC, 2) AS cpc_promedio
FROM v_marketing_performance_analysis
WHERE report_date >= '2024-01-01'
GROUP BY campaign_name
ORDER BY gasto_total DESC;
```

#### Top conjuntos de anuncios
```sql
SELECT 
    campaign_name AS campaña,
    adset_name AS conjunto,
    SUM(spend) AS gasto,
    SUM(conversions) AS conversiones,
    ROUND(AVG(roas)::NUMERIC, 2) AS roas
FROM v_marketing_performance_analysis
WHERE report_date >= '2024-01-01'
GROUP BY campaign_name, adset_name
ORDER BY gasto DESC
LIMIT 20;
```

#### Top anuncios
```sql
SELECT 
    campaign_name AS campaña,
    ad_name AS anuncio,
    SUM(spend) AS gasto,
    SUM(conversions) AS conversiones,
    SUM(clicks) AS clics,
    ROUND(AVG(roas)::NUMERIC, 2) AS roas,
    ROUND(AVG(cpc)::NUMERIC, 2) AS cpc
FROM v_marketing_performance_analysis
WHERE report_date >= '2024-01-01'
GROUP BY campaign_name, ad_name
ORDER BY gasto DESC
LIMIT 20;
```

---

### 📊 Combinadas (Ventas + Marketing)

#### Resumen diario completo
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

#### Resumen mensual
```sql
SELECT 
    month AS mes,
    revenue AS ingresos,
    product_cost AS costo_productos,
    marketing_cost AS gasto_marketing,
    profit AS utilidad,
    margin_pct AS margen_porcentaje
FROM v_monthly_sales_costs
ORDER BY month DESC;
```

#### Análisis día específico
```sql
-- Ventas
SELECT 
    'VENTAS' AS tipo,
    COUNT(*) AS cantidad,
    SUM(total_revenue) AS total,
    STRING_AGG(DISTINCT product_name, ', ') AS detalle
FROM order_summary
WHERE order_date = '2024-01-15'

UNION ALL

-- Marketing
SELECT 
    'MARKETING' AS tipo,
    COUNT(*) AS cantidad,
    SUM(spend) AS total,
    STRING_AGG(DISTINCT campaign_name, ', ') AS detalle
FROM v_marketing_performance_analysis
WHERE report_date = '2024-01-15';
```

---

## 🎯 Campos Clave - Mapa Rápido

### Shopify → `order_summary`
```
✅ order_date        → FECHA
✅ product_name      → PRODUCTO COMPRADO
✅ product_cost      → COSTO DEL PRODUCTO
   total_revenue     → precio de venta
   quantity          → cantidad vendida
   customer_name     → nombre cliente
```

### Marketing → `v_marketing_performance_analysis`
```
✅ report_date       → FECHA
✅ campaign_name     → CAMPAÑA
✅ adset_name        → CONJUNTO DE ANUNCIOS
✅ ad_name           → ANUNCIO
✅ spend             → MONTO GASTADO
✅ cpc               → COSTO POR CLIC (calculado)
✅ roas              → ROAS (calculado)
✅ conversions       → CONVERSIONES
   clicks            → clics
   impressions       → impresiones
   revenue           → ingresos atribuidos
```

### Combinado → `v_sales_costs_daily`
```
✅ day               → FECHA
   orders            → número de pedidos
   revenue           → ingresos totales
   sales_cost        → costo productos
   marketing_cost    → gasto marketing
   profit            → utilidad neta
   margin_pct        → margen %
```

---

## 🔢 Fórmulas de Cálculo

| Métrica | Fórmula SQL | Vista que lo tiene |
|---------|-------------|-------------------|
| **ROAS** | `revenue / NULLIF(spend, 0)` | ✅ `v_marketing_performance_analysis` |
| **CPC** | `spend / NULLIF(clicks, 0)` | ✅ `v_marketing_performance_analysis` |
| **CPM** | `(spend / NULLIF(impressions, 0)) * 1000` | Debes calcular |
| **CVR** | `(conversions::FLOAT / NULLIF(clicks, 0)) * 100` | Debes calcular |
| **AOV** | `revenue / NULLIF(orders, 0)` | Debes calcular |
| **Margen** | `((revenue - costs) / NULLIF(revenue, 0)) * 100` | ✅ `v_sales_costs_daily` |
| **Utilidad** | `revenue - product_cost - marketing_cost` | ✅ `v_sales_costs_daily` |

---

## 📅 Filtros de Fecha Comunes

```sql
-- Hoy
WHERE date_column = CURRENT_DATE

-- Ayer
WHERE date_column = CURRENT_DATE - INTERVAL '1 day'

-- Últimos 7 días
WHERE date_column >= CURRENT_DATE - INTERVAL '7 days'

-- Últimos 30 días
WHERE date_column >= CURRENT_DATE - INTERVAL '30 days'

-- Este mes
WHERE date_column >= date_trunc('month', CURRENT_DATE)

-- Mes pasado
WHERE date_column >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
  AND date_column < date_trunc('month', CURRENT_DATE)

-- Rango específico
WHERE date_column >= '2024-01-01' 
  AND date_column < '2024-02-01'

-- Año actual
WHERE EXTRACT(YEAR FROM date_column) = EXTRACT(YEAR FROM CURRENT_DATE)
```

---

## 🛠️ Funciones Útiles

### Agrupar por Período
```sql
-- Por día
date_trunc('day', order_date)::DATE

-- Por semana
date_trunc('week', order_date)::DATE

-- Por mes
date_trunc('month', order_date)::DATE

-- Por año
date_trunc('year', order_date)::DATE
```

### Redondear Números
```sql
-- 2 decimales
ROUND(valor::NUMERIC, 2)

-- Sin decimales
ROUND(valor::NUMERIC, 0)

-- Formato moneda
TO_CHAR(valor, 'FM$999,999,999.00')
```

### Manejar NULLs
```sql
-- Valor por defecto si es NULL
COALESCE(valor, 0)

-- Evitar división por cero
valor / NULLIF(divisor, 0)

-- Reemplazar NULL con texto
COALESCE(texto, 'N/A')
```

### Concatenar Texto
```sql
-- Agrupar valores únicos
STRING_AGG(DISTINCT column, ', ')

-- Concatenar con ||
column1 || ' - ' || column2
```

---

## 🎨 Ejemplos de Reportes

### 1. Dashboard Diario
```sql
SELECT 
    day AS fecha,
    orders AS pedidos,
    revenue AS ingresos,
    marketing_cost AS gasto_ads,
    profit AS utilidad,
    ROUND(margin_pct, 2) AS margen_pct,
    CASE 
        WHEN profit > 0 THEN '✅ Positivo'
        ELSE '❌ Negativo'
    END AS estado
FROM v_sales_costs_daily
WHERE day >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY day DESC;
```

### 2. Análisis de Productos
```sql
SELECT 
    product_name AS producto,
    COUNT(*) AS ventas,
    SUM(quantity) AS unidades,
    ROUND(AVG(total_revenue)::NUMERIC, 0) AS precio_promedio,
    SUM(total_revenue) AS ingresos_totales,
    SUM(product_cost) AS costo_total,
    SUM(total_revenue - product_cost) AS ganancia_bruta,
    ROUND(
        (SUM(total_revenue - product_cost) / NULLIF(SUM(total_revenue), 0) * 100)::NUMERIC, 
        2
    ) AS margen_pct
FROM order_summary
WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY product_name
HAVING SUM(total_revenue) > 0
ORDER BY ingresos_totales DESC;
```

### 3. Performance de Campañas
```sql
SELECT 
    campaign_name AS campaña,
    COUNT(DISTINCT report_date) AS dias_activa,
    SUM(spend) AS inversion_total,
    SUM(conversions) AS conversiones_totales,
    SUM(clicks) AS clics_totales,
    ROUND(AVG(roas)::NUMERIC, 2) AS roas_promedio,
    ROUND(AVG(cpc)::NUMERIC, 2) AS cpc_promedio,
    ROUND((SUM(spend) / NULLIF(SUM(conversions), 0))::NUMERIC, 2) AS costo_por_conversion,
    CASE 
        WHEN AVG(roas) > 3 THEN '🟢 Excelente'
        WHEN AVG(roas) > 2 THEN '🟡 Bueno'
        ELSE '🔴 Revisar'
    END AS evaluacion
FROM v_marketing_performance_analysis
WHERE report_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY campaign_name
ORDER BY inversion_total DESC;
```

### 4. Comparación Mes a Mes
```sql
WITH mes_actual AS (
    SELECT 
        COUNT(*) AS ordenes,
        SUM(total_revenue) AS ingresos,
        SUM(product_cost) AS costos
    FROM order_summary
    WHERE order_date >= date_trunc('month', CURRENT_DATE)
),
mes_anterior AS (
    SELECT 
        COUNT(*) AS ordenes,
        SUM(total_revenue) AS ingresos,
        SUM(product_cost) AS costos
    FROM order_summary
    WHERE order_date >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
      AND order_date < date_trunc('month', CURRENT_DATE)
)
SELECT 
    'Mes Actual' AS periodo,
    ma.ordenes,
    ma.ingresos,
    ma.costos,
    ROUND(
        ((ma.ingresos::FLOAT - mp.ingresos) / NULLIF(mp.ingresos, 0) * 100)::NUMERIC, 
        2
    ) AS cambio_pct
FROM mes_actual ma, mes_anterior mp

UNION ALL

SELECT 
    'Mes Anterior' AS periodo,
    ordenes,
    ingresos,
    costos,
    0 AS cambio_pct
FROM mes_anterior;
```

---

## 💾 Exportar Resultados

### CSV
```sql
-- En psql:
\copy (SELECT * FROM v_sales_costs_daily WHERE day >= '2024-01-01') TO 'ventas.csv' CSV HEADER;
```

### JSON (desde Python)
```python
import psycopg2
import json

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT * FROM v_marketing_performance_analysis WHERE report_date >= '2024-01-01'")

columns = [desc[0] for desc in cur.description]
results = [dict(zip(columns, row)) for row in cur.fetchall()]

with open('marketing.json', 'w') as f:
    json.dump(results, f, default=str, indent=2)
```

---

## 🔗 Referencias Rápidas

- **Documentación completa**: `ESTRUCTURA_BASE_DATOS.md`
- **Guía rápida**: `GUIA_RAPIDA_DATOS.md`
- **Código Python**: `send_daily_sales_summary.py`, `send_marketing_summary.py`
- **Vistas SQL**: `sql/update_v_marketing_performance_analysis.sql`

---

## ⚠️ Troubleshooting

| Problema | Solución |
|----------|----------|
| "relation does not exist" | Verifica que la vista existe con `\dv` en psql |
| Valores NULL en resultados | Usa `COALESCE(column, 0)` |
| División por cero | Usa `NULLIF(divisor, 0)` |
| Fechas incorrectas | Convierte con `::DATE` o `date_trunc()` |
| Datos no actualizados | Verifica que las tablas base tienen datos |

---

**Última actualización**: Noviembre 2024  
**¿Dudas?** Consulta la documentación completa en `ESTRUCTURA_BASE_DATOS.md`

