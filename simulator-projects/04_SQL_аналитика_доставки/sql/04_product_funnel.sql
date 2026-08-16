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
