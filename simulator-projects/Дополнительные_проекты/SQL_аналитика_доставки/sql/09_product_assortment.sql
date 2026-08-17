-- 09. Ассортимент: количество проданных единиц и вклад в выручку.

WITH sold_items AS (
    SELECT item.product_id,
           o.order_id,
           p.name,
           p.price
    FROM orders o
    CROSS JOIN LATERAL UNNEST(o.product_ids) AS item(product_id)
    JOIN products p USING (product_id)
    WHERE NOT EXISTS (
        SELECT 1 FROM user_actions ua
        WHERE ua.order_id = o.order_id AND ua.action = 'cancel_order'
    )
),
product_metrics AS (
    SELECT product_id,
           name,
           COUNT(*) AS units_sold,
           COUNT(DISTINCT order_id) AS orders_with_product,
           SUM(price) AS revenue
    FROM sold_items
    GROUP BY product_id, name
)
SELECT product_id,
       name AS product_name,
       units_sold,
       orders_with_product,
       ROUND(revenue::numeric, 2) AS revenue,
       ROUND(100.0 * revenue / NULLIF(SUM(revenue) OVER (), 0), 2) AS revenue_share_pct,
       ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC)
             / NULLIF(SUM(revenue) OVER (), 0), 2) AS cumulative_revenue_share_pct,
       DENSE_RANK() OVER (ORDER BY revenue DESC) AS revenue_rank
FROM product_metrics
ORDER BY revenue DESC;
