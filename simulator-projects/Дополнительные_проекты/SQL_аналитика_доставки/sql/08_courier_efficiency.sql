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
