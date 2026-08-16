-- 01. Базовая витрина неотменённых заказов.
-- Одна строка = один заказ. Используется как эталон логики в следующих запросах.

WITH cancelled_orders AS (
    SELECT DISTINCT order_id
    FROM user_actions
    WHERE action = 'cancel_order'
),
order_users AS (
    SELECT order_id, MIN(user_id) AS user_id
    FROM user_actions
    WHERE action = 'create_order'
    GROUP BY order_id
),
order_revenue AS (
    SELECT o.order_id,
           SUM(p.price) AS revenue
    FROM orders o
    CROSS JOIN LATERAL UNNEST(o.product_ids) AS item(product_id)
    JOIN products p USING (product_id)
    GROUP BY o.order_id
)
SELECT o.order_id,
       ou.user_id,
       o.creation_time,
       o.creation_time::date AS order_date,
       CARDINALITY(o.product_ids) AS product_count,
       orv.revenue
FROM orders o
JOIN order_users ou USING (order_id)
JOIN order_revenue orv USING (order_id)
LEFT JOIN cancelled_orders co USING (order_id)
WHERE co.order_id IS NULL
ORDER BY o.creation_time, o.order_id;
