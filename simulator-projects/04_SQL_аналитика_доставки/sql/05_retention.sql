-- 05. Дневной retention по когорте первой успешной покупки.
-- Одна строка результата = когорта × номер дня.

WITH successful_orders AS (
    SELECT DISTINCT ua.user_id,
           o.order_id,
           o.creation_time::date AS activity_date
    FROM orders o
    JOIN user_actions ua
      ON ua.order_id = o.order_id AND ua.action = 'create_order'
    WHERE NOT EXISTS (
        SELECT 1 FROM user_actions x
        WHERE x.order_id = o.order_id AND x.action = 'cancel_order'
    )
),
user_cohorts AS (
    SELECT user_id, MIN(activity_date) AS cohort_date
    FROM successful_orders
    GROUP BY user_id
),
activity AS (
    SELECT DISTINCT so.user_id,
           uc.cohort_date,
           so.activity_date,
           so.activity_date - uc.cohort_date AS day_number
    FROM successful_orders so
    JOIN user_cohorts uc USING (user_id)
),
cohort_sizes AS (
    SELECT cohort_date, COUNT(*) AS cohort_size
    FROM user_cohorts
    GROUP BY cohort_date
)
SELECT a.cohort_date,
       a.day_number,
       cs.cohort_size,
       COUNT(DISTINCT a.user_id) AS retained_users,
       ROUND(100.0 * COUNT(DISTINCT a.user_id) / NULLIF(cs.cohort_size, 0), 2)
           AS retention_rate_pct
FROM activity a
JOIN cohort_sizes cs USING (cohort_date)
WHERE a.day_number BETWEEN 0 AND 30
GROUP BY a.cohort_date, a.day_number, cs.cohort_size
ORDER BY a.cohort_date, a.day_number;
