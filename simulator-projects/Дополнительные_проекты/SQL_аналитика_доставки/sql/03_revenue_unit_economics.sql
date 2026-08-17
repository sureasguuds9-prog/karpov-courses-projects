-- 03. Выручка, ARPU, ARPPU и AOV по дням.
-- Важно: ARPU использует всех активных пользователей дня, ARPPU — платящих.

WITH order_revenue AS (
    SELECT o.order_id,
           o.creation_time::date AS date,
           SUM(p.price) AS order_revenue
    FROM orders o
    CROSS JOIN LATERAL UNNEST(o.product_ids) AS item(product_id)
    JOIN products p USING (product_id)
    WHERE NOT EXISTS (
        SELECT 1 FROM user_actions ua
        WHERE ua.order_id = o.order_id AND ua.action = 'cancel_order'
    )
    GROUP BY o.order_id, o.creation_time::date
),
revenue_by_day AS (
    SELECT date,
           COUNT(*) AS orders,
           SUM(order_revenue) AS revenue,
           AVG(order_revenue) AS aov
    FROM order_revenue
    GROUP BY date
),
daily_active AS (
    SELECT time::date AS date, COUNT(DISTINCT user_id) AS active_users
    FROM user_actions
    GROUP BY time::date
),
daily_payers AS (
    SELECT o.creation_time::date AS date, COUNT(DISTINCT ua.user_id) AS paying_users
    FROM orders o
    JOIN user_actions ua
      ON ua.order_id = o.order_id AND ua.action = 'create_order'
    WHERE NOT EXISTS (
        SELECT 1 FROM user_actions x
        WHERE x.order_id = o.order_id AND x.action = 'cancel_order'
    )
    GROUP BY o.creation_time::date
)
SELECT r.date,
       r.orders,
       da.active_users,
       dp.paying_users,
       ROUND(r.revenue::numeric, 2) AS revenue,
       ROUND(r.revenue / NULLIF(da.active_users, 0), 2) AS arpu,
       ROUND(r.revenue / NULLIF(dp.paying_users, 0), 2) AS arppu,
       ROUND(r.aov::numeric, 2) AS aov,
       ROUND(SUM(r.revenue) OVER (ORDER BY r.date)::numeric, 2) AS cumulative_revenue
FROM revenue_by_day r
JOIN daily_active da USING (date)
JOIN daily_payers dp USING (date)
ORDER BY r.date;
