# Спецификация визуализаций Redash

Пять основных визуализаций фактически созданы и проверены в Redash. Скриншоты находятся в `assets/screenshots/` и встроены в корневой `README.md`.

## Фильтры

- период анализа;
- пол пользователя;
- когорта первой покупки;
- кампания;
- товар.

## Визуализации

| Блок | Запрос | Визуализация | Поля |
|---|---|---|---|
| KPI | `03` | Counter | revenue, orders, paying_users, ARPU, AOV за последний день/период |
| Аудитория и заказы | `02` | Line | date; created_orders |
| Деньги | `03` | Line | date; cumulative_revenue |
| Воронка | `04` | Funnel | created_orders → accepted_orders → delivered_orders |
| Retention | `05` | Line | day_number; retention_rate_pct; series = cohort_date |
| Когорты | `06` | Line | month_number; cumulative_revenue, серия cohort_month |
| Кампании | `07` | Bar | campaign; users, revenue, avg_user_check |
| Курьеры | `08` | Scatter | delivered_orders, avg_delivery_minutes; courier_id как label |
| Ассортимент | `09` | Horizontal bar | product_name, revenue |
| Часы пик | `10` | Bar | hour; created_orders |
| Сегменты | `11` | Bar | segment; revenue |

## Правила оформления

- одинаковые цвета одной метрики на всех графиках;
- деньги — с разделителем тысяч и двумя знаками после запятой;
- доли — в процентах;
- ось времени — без пропущенных подписей и лишней детализации;
- в подписи указывать определение метрики и период;
- не использовать круговую диаграмму для большого числа категорий.

## Макет

1. KPI-карточки.
2. Динамика аудитории и денег.
3. Воронка и retention.
4. Кампании и пользовательские сегменты.
5. Курьеры, часы пик и ассортимент.
