-- Update marketing performance view to include daily spend per ad
-- Run this after the `spend` column is available on the `ad_performance` table

CREATE OR REPLACE VIEW public.v_marketing_performance_analysis AS
SELECT
    date_trunc('day', ap.event_date)                     AS report_date,
    ap.campaign_id,
    ap.campaign_name,
    ap.adset_id,
    ap.adset_name,
    ap.ad_id,
    ap.ad_name,
    SUM(ap.spend)                                        AS spend,
    SUM(ap.revenue)                                      AS revenue,
    SUM(ap.conversions)                                  AS conversions,
    SUM(ap.clicks)                                       AS clicks,
    CASE
        WHEN SUM(ap.spend) > 0 THEN SUM(ap.revenue) / NULLIF(SUM(ap.spend), 0)
        ELSE NULL
    END                                                  AS roas,
    CASE
        WHEN SUM(ap.clicks) > 0 THEN SUM(ap.spend) / NULLIF(SUM(ap.clicks), 0)
        ELSE NULL
    END                                                  AS cpc,
    SUM(ap.impressions)                                  AS impressions
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




