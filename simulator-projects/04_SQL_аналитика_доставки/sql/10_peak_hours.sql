-- 10. Нагрузка и отмены по часу создания заказа.

WITH created_orders AS (
    SELECT ua.order_id,
           ua.time,
           EXTRACT(HOUR FROM ua.time)::int AS hour,
           EXISTS (
               SELECT 1 FROM user_actions x
               WHERE x.order_id = ua.order_id AND x.action = 'cancel_order'
           ) AS is_cancelled
    FROM user_actions ua
    WHERE ua.action = 'create_order'
)
SELECT hour,
       COUNT(*) AS created_orders,
       COUNT(*) FILTER (WHERE NOT is_cancelled) AS successful_orders,
       COUNT(*) FILTER (WHERE is_cancelled) AS cancelled_orders,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_cancelled)
             / NULLIF(COUNT(*), 0), 2) AS cancellation_rate_pct,
       ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS order_share_pct
FROM created_orders
GROUP BY hour
ORDER BY hour;
