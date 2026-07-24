-- Финальный проект, вариант 2
-- Источник данных в Redash: StartDA (lab)
-- Состояние сегментов: 31 марта 2024 года
--
-- Почему нужны две отдельные агрегации:
-- у одного клиента может быть несколько заказов и несколько событий.
-- Если соединить сырые таблицы сразу, строки перемножатся, а COUNT и AVG исказятся.

WITH delivered_orders AS (
    SELECT
        customer_id,
        COUNT(*) FILTER (
            WHERE order_status = 'Delivered'
        ) AS orders_count,
        AVG(
            EXTRACT(
                EPOCH FROM (
                    order_delivered_customer_time - order_created_time
                )
            ) / 86400.0
        ) FILTER (
            WHERE order_status = 'Delivered'
              AND order_delivered_customer_time IS NOT NULL
        ) AS avg_delivery_days
    FROM orders
    GROUP BY customer_id
),

purchase_events AS (
    SELECT
        customer_id,
        COUNT(*) FILTER (
            WHERE event_type = 'Purchase'
        ) AS purchase_events_count
    FROM customer_actions
    GROUP BY customer_id
)

SELECT
    c.customer_id,
    c.customer_city,
    c.created_at::date AS registration_date,
    DATE '2024-03-31' - c.created_at::date AS days_since_registration,
    COALESCE(o.orders_count, 0) AS orders_count,
    COALESCE(p.purchase_events_count, 0) AS purchase_events_count,
    ROUND(o.avg_delivery_days::numeric, 2) AS avg_delivery_days,
    CASE
        WHEN COALESCE(o.orders_count, 0) >= 3
            THEN 'Постоянный'
        WHEN COALESCE(o.orders_count, 0) BETWEEN 1 AND 2
            THEN 'Разовый'
        WHEN DATE '2024-03-31' - c.created_at::date > 30
            THEN 'Неактивный'
        ELSE 'Новый'
    END AS segment
FROM customers AS c
LEFT JOIN delivered_orders AS o USING (customer_id)
LEFT JOIN purchase_events AS p USING (customer_id)
ORDER BY c.customer_id;
