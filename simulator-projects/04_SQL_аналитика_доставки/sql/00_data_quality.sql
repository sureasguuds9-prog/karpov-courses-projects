-- 00. Проверка качества данных.
-- Результат: список контрольных метрик. Ненулевые orphan-показатели требуют расследования.

WITH checks AS (
    SELECT 'orders_rows' AS metric, COUNT(*)::text AS value FROM orders
    UNION ALL
    SELECT 'duplicate_order_ids', (COUNT(*) - COUNT(DISTINCT order_id))::text FROM orders
    UNION ALL
    SELECT 'duplicate_user_ids', (COUNT(*) - COUNT(DISTINCT user_id))::text FROM users
    UNION ALL
    SELECT 'duplicate_courier_ids', (COUNT(*) - COUNT(DISTINCT courier_id))::text FROM couriers
    UNION ALL
    SELECT 'duplicate_product_ids', (COUNT(*) - COUNT(DISTINCT product_id))::text FROM products
    UNION ALL
    SELECT 'orders_with_empty_product_array', COUNT(*)::text
    FROM orders
    WHERE product_ids IS NULL OR CARDINALITY(product_ids) = 0
    UNION ALL
    SELECT 'user_actions_without_order', COUNT(*)::text
    FROM user_actions ua
    LEFT JOIN orders o USING (order_id)
    WHERE o.order_id IS NULL
    UNION ALL
    SELECT 'courier_actions_without_order', COUNT(*)::text
    FROM courier_actions ca
    LEFT JOIN orders o USING (order_id)
    WHERE o.order_id IS NULL
    UNION ALL
    SELECT 'unknown_products_after_unnest', COUNT(*)::text
    FROM orders o
    CROSS JOIN LATERAL UNNEST(o.product_ids) AS item(product_id)
    LEFT JOIN products p USING (product_id)
    WHERE p.product_id IS NULL
    UNION ALL
    SELECT 'cancelled_order_share_pct',
           ROUND(100.0 * COUNT(DISTINCT order_id) FILTER (WHERE action = 'cancel_order')
                 / NULLIF(COUNT(DISTINCT order_id), 0), 2)::text
    FROM user_actions
)
SELECT metric, value
FROM checks
ORDER BY metric;
