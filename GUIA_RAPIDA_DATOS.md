# 🎯 Guía Rápida - Datos de Marketing y Shopify

## 📦 Datos que Necesitas

### ✅ Para Ventas Shopify
| Campo | Tabla/Vista | Columna |
|-------|-------------|---------|
| **Fecha (por día)** | `order_summary` | `order_date` |
| **Producto comprado** | `order_summary` | `product_name` |
| **Costo del producto** | `order_summary` | `product_cost` |

### ✅ Para Marketing
| Campo | Tabla/Vista | Columna |
|-------|-------------|---------|
| **Fecha (por día)** | `v_marketing_performance_analysis` | `report_date` |
| **Campaña** | `v_marketing_performance_analysis` | `campaign_name` |
| **Conjunto de anuncios** | `v_marketing_performance_analysis` | `adset_name` |
| **Anuncio** | `v_marketing_performance_analysis` | `ad_name` |
| **Monto gastado** | `v_marketing_performance_analysis` | `spend` |
| **Costo por clic** | `v_marketing_performance_analysis` | `cpc` (calculado) |
| **ROAS** | `v_marketing_performance_analysis` | `roas` (calculado) |
| **Conversiones** | `v_marketing_performance_analysis` | `conversions` |

---

## 🗺️ Estructura Simplificada

```
TABLAS BASE
===========

┌────────────────────────────────────────┐
│         order_summary                  │  ← Tabla principal de Shopify
├────────────────────────────────────────┤
│ • order_date        (FECHA)            │
│ • product_name      (PRODUCTO)         │
│ • product_cost      (COSTO)            │
│ • total_revenue     (precio venta)     │
│ • quantity          (cantidad)         │
│ • customer_name                        │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│        ad_performance                  │  ← Tabla principal de Marketing
├────────────────────────────────────────┤
│ • event_date        (FECHA)            │
│ • campaign_name     (CAMPAÑA)          │
│ • adset_name        (CONJUNTO)         │
│ • ad_name           (ANUNCIO)          │
│ • spend             (GASTO)            │
│ • conversions       (CONVERSIONES)     │
│ • clicks            (CLICS)            │
│ • revenue           (ingresos)         │
└────────────────────────────────────────┘

VISTAS (Pre-calculadas)
=======================

┌────────────────────────────────────────┐
│  v_marketing_performance_analysis      │  ← USAR ESTA para marketing
├────────────────────────────────────────┤
│ Agrega ad_performance por día          │
│ + calcula ROAS y CPC automáticamente   │
│                                        │
│ • report_date       (FECHA)            │
│ • campaign_name     (CAMPAÑA)          │
│ • adset_name        (CONJUNTO)         │
│ • ad_name           (ANUNCIO)          │
│ • spend             (GASTO) ← SUM      │
│ • conversions       (CONV.) ← SUM      │
│ • clicks            (CLICS) ← SUM      │
│ • roas              ← revenue/spend    │
│ • cpc               ← spend/clicks     │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│      v_sales_costs_daily               │  ← Ventas + Marketing por día
├────────────────────────────────────────┤
│ Combina order_summary + marketing      │
│                                        │
│ • day               (FECHA)            │
│ • orders            (pedidos)          │
│ • revenue           (ingresos)         │
│ • sales_cost        (costo productos)  │
│ • marketing_cost    (gasto marketing)  │
│ • profit            (utilidad)         │
│ • margin_pct        (margen %)         │
└────────────────────────────────────────┘
```

---

## 🔍 Consultas Rápidas

### 1️⃣ Obtener Ventas Shopify (lo que necesitas)

```sql
SELECT 
    order_date::DATE AS fecha,
    product_name AS producto_comprado,
    product_cost AS costo_producto
FROM order_summary
WHERE order_date >= '2024-01-01'
ORDER BY order_date DESC;
```

**Output ejemplo:**
```
fecha       | producto_comprado    | costo_producto
------------|---------------------|---------------
2024-01-15  | Crema Facial XYZ    | 15000
2024-01-15  | Serum Vitamina C    | 25000
2024-01-14  | Crema Facial XYZ    | 15000
```

---

### 2️⃣ Obtener Marketing (lo que necesitas)

```sql
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

**Output ejemplo:**
```
fecha       | campaña        | conjunto_anuncios | anuncio       | monto_gastado | costo_por_clic | roas | conversiones
------------|----------------|-------------------|---------------|---------------|----------------|------|-------------
2024-01-15  | Black Friday   | Mujeres 25-35     | Video Crema   | 50000         | 250            | 3.5  | 15
2024-01-15  | Black Friday   | Mujeres 25-35     | Imagen Serum  | 35000         | 180            | 4.2  | 12
2024-01-14  | Verano 2024    | Hombres 18-45     | Carousel      | 42000         | 320            | 2.8  | 8
```

---

## 🔄 Cómo se Cruzan las Tablas

### Por Fecha (Sin Relación Directa)

```sql
-- VENTAS de un día
SELECT * FROM order_summary
WHERE order_date = '2024-01-15'

