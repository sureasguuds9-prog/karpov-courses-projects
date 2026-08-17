-- 11. Простая сегментация пользователей по числу успешных заказов.
-- Strong junior вариант: понятные бизнес-пороги без сложной RFM-модели.

WITH order_revenue AS (
    SELECT ua.user_id,
           o.order_id,
           MAX(o.creation_time) AS order_time,
           SUM(p.price) AS revenue
    FROM orders o
    JOIN user_actions ua
      ON ua.order_id = o.order_id AND ua.action = 'create_order'
    CROSS JOIN LATERAL UNNEST(o.product_ids) AS item(product_id)
    JOIN products p USING (product_id)
    WHERE NOT EXISTS (
        SELECT 1 FROM user_actions x
        WHERE x.order_id = o.order_id AND x.action = 'cancel_order'
    )
    GROUP BY ua.user_id, o.order_id
),
user_metrics AS (
    SELECT user_id,
           COUNT(*) AS orders,
           SUM(revenue) AS revenue,
           MAX(order_time)::date AS last_order_date
    FROM order_revenue
    GROUP BY user_id
),
segmented AS (
    SELECT *,
           CASE
               WHEN orders = 1 THEN '1. One-time'
               WHEN orders BETWEEN 2 AND 4 THEN '2. Repeat'
               ELSE '3. Loyal'
           END AS user_segment
    FROM user_metrics
)
SELECT user_segment,
       COUNT(*) AS users,
       SUM(orders) AS orders,
       ROUND(AVG(orders)::numeric, 2) AS avg_orders_per_user,
       ROUND(SUM(revenue)::numeric, 2) AS revenue,
       ROUND(100.0 * SUM(revenue) / NULLIF(SUM(SUM(revenue)) OVER (), 0), 2)
           AS revenue_share_pct,
       MAX(last_order_date) AS latest_order_date
FROM segmented
GROUP BY user_segment
ORDER BY user_segment;
