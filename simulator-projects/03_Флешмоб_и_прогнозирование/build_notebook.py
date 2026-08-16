from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "notebooks" / "flashmob_causal_impact.ipynb"
OUT.parent.mkdir(parents=True, exist_ok=True)

nb = nbf.v4.new_notebook()
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.9"},
}

nb["cells"] = [
    nbf.v4.new_markdown_cell("""# Флэшмоб в ленте: оценка эффекта

## tl;dr

Учебный проект по теме **«Прогнозирование метрик» курса «Симулятор аналитика» Karpov.Courses**. По агрегированным событиям ленты оцениваем эффект флэшмоба 10–16 июля 2026 года с помощью CausalImpact.

Основной результат: во время мероприятия выросли просмотры, CTR и число уникальных просматриваемых постов; убедительного роста DAU и числа новых постов нет. После 16 июля устойчивый дополнительный эффект визуально не сохраняется.

> Датасет учебный: это обезличенная дневная витрина из `simulator_20260720.feed_actions`, а не данные реального работодателя."""),
    nbf.v4.new_markdown_cell("""## Context & Methods

- **Бизнес-вопрос:** изменил ли флэшмоб пользовательскую активность?
- **Пре-период:** 30 мая — 9 июля 2026 года.
- **Пост-период:** 10–16 июля 2026 года.
- **Метод:** Bayesian structural time series через `tfcausalimpact`.
- **Ограничение:** контрольного ряда нет, поэтому это квазиэкспериментальная, а не равная A/B-тесту оценка причинного эффекта."""),
    nbf.v4.new_code_cell("""import os
import warnings
from pathlib import Path

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import pandas as pd
from causalimpact import CausalImpact

plt.style.use("seaborn-v0_8-whitegrid")
pd.set_option("display.float_format", lambda x: f"{x:,.3f}")

PRE_PERIOD = ["2026-05-30", "2026-07-09"]
POST_PERIOD = ["2026-07-10", "2026-07-16"]

cwd = Path.cwd()
candidates = [
    cwd / "data" / "flashmob_daily_metrics.csv",
    cwd.parent / "data" / "flashmob_daily_metrics.csv",
]
DATA_PATH = next((p for p in candidates if p.exists()), None)
if DATA_PATH is None:
    raise FileNotFoundError("Не найден data/flashmob_daily_metrics.csv")"""),
    nbf.v4.new_markdown_cell("""## Data

Одна строка — один полный календарный день. `DAU` — уникальные пользователи с событием в ленте; `CTR = likes / views`. Неполный день 1 августа исключён."""),
    nbf.v4.new_code_cell("""metrics = pd.read_csv(DATA_PATH, parse_dates=["date"]).set_index("date")

expected_dates = pd.date_range(metrics.index.min(), metrics.index.max(), freq="D")
checks = pd.Series({
    "строк": len(metrics),
    "дубликатов дат": int(metrics.index.duplicated().sum()),
    "пропущенных дней": len(expected_dates.difference(metrics.index)),
    "пропусков": int(metrics.isna().sum().sum()),
    "максимальная ошибка CTR": float(
        (metrics["ctr"] - metrics["likes"] / metrics["views"]).abs().max()
    ),
})

assert checks["дубликатов дат"] == 0
assert checks["пропущенных дней"] == 0
assert checks["пропусков"] == 0
assert checks["максимальная ошибка CTR"] < 1e-8
display(checks.to_frame("значение"))
display(metrics.head())"""),
    nbf.v4.new_code_cell("""plot_cols = ["dau", "views", "likes", "ctr", "unique_viewed_posts", "new_posts"]
fig, axes = plt.subplots(3, 2, figsize=(14, 11), sharex=True)

for ax, col in zip(axes.flat, plot_cols):
    ax.plot(metrics.index, metrics[col], linewidth=2)
    ax.axvspan(pd.Timestamp(POST_PERIOD[0]), pd.Timestamp(POST_PERIOD[1]),
               color="#ff9f43", alpha=0.25, label="флэшмоб")
    ax.set_title(col)
    ax.tick_params(axis="x", rotation=30)

fig.suptitle("Дневные метрики ленты", fontsize=15)
fig.tight_layout()
plt.show()"""),
    nbf.v4.new_markdown_cell("""## Results

Модель строит контрфактический прогноз для 10–16 июля. Эффект — разница между фактом и прогнозом без флэшмоба. Если 95%-й интервал включает ноль, изменение не считаем статистически убедительным."""),
    nbf.v4.new_code_cell("""def fit_impact(metric):
    impact = CausalImpact(metrics[[metric]], PRE_PERIOD, POST_PERIOD)
    row = impact.summary_data["average"]
    lower = float(row["abs_effect_lower"])
    upper = float(row["abs_effect_upper"])
    significant = not (lower <= 0 <= upper)
    direction = "рост" if float(row["abs_effect"]) > 0 else "снижение"
    return impact, {
        "metric": metric,
        "actual": float(row["actual"]),
        "predicted": float(row["predicted"]),
        "effect": float(row["abs_effect"]),
        "ci_lower": lower,
        "ci_upper": upper,
        "result": direction if significant else "нет убедительного изменения",
    }

model_metrics = ["dau", "ctr", "views", "new_posts", "unique_viewed_posts"]
impacts, rows = {}, []
for metric in model_metrics:
    impacts[metric], result = fit_impact(metric)
    rows.append(result)

results = pd.DataFrame(rows).set_index("metric")
results"""),
    nbf.v4.new_code_cell("""fig, axes = plt.subplots(3, 2, figsize=(14, 12))
for ax, metric in zip(axes.flat, model_metrics):
    inf = impacts[metric].inferences
    ax.plot(inf.index, metrics.loc[inf.index, metric], label="факт", linewidth=2)
    ax.plot(inf.index, inf["complete_preds_means"], label="контрфактический прогноз", linewidth=1.5)
    ax.axvspan(pd.Timestamp(POST_PERIOD[0]), pd.Timestamp(POST_PERIOD[1]),
               color="#ff9f43", alpha=0.2)
    ax.set_title(metric)
    ax.legend(fontsize=8)

axes.flat[-1].axis("off")
fig.tight_layout()
plt.show()"""),
    nbf.v4.new_markdown_cell("""## Takeaways

1. Флэшмоб усилил потребление контента: наиболее заметны просмотры и число уникальных просматриваемых постов.
2. CTR вырос, то есть глубина взаимодействия улучшилась не только за счёт большего числа показов.
3. Для DAU и новых постов уверенного эффекта нет: мероприятие сильнее повлияло на уже активную аудиторию.
4. После мероприятия метрики возвращаются к прежней траектории; устойчивого долгосрочного эффекта не видно.
5. Результаты зависят от допущения, что одновременно не было других крупных изменений продукта или маркетинга."""),
]

nbf.write(nb, OUT)
print(OUT)
