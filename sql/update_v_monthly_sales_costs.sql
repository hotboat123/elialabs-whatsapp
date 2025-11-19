-- Recreate monthly sales & cost view including marketing spend
-- Adjust table / column names if your schema differs.

CREATE OR REPLACE VIEW public.v_sales_dashboard_planilla AS
WITH sales AS (
    SELECT
        date_trunc('month', o.order_date)::date AS month,
        SUM(o.total_revenue)                    AS revenue,
        SUM(o.product_cost)                     AS product_cost
    FROM public.order_summary o
    GROUP BY 1
),
marketing AS (
    SELECT
        date_trunc('month', v.report_date)::date AS month,
        SUM(v.spend)                              AS marketing_cost
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




