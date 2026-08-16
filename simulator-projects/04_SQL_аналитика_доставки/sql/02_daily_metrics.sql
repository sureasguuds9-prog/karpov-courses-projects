-- 02. Ежедневные продуктовые метрики.
-- DAU включает пользователей с любым действием; paying_users — только с успешным заказом.

WITH calendar AS (
    SELECT GENERATE_SERIES(
        (SELECT MIN(creation_time)::date FROM orders),
        (SELECT MAX(creation_time)::date FROM orders),
        INTERVAL '1 day'
    )::date AS date
),
daily_active AS (
    SELECT time::date AS date, COUNT(DISTINCT user_id) AS dau
    FROM user_actions
    GROUP BY time::date
),
created AS (
    SELECT ua.time::date AS date,
           COUNT(DISTINCT ua.order_id) AS created_orders,
           COUNT(DISTINCT ua.user_id) AS ordering_users
    FROM user_actions ua
    WHERE ua.action = 'create_order'
    GROUP BY ua.time::date
),
cancelled AS (
    SELECT time::date AS date, COUNT(DISTINCT order_id) AS cancelled_orders
    FROM user_actions
    WHERE action = 'cancel_order'
    GROUP BY time::date
),
successful AS (
    SELECT o.creation_time::date AS date,
           COUNT(DISTINCT o.order_id) AS successful_orders,
           COUNT(DISTINCT ua.user_id) AS paying_users
    FROM orders o
    JOIN user_actions ua
      ON ua.order_id = o.order_id AND ua.action = 'create_order'
    WHERE NOT EXISTS (
        SELECT 1 FROM user_actions x
        WHERE x.order_id = o.order_id AND x.action = 'cancel_order'
    )
    GROUP BY o.creation_time::date
),
delivered AS (
    SELECT time::date AS date, COUNT(DISTINCT order_id) AS delivered_orders
    FROM courier_actions
    WHERE action = 'deliver_order'
    GROUP BY time::date
)
SELECT cal.date,
       COALESCE(da.dau, 0) AS dau,
       COALESCE(c.ordering_users, 0) AS ordering_users,
       COALESCE(s.paying_users, 0) AS paying_users,
       COALESCE(c.created_orders, 0) AS created_orders,
       COALESCE(s.successful_orders, 0) AS successful_orders,
       COALESCE(d.delivered_orders, 0) AS delivered_orders,
       COALESCE(cn.cancelled_orders, 0) AS cancelled_orders,
       ROUND(100.0 * COALESCE(cn.cancelled_orders, 0)
             / NULLIF(c.created_orders, 0), 2) AS cancellation_rate_pct
FROM calendar cal
LEFT JOIN daily_active da USING (date)
LEFT JOIN created c USING (date)
LEFT JOIN cancelled cn USING (date)
LEFT JOIN successful s USING (date)
LEFT JOIN delivered d USING (date)
ORDER BY cal.date;
