-- Полная последовательность запросов проекта Karpov Delivery SQL Analytics.
-- Запускайте запросы по одному: каждый блок заканчивается точкой с запятой.

-- ============================================================================
-- 00_data_quality.sql
-- ============================================================================

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
-- ============================================================================
-- 01_clean_orders.sql
-- ============================================================================

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
-- ============================================================================
-- 02_daily_metrics.sql
-- ============================================================================

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
-- ============================================================================
-- 03_revenue_unit_economics.sql
-- ============================================================================

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
-- ============================================================================
-- 04_product_funnel.sql
-- ============================================================================

-- 04. Воронка прохождения заказа по дням создания.
-- Этапы считаются на одном наборе order_id, поэтому между ними можно сравнивать конверсию.

WITH order_statuses AS (
    SELECT o.order_id,
           o.creation_time::date AS date,
           EXISTS (
               SELECT 1 FROM user_actions ua
               WHERE ua.order_id = o.order_id AND ua.action = 'cancel_order'
           ) AS is_cancelled,
           EXISTS (
               SELECT 1 FROM courier_actions ca
               WHERE ca.order_id = o.order_id AND ca.action = 'accept_order'
           ) AS is_accepted,
           EXISTS (
               SELECT 1 FROM courier_actions ca
               WHERE ca.order_id = o.order_id AND ca.action = 'deliver_order'
           ) AS is_delivered
    FROM orders o
)
SELECT date,
       COUNT(*) AS created_orders,
       COUNT(*) FILTER (WHERE NOT is_cancelled) AS successful_orders,
       COUNT(*) FILTER (WHERE is_accepted AND NOT is_cancelled) AS accepted_orders,
       COUNT(*) FILTER (WHERE is_delivered AND NOT is_cancelled) AS delivered_orders,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_delivered AND NOT is_cancelled)
             / NULLIF(COUNT(*), 0), 2) AS created_to_delivered_pct
FROM order_statuses
GROUP BY date
ORDER BY date;
-- ============================================================================
-- 05_retention.sql
-- ============================================================================

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
-- ============================================================================
-- 06_cohort_revenue.sql
-- ============================================================================

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
-- ============================================================================
-- 07_marketing_campaigns.sql
-- ============================================================================

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
-- ============================================================================
-- 08_courier_efficiency.sql
-- ============================================================================

-- 08. Эффективность курьеров.
-- Время доставки: от creation_time заказа до действия deliver_order.

WITH deliveries AS (
    SELECT ca.courier_id,
           ca.order_id,
           o.creation_time,
           MIN(ca.time) FILTER (WHERE ca.action = 'accept_order') AS accepted_at,
           MIN(ca.time) FILTER (WHERE ca.action = 'deliver_order') AS delivered_at
    FROM courier_actions ca
    JOIN orders o USING (order_id)
    WHERE NOT EXISTS (
        SELECT 1 FROM user_actions ua
        WHERE ua.order_id = o.order_id AND ua.action = 'cancel_order'
    )
    GROUP BY ca.courier_id, ca.order_id, o.creation_time
),
courier_metrics AS (
    SELECT courier_id,
           COUNT(*) FILTER (WHERE delivered_at IS NOT NULL) AS delivered_orders,
           AVG(EXTRACT(EPOCH FROM (delivered_at - creation_time)) / 60.0)
               FILTER (WHERE delivered_at IS NOT NULL) AS avg_delivery_minutes,
           AVG(EXTRACT(EPOCH FROM (delivered_at - accepted_at)) / 60.0)
               FILTER (WHERE delivered_at IS NOT NULL AND accepted_at IS NOT NULL)
               AS avg_minutes_after_accept
    FROM deliveries
    GROUP BY courier_id
)
SELECT cm.courier_id,
       c.sex,
       DATE_PART('year', AGE(CURRENT_DATE, c.birth_date))::int AS age,
       cm.delivered_orders,
       ROUND(cm.avg_delivery_minutes::numeric, 2) AS avg_delivery_minutes,
       ROUND(cm.avg_minutes_after_accept::numeric, 2) AS avg_minutes_after_accept,
       ROUND(AVG(cm.avg_delivery_minutes) OVER ()::numeric, 2) AS service_avg_minutes
FROM courier_metrics cm
LEFT JOIN couriers c USING (courier_id)
WHERE cm.delivered_orders > 0
ORDER BY cm.delivered_orders DESC, cm.avg_delivery_minutes;
-- ============================================================================
-- 09_product_assortment.sql
-- ============================================================================

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
-- ============================================================================
-- 10_peak_hours.sql
-- ============================================================================

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
-- ============================================================================
-- 11_user_segments.sql
-- ============================================================================

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