-- MARKETING del mismo día
SELECT * FROM v_marketing_performance_analysis
WHERE report_date = '2024-01-15'
```

**⚠️ Importante**: No hay una relación directa entre una orden específica y un anuncio específico.  
Solo se pueden relacionar **agrupando por fecha**.

### Vista Pre-combinada

La vista `v_sales_costs_daily` ya hace este cruce automáticamente:

```sql
-- Resumen del día con ventas Y marketing
SELECT 
    day AS fecha,
    orders AS pedidos,
    revenue AS ingresos,
    sales_cost AS costo_productos,
    marketing_cost AS gasto_marketing
FROM v_sales_costs_daily
WHERE day = '2024-01-15';
```

**Output:**
```
fecha       | pedidos | ingresos | costo_productos | gasto_marketing
------------|---------|----------|-----------------|----------------
2024-01-15  | 27      | 450000   | 180000          | 85000
```

---

## 📊 Ejemplos Completos

### Ejemplo 1: Reporte de Ventas Semanal

```sql
SELECT 
    order_date::DATE AS fecha,
    COUNT(*) AS num_ordenes,
    STRING_AGG(DISTINCT product_name, ', ') AS productos,
    SUM(product_cost) AS costo_total,
    SUM(total_revenue) AS ingresos_totales,
    SUM(total_revenue - product_cost) AS ganancia_bruta
FROM order_summary
WHERE order_date >= '2024-01-08' AND order_date < '2024-01-15'
GROUP BY order_date::DATE
ORDER BY fecha DESC;
```

### Ejemplo 2: Performance de Campañas del Mes

```sql
SELECT 
    campaign_name AS campaña,
    SUM(spend) AS gasto_total,
    SUM(conversions) AS conversiones_totales,
    AVG(cpc) AS cpc_promedio,
    AVG(roas) AS roas_promedio
FROM v_marketing_performance_analysis
WHERE report_date >= '2024-01-01' AND report_date < '2024-02-01'
GROUP BY campaign_name
ORDER BY gasto_total DESC;
```

### Ejemplo 3: Análisis Diario Completo

```sql
-- Combina ventas + marketing en una sola consulta
WITH ventas AS (
    SELECT 
        order_date::DATE AS fecha,
        COUNT(*) AS pedidos,
        STRING_AGG(DISTINCT product_name, ', ') AS productos,
        SUM(product_cost) AS costo_productos,
        SUM(total_revenue) AS ingresos
    FROM order_summary
    WHERE order_date >= '2024-01-01'
    GROUP BY order_date::DATE
),
marketing AS (
    SELECT 
        report_date AS fecha,
        SUM(spend) AS gasto_marketing,
        SUM(conversions) AS conversiones,
        ROUND(AVG(roas)::NUMERIC, 2) AS roas_promedio,
        STRING_AGG(DISTINCT campaign_name, ', ') AS campañas
    FROM v_marketing_performance_analysis
    WHERE report_date >= '2024-01-01'
    GROUP BY report_date
)
SELECT 
    COALESCE(v.fecha, m.fecha) AS fecha,
    v.pedidos,
    v.productos,
    v.costo_productos,
    v.ingresos,
    m.gasto_marketing,
    m.conversiones,
    m.roas_promedio,
    m.campañas,
    (v.ingresos - v.costo_productos - COALESCE(m.gasto_marketing, 0)) AS utilidad_neta
FROM ventas v
FULL OUTER JOIN marketing m ON v.fecha = m.fecha
ORDER BY fecha DESC;
```

---

## 🎯 Campos Más Importantes

### 🛒 Shopify (Ventas)
```
✅ order_summary.order_date      → Fecha
✅ order_summary.product_name    → Producto comprado
✅ order_summary.product_cost    → Costo del producto
```

### 📢 Marketing (Ads)
```
✅ v_marketing_performance_analysis.report_date    → Fecha
✅ v_marketing_performance_analysis.campaign_name  → Campaña
✅ v_marketing_performance_analysis.adset_name     → Conjunto de anuncios
✅ v_marketing_performance_analysis.ad_name        → Anuncio
✅ v_marketing_performance_analysis.spend          → Monto gastado
✅ v_marketing_performance_analysis.cpc            → Costo por clic
✅ v_marketing_performance_analysis.roas           → ROAS
✅ v_marketing_performance_analysis.conversions    → Conversiones
```

---

## 💡 Tips

1. **Usa las vistas, no las tablas base**
   - ✅ `v_marketing_performance_analysis` (tiene ROAS y CPC ya calculados)
   - ❌ `ad_performance` (tienes que calcular todo manualmente)

2. **Filtra siempre por fecha**
   ```sql
   WHERE report_date >= '2024-01-01'
   ```

3. **Para ROAS y CPC ya calculados, usa la vista**
   - La vista `v_marketing_performance_analysis` ya tiene estos campos listos

4. **Para relacionar ventas y marketing**
   - Agrupa ambas por la misma fecha
   - O usa directamente `v_sales_costs_daily`

---

## 📁 Archivos Relacionados

- `send_daily_sales_summary.py` → Consulta ventas diarias
- `send_marketing_summary.py` → Consulta marketing diario
- `sql/update_v_marketing_performance_analysis.sql` → Definición de la vista de marketing
- `sql/update_v_sales_dashboard_planilla.sql` → Vista combinada mensual
- `app/db/business_data.py` → Funciones Python para consultar

---

**¿Necesitas algo más específico?** Revisa `ESTRUCTURA_BASE_DATOS.md` para documentación completa.

