# Проекты курса «Аналитик данных» — Karpov.Courses

Общий репозиторий с финальными аналитическими проектами. Каждый проект
лежит в отдельной папке и содержит воспроизводимый Jupyter Notebook, выводы и
необходимые материалы.

## Проекты

| Проект | Содержание | Основные инструменты |
|---|---|---|
| [1. Аналитика мобильной игры](../../project-1-mobile-game-analytics/) | Retention, когортный анализ и A/B-тест | Python, Pandas, SciPy, статистика |
| [2. A/B-тест оплаты и сегментация клиентов](../../project-2-payment-ab-segmentation/) | Анализ новой механики оплаты, статистические тесты, SQL-сегментация | Python, Pandas, SciPy, Statsmodels, PostgreSQL |
| [3. A/B-тест цены премиума](../../project-3-premium-price-ab-test/) | Цена премиум-подписки, качество транзакций, CR, ARPU, статистические тесты | Python, Pandas, SciPy, Statsmodels |

## Логика и формулы

Общая методичка по единице анализа, CR, ARPU, ARPPU, retention, z-тестам,
Welch t-test, доверительным интервалам и SQL-агрегациям находится в
[`logic_and_formulas.md`](logic_and_formulas.md).

## Как использовать

```bash
git clone https://github.com/yzinchenko-data/karpov-courses-projects.git
cd karpov-courses-projects
python -m pip install -r project-2-payment-ab-segmentation/requirements.txt
```

После установки можно открыть нужный ноутбук в Jupyter и выполнить `Run All`.

## Автор

Ярослав Зинченко
