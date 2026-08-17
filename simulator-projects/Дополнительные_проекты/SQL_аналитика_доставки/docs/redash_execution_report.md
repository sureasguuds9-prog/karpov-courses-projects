# Отчёт о выполнении запросов в Redash

Источник данных: `Simulator SQL`

Дата live-проверки: 3 августа 2026 года

Период данных: 24 августа — 8 сентября 2022 года

| № | Запрос | Redash | Статус |
|---:|---|---|---|
| 00 | Проверка качества | [query 130232](https://redash.public.karpov.courses/queries/130232/source) | выполнен, 10 контрольных метрик |
| 01 | Успешные заказы | [query 130243](https://redash.public.karpov.courses/queries/130243/source) | выполнен |
| 02 | Дневные метрики | [query 130234](https://redash.public.karpov.courses/queries/130234/source) | выполнен, 16 дней |
| 03 | Выручка и unit-экономика | [query 130235](https://redash.public.karpov.courses/queries/130235/source) | выполнен, 16 дней |
| 04 | Воронка заказов | [query 130236](https://redash.public.karpov.courses/queries/130236/source) | выполнен |
| 05 | Когортный retention | [query 130237](https://redash.public.karpov.courses/queries/130237/source) | выполнен, 136 строк |
| 06 | Когортная выручка | [query 130238](https://redash.public.karpov.courses/queries/130238/source) | выполнен |
| 07 | Маркетинговые кампании | [query 130239](https://redash.public.karpov.courses/queries/130239/source) | выполнен, ожидаемо 0 строк |
| 08 | Эффективность курьеров | [query 130240](https://redash.public.karpov.courses/queries/130240/source) | выполнен |
| 09 | Ассортимент и товары | [query 130241](https://redash.public.karpov.courses/queries/130241/source) | выполнен |
| 10 | Пиковые часы | [query 130242](https://redash.public.karpov.courses/queries/130242/source) | выполнен, 24 часа |
| 11 | Сегменты пользователей | [query 130170](https://redash.public.karpov.courses/queries/130170/source) | выполнен, 3 сегмента |

## Контрольные результаты

- строк в `orders`: 59 595;
- доля отмен: 5,00%;
- дубликаты ключей: 0;
- пустые массивы товаров: 0;
- действия без соответствующего заказа: 0;
- неизвестные товары после `UNNEST`: 0;
- накопленная выручка: 21 679 095;
- максимальная часовая нагрузка: 19:00, 3 685 созданных заказов;
- среднее время доставки по сервису: 19,95 минуты.

## Визуализации

В Redash сохранены пять визуализаций:

1. динамика созданных заказов — query 130234;
2. накопленная выручка — query 130235;
3. cohort retention — query 130237;
4. заказы по часам — query 130242;
5. выручка по пользовательским сегментам — query 130170.

Запросы оставлены непубличными внутри учебного Redash. Для портфолио используются локальные скриншоты без передачи доступа к учебной среде.
