-- Дневная витрина для оценки флэшмоба 10–16 июля 2026 года.
-- Источник: ClickHouse, simulator_20260720.feed_actions.

WITH
daily AS (
    SELECT
        toDate(time) AS date,
        uniqExact(user_id) AS dau,
        countIf(action = 'like') AS likes,
        countIf(action = 'view') AS views,
        likes / views AS ctr,
        uniqExactIf(post_id, action = 'view') AS unique_viewed_posts
    FROM simulator_20260720.feed_actions
    WHERE time < toDateTime('2026-08-01 00:00:00')
    GROUP BY date
),
first_seen AS (
    -- В feed_actions нет даты создания поста, поэтому новым считаем пост
    -- в день его первого появления в событиях ленты.
    SELECT
        post_id,
        toDate(min(time)) AS first_seen_date
    FROM simulator_20260720.feed_actions
    WHERE time < toDateTime('2026-08-01 00:00:00')
    GROUP BY post_id
),
new_posts AS (
    SELECT
        first_seen_date AS date,
        count() AS new_posts
    FROM first_seen
    GROUP BY date
)
SELECT
    d.date,
    d.dau,
    d.likes,
    d.views,
    d.ctr,
    d.unique_viewed_posts,
    coalesce(n.new_posts, 0) AS new_posts
FROM daily AS d
LEFT JOIN new_posts AS n USING (date)
ORDER BY d.date;
