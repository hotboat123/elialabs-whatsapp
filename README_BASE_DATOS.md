# 📚 Documentación de Base de Datos - Marketing y Shopify

## 🎯 Resumen Ejecutivo

Esta documentación explica la estructura completa de la base de datos, incluyendo:
- **Tablas de Shopify** (órdenes/ventas)
- **Tablas de Marketing** (rendimiento de anuncios)
- **Vistas agregadas** (métricas pre-calculadas)
- **Relaciones y cruces** entre ambas fuentes de datos

---

## 📖 Documentos Disponibles

### 1. 📘 [ESTRUCTURA_BASE_DATOS.md](./ESTRUCTURA_BASE_DATOS.md)
**Documentación técnica completa**

Incluye:
- ✅ Definición detallada de todas las tablas
- ✅ Estructura de las vistas SQL con código completo
- ✅ Diagramas de relaciones
- ✅ 8+ consultas de ejemplo complejas
- ✅ Mejores prácticas y consideraciones
- ✅ Acceso desde Python

**👉 Léelo cuando**: Necesites entender a fondo la arquitectura de datos.

---

### 2. 🚀 [GUIA_RAPIDA_DATOS.md](./GUIA_RAPIDA_DATOS.md)
**Guía visual rápida**

Incluye:
- ✅ Tabla rápida de campos específicos que necesitas
- ✅ Diagramas visuales simplificados
- ✅ 3 consultas esenciales (ventas, marketing, combinadas)
- ✅ Ejemplos de output esperado
- ✅ Tips y advertencias importantes

**👉 Léelo cuando**: Necesites encontrar rápidamente qué campo usar.

---

### 3. ⚡ [CHEATSHEET_CONSULTAS.md](./CHEATSHEET_CONSULTAS.md)
**Cheat sheet con consultas copy-paste**

Incluye:
- ✅ 15+ consultas SQL listas para usar
- ✅ Filtros de fecha comunes
- ✅ Fórmulas de cálculo (ROAS, CPC, etc.)
- ✅ Ejemplos de reportes completos
- ✅ Tips de exportación

**👉 Léelo cuando**: Necesites copiar y pegar una consulta rápidamente.

---

## 🗺️ Mapa Visual Rápido

```
┌─────────────────────────────────────────────────────────────┐
│                    TABLAS BASE                              │
└─────────────────────────────────────────────────────────────┘

    order_summary                   ad_performance
    (Shopify)                       (Marketing)
         │                                │
         │                                │
         ├── order_date                   ├── event_date
         ├── product_name                 ├── campaign_name
         ├── product_cost                 ├── adset_name
         ├── total_revenue                ├── ad_name
         └── quantity                     ├── spend
                                          ├── conversions
                                          ├── clicks
                                          └── revenue
              │                                │
              │                                │
              └────────┬───────────────────────┘
                       │
                       │ Agrupación por fecha
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    VISTAS (Pre-calculadas)                  │
└─────────────────────────────────────────────────────────────┘

    v_marketing_performance_analysis
    • report_date (fecha)
    • campaign_name, adset_name, ad_name
    • spend, conversions, clicks
    • roas (calculado), cpc (calculado)
              │
              │
              ├──────────────────┐
              │                  │
              ▼                  ▼
    v_sales_costs_daily    v_monthly_sales_costs
    • day (fecha)          • month
    • orders               • revenue
    • revenue              • product_cost
    • sales_cost           • marketing_cost
    • marketing_cost       • profit
    • profit               • margin_pct
    • margin_pct
```

---

## 🎯 Lo que Necesitas Específicamente

### ✅ Para Ventas Shopify

**Consulta básica:**
```sql
SELECT 
    order_date::DATE AS fecha,
    product_name AS producto_comprado,
    product_cost AS costo_producto
FROM order_summary
WHERE order_date >= '2024-01-01'
ORDER BY order_date DESC;
```

**Tabla**: `order_summary`  
**Campos clave**:
- `order_date` → **Fecha (por día)**
- `product_name` → **Producto comprado**
- `product_cost` → **Costo del producto**

---

### ✅ Para Marketing (Ads)

