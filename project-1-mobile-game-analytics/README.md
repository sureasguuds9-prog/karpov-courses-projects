# Mobile Game Product Analytics

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.x-150458?logo=pandas&logoColor=white)
![Tests](https://img.shields.io/badge/tests-passed-2EA44F)
![Status](https://img.shields.io/badge/status-ready%20for%20review-2EA44F)

Финальный проект курса **«Аналитик данных»**: когортный retention, разбор A/B-теста
акционных предложений и дизайн метрик тематического события в мобильной игре.

## Главный вывод

**Тестовый набор B пока нельзя считать лучшим.** ARPU вырос на 5,26%, но статистически
значимого эффекта нет (`p = 0,533`), а конверсия в покупку снизилась на 6,64% относительно
контроля (`p = 0,035`). Дополнительно обнаружен аномальный кластер крупных плательщиков
в A, поэтому перед следующим экспериментом требуется проверить логирование и
стратифицировать игроков по историческому LTV.

| Результат | Значение |
|---|---:|
| Retention D1 / D7 / D14 | 2,35% / 5,86% / 4,50% |
| ARPU A → B | 25,414 → 26,751 |
| Conversion A → B | 0,954% → 0,891% |
| ARPPU A → B | 2 663,998 → 3 003,658 |
| Решение по B | не раскатывать без повторного теста |

> Retention рассчитан для последних полностью наблюдаемых когорт 01–09.09.2020 на
> горизонте D0–D14. Это классический day-N, а не rolling retention.

![Когортный retention](figures/retention_heatmap.png)

![Ключевые метрики A/B-теста](figures/ab_key_metrics.png)

## Что находится в проекте

```text
mobile-game-product-analytics/
├── notebooks/
│   └── final_project_variant_1.ipynb  # полный выполненный анализ
├── src/
│   └── retention.py                   # переиспользуемая функция retention
├── tests/
│   └── test_retention.py              # unit-тесты функции
├── reports/
│   └── final_report.md                # выводы в формате отчёта менеджеру
├── figures/                            # графики из ноутбука
├── data/
│   ├── raw/ab_test.csv                # исходные данные задания 2
│   └── README.md                       # порядок подключения больших файлов
└── scripts/validate_project.py         # быстрая проверка проекта
```

## Быстрый просмотр

- **[Открыть выполненный ноутбук](notebooks/final_project_variant_1.ipynb)** — код,
  проверки качества данных, таблицы, статистические тесты и визуализации.
- **[Прочитать итоговый отчёт](reports/final_report.md)** — краткий ответ по всем трём
  заданиям и рекомендация менеджеру.
- **[Посмотреть функцию retention](src/retention.py)** — независимая от ноутбука реализация.

## Методология

### 1. Retention

В основном ноутбуке расчёт показан последовательно через простые операции `Pandas`:
преобразование дат, объединение таблиц, расчёт дня жизни, `pivot_table` и деление на
размер когорты. Отдельная функция сохранена в `src/retention.py` для формального
соответствия условию задания.

```python
from src.retention import calculate_retention

retention = calculate_retention(
    reg_data="data/raw/problem1-reg_data.csv",
    auth_data="data/raw/problem1-auth_data.csv",
    start_date="2020-09-01",
    end_date="2020-09-09",
    max_days=14,
    as_percent=True,
)
```

### 2. A/B-тест

- Sample Ratio Mismatch: `chi-square goodness-of-fit`;
- ARPU и ARPPU: готовый `Welch t-test` из библиотеки `Pingouin`;
- conversion to payer: `chi-square test` из `scipy.stats`;
- форма распределений плательщиков: описательные статистики и визуальная проверка.

ARPU выбрана primary metric, conversion и ARPPU — диагностические. Выбросы не удаляются
post-hoc: их происхождение становится отдельной проверкой качества эксперимента.

### 3. Метрики события

Использована продуктовая цепочка: **охват → старт → прогресс → завершение → награда →
удержание/монетизация**, дополненная guardrails. Для механики отката добавлены rollback,
recovery, net progress velocity и churn после потери прогресса.

## Воспроизведение

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
jupyter lab notebooks/final_project_variant_1.ipynb
```

Файлы задания 1 слишком велики для обычного Git-репозитория. В ноутбуке уже указаны
локальные пути ко всем трём исходным файлам из папки `Downloads`. На другом компьютере
достаточно заменить значения `REG_PATH`, `AUTH_PATH` и `AB_PATH` в ячейке загрузки. Подробности находятся в
[`data/README.md`](data/README.md).

Проверка структуры и сохранённых результатов:

```bash
python scripts/validate_project.py
```

## Стек

`Python` · `Pandas` · `Pingouin` · `SciPy` · `Matplotlib` · `Seaborn` · `Jupyter` · `Pytest`
