# Проект 3: A/B-тест цены премиум-подписки

Вариант 3 финального проекта Karpov.Courses.

## Задача

Проверить эксперимент, в котором для части новых пользователей изменилась цена
обычной премиум-подписки через новые платёжные системы. Цена trial-периода не
менялась.

## Главный вывод

Текущую цену не следует раскатывать на всех пользователей:

| Метрика | Контроль | Тест | Эффект | p-value |
|---|---:|---:|---:|---:|
| CR payer | 4.40% | 3.39% | −1.02 п.п. | 0.0059 |
| CR premium | 2.34% | 1.56% | −0.78 п.п. | 0.0033 |
| ARPU | 523.21 | 534.08 | +2.08% | 0.9070 |
| Premium ARPU | 177.13 | 188.19 | +6.24% | 0.8117 |

Цена повысила выручку на одного платящего, но не компенсировала потерю
покупателей. Для подписки нужен более длинный период наблюдения за повторными
платежами, оттоком и LTV.

## Структура

```text
project-3-premium-price-ab-test/
├── data/raw/                  # шесть исходных CSV проекта
├── notebooks/project_3_variant_3.ipynb
├── notebooks/project_3_variant_3_explained.ipynb
├── docs/how_to_repeat.md
└── README.md
```

## Как повторить

```bash
python -m pip install -r requirements.txt
jupyter lab notebooks/project_3_variant_3.ipynb
```

Запустите `Run All`. Ноутбук использует относительный путь `../data/raw`, поэтому
работает после клонирования репозитория.

Общая логика формул находится в
[`../../docs/logic_and_formulas.md`](../../docs/logic_and_formulas.md).

Полный разбор решения по шагам с объяснением «что делаем, зачем и как
интерпретировать» находится в
[`docs/project_3_step_by_step_explanation.md`](docs/project_3_step_by_step_explanation.md).

Если нужен весь разбор прямо внутри Jupyter, открывайте
[`project_3_variant_3_explained.ipynb`](notebooks/project_3_variant_3_explained.ipynb).