**Consulta básica:**
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
ORDER BY report_date DESC;
```

**Vista**: `v_marketing_performance_analysis` (👈 **Usa esta**)  
**Campos clave**:
- `report_date` → **Fecha (por día)**
- `campaign_name` → **Campaña**
- `adset_name` → **Conjunto de anuncios**
- `ad_name` → **Anuncio**
- `spend` → **Monto gastado**
- `cpc` → **Costo por clic** (ya calculado)
- `roas` → **ROAS** (ya calculado)
- `conversions` → **Conversiones**

---

## 🔗 Cómo se Relacionan

**Por Fecha** (No hay relación directa entre órdenes y anuncios):

```sql
-- Ventas del día
SELECT * FROM order_summary 
WHERE order_date = '2024-01-15'

-- Marketing del día
SELECT * FROM v_marketing_performance_analysis 
WHERE report_date = '2024-01-15'
```

**Vista pre-combinada**:
```sql
-- Resumen diario completo
SELECT * FROM v_sales_costs_daily
WHERE day = '2024-01-15'
```

---

## 📊 Fórmulas Clave

| Métrica | Fórmula | Disponible en |
|---------|---------|---------------|
| **ROAS** | revenue / spend | ✅ `v_marketing_performance_analysis` |
| **CPC** | spend / clicks | ✅ `v_marketing_performance_analysis` |
| **Margen %** | (revenue - costs) / revenue × 100 | ✅ `v_sales_costs_daily` |
| **Utilidad** | revenue - product_cost - marketing_cost | ✅ `v_sales_costs_daily` |
| **AOV** | revenue / orders | Debes calcular |
| **CVR** | conversions / clicks × 100 | Debes calcular |

---

## 🛠️ Acceso desde Python

Los scripts ya están listos para usar:

```python
# send_daily_sales_summary.py
# Consulta: v_sales_costs_daily
python send_daily_sales_summary.py --to "+56912345678" --date "2024-01-15"

# send_marketing_summary.py
# Consulta: v_marketing_performance
python send_marketing_summary.py --to "+56912345678" --date "2024-01-15"
```

**Funciones disponibles** en `app/db/business_data.py`:
```python
from app.db.business_data import (
    get_sales_report,           # Reportes de ventas
    get_marketing_report,       # Reportes de marketing
    get_monthly_sales_costs,    # Vista mensual
    query_view,                 # Consulta personalizada
)

# Ejemplo
data = await get_marketing_report(limit=100)
```

---

## 📁 Estructura de Archivos

```
proyecto/
├── README_BASE_DATOS.md              ← Este archivo (índice)
├── ESTRUCTURA_BASE_DATOS.md          ← Documentación completa
├── GUIA_RAPIDA_DATOS.md              ← Guía visual rápida
├── CHEATSHEET_CONSULTAS.md           ← Consultas copy-paste
├── sql/
│   ├── update_v_marketing_performance_analysis.sql
│   └── update_v_monthly_sales_costs.sql
├── app/
│   └── db/
│       ├── connection.py             ← Conexión a DB
│       ├── business_data.py          ← Funciones de consulta
│       └── queries.py                ← Otras consultas
├── send_daily_sales_summary.py       ← Script de ventas
└── send_marketing_summary.py         ← Script de marketing
```

---

## 🚦 Inicio Rápido

### 1️⃣ Explorar las vistas disponibles
```sql
SELECT table_name 
FROM information_schema.views 
WHERE table_schema = 'public'
ORDER BY table_name;
```

### 2️⃣ Ver datos de ejemplo
```sql
-- Ventas
SELECT * FROM order_summary LIMIT 5;

-- Marketing
SELECT * FROM v_marketing_performance_analysis LIMIT 5;

-- Resumen diario
SELECT * FROM v_sales_costs_daily LIMIT 5;
```

### 3️⃣ Obtener datos de ayer
```sql
-- Ventas de ayer
SELECT * FROM order_summary 
WHERE order_date = CURRENT_DATE - INTERVAL '1 day';

-- Marketing de ayer
SELECT * FROM v_marketing_performance_analysis 
WHERE report_date = CURRENT_DATE - INTERVAL '1 day';

