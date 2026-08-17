-- 06. Месячные когорты: пользователи, заказы и накопительная выручка.

WITH order_revenue AS (
    SELECT o.order_id,
           MIN(ua.user_id) AS user_id,
           DATE_TRUNC('month', o.creation_time)::date AS activity_month,
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
    GROUP BY o.order_id, DATE_TRUNC('month', o.creation_time)::date
),
cohorts AS (
    SELECT user_id, MIN(activity_month) AS cohort_month
    FROM order_revenue
    GROUP BY user_id
),
cohort_metrics AS (
    SELECT c.cohort_month,
           r.activity_month,
           (EXTRACT(YEAR FROM AGE(r.activity_month, c.cohort_month)) * 12
            + EXTRACT(MONTH FROM AGE(r.activity_month, c.cohort_month)))::int AS month_number,
           COUNT(DISTINCT r.user_id) AS active_users,
           COUNT(DISTINCT r.order_id) AS orders,
           SUM(r.revenue) AS revenue
    FROM order_revenue r
    JOIN cohorts c USING (user_id)
    GROUP BY c.cohort_month, r.activity_month
)
SELECT cohort_month,
       activity_month,
       month_number,
       active_users,
       orders,
       ROUND(revenue::numeric, 2) AS revenue,
       ROUND((revenue / NULLIF(active_users, 0))::numeric, 2) AS revenue_per_active_user,
       ROUND(SUM(revenue) OVER (
           PARTITION BY cohort_month ORDER BY month_number
       )::numeric, 2) AS cumulative_revenue
FROM cohort_metrics
ORDER BY cohort_month, month_number;
