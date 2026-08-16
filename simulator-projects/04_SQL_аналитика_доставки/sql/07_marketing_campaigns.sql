-- 07. Сравнение маркетинговых кампаний.
-- Замените строки с NULL реальными парами (user_id, campaign) из условия задачи.
-- Запрос намеренно не содержит выдуманных ID и до заполнения вернёт пустой результат.

WITH campaign_users(user_id, campaign) AS (
    VALUES
        (NULL::integer, NULL::text)
        -- Пример формата, не данные: (123, 'Campaign 1'), (456, 'Campaign 2')
),
order_revenue AS (
    SELECT cu.campaign,
           cu.user_id,
           o.order_id,
           SUM(p.price) AS order_revenue
    FROM campaign_users cu
    JOIN user_actions ua
      ON ua.user_id = cu.user_id AND ua.action = 'create_order'
    JOIN orders o USING (order_id)
    CROSS JOIN LATERAL UNNEST(o.product_ids) AS item(product_id)
    JOIN products p USING (product_id)
    WHERE cu.user_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM user_actions x
          WHERE x.order_id = o.order_id AND x.action = 'cancel_order'
      )
    GROUP BY cu.campaign, cu.user_id, o.order_id
),
user_metrics AS (
    SELECT campaign,
           user_id,
           COUNT(*) AS orders,
           SUM(order_revenue) AS user_revenue,
           AVG(order_revenue) AS user_avg_check
    FROM order_revenue
    GROUP BY campaign, user_id
)
SELECT campaign,
       COUNT(*) AS users_with_orders,
       SUM(orders) AS orders,
       ROUND(SUM(user_revenue)::numeric, 2) AS revenue,
       ROUND(AVG(orders)::numeric, 2) AS orders_per_user,
       ROUND(AVG(user_revenue)::numeric, 2) AS revenue_per_user,
       ROUND(AVG(user_avg_check)::numeric, 2) AS avg_user_check
FROM user_metrics
GROUP BY campaign
ORDER BY revenue DESC;