-- Resumen de ayer
SELECT * FROM v_sales_costs_daily 
WHERE day = CURRENT_DATE - INTERVAL '1 day';
```

---

## ❓ FAQ

### ¿Cuál vista debo usar para marketing?
👉 **`v_marketing_performance_analysis`** - Ya tiene ROAS y CPC calculados.

### ¿Cómo relaciono una venta con un anuncio específico?
👉 No hay relación directa. Solo se pueden agrupar **por fecha**.

### ¿Qué vista tiene todo combinado?
👉 **`v_sales_costs_daily`** - Ventas + Marketing por día.

### ¿Cómo calculo ROAS manualmente?
👉 `revenue / NULLIF(spend, 0)` - Pero mejor usa la vista que ya lo tiene.

### ¿Qué campos necesito para un reporte de ventas?
👉 `order_date`, `product_name`, `product_cost` de `order_summary`.

### ¿Qué campos necesito para un reporte de marketing?
👉 `report_date`, `campaign_name`, `adset_name`, `ad_name`, `spend`, `cpc`, `roas`, `conversions` de `v_marketing_performance_analysis`.

---

## 🎓 Nivel de Dificultad de cada Documento

| Documento | Nivel | Tiempo de lectura |
|-----------|-------|-------------------|
| GUIA_RAPIDA_DATOS.md | 🟢 Principiante | 5 min |
| CHEATSHEET_CONSULTAS.md | 🟡 Intermedio | 10 min |
| ESTRUCTURA_BASE_DATOS.md | 🔴 Avanzado | 20 min |

---

## 🔍 Búsqueda Rápida

**¿Buscas...**

- **Campos específicos que necesitas?** → `GUIA_RAPIDA_DATOS.md` - Sección "Datos que Necesitas"
- **Consulta SQL lista para copiar?** → `CHEATSHEET_CONSULTAS.md`
- **Entender la arquitectura completa?** → `ESTRUCTURA_BASE_DATOS.md`
- **Ver diagramas visuales?** → `GUIA_RAPIDA_DATOS.md` - Sección "Estructura Simplificada"
- **Ejemplos de reportes complejos?** → `ESTRUCTURA_BASE_DATOS.md` - Sección "Consultas Útiles"
- **Fórmulas de cálculo?** → `CHEATSHEET_CONSULTAS.md` - Sección "Fórmulas de Cálculo"

---

## 🎯 Próximos Pasos

1. ✅ Lee `GUIA_RAPIDA_DATOS.md` primero (5 minutos)
2. ✅ Prueba las consultas de `CHEATSHEET_CONSULTAS.md`
3. ✅ Explora `ESTRUCTURA_BASE_DATOS.md` para profundizar
4. ✅ Adapta las consultas a tus necesidades específicas

---

## 📞 Soporte

Si necesitas:
- Crear nuevas vistas
- Optimizar consultas
- Agregar nuevos campos

Revisa los archivos en `sql/` o consulta `app/db/business_data.py`.

---

**Documentación creada**: Noviembre 2024  
**Versión**: 1.0  
**Autor**: EliaLabs  

---

## ⭐ Índice Detallado

### ESTRUCTURA_BASE_DATOS.md
1. Tablas Base (order_summary, ad_performance)
2. Vistas de Análisis (v_marketing_performance_analysis, etc.)
3. Relaciones y Cruces (diagramas)
4. Consultas Útiles (8 ejemplos)
5. Resumen de Campos Clave
6. Mejores Prácticas
7. Acceso desde Python

### GUIA_RAPIDA_DATOS.md
1. Datos que Necesitas (tabla de campos)
2. Estructura Simplificada (diagramas)
3. Consultas Rápidas (3 esenciales)
4. Cómo se Cruzan las Tablas
5. Ejemplos Completos (3 reportes)
6. Campos Más Importantes
7. Tips

### CHEATSHEET_CONSULTAS.md
1. Tablas y Vistas Principales
2. Consultas Copy-Paste (15+)
   - Ventas Shopify (3 consultas)
   - Marketing (5 consultas)
   - Combinadas (3 consultas)
3. Campos Clave - Mapa Rápido
4. Fórmulas de Cálculo
5. Filtros de Fecha Comunes
6. Funciones Útiles
7. Ejemplos de Reportes (4 completos)
8. Exportar Resultados
9. Troubleshooting

---

**🎉 ¡Todo listo para empezar!**

