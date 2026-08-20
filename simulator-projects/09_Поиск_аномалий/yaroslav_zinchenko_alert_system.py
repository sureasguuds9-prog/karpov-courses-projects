"""Система алертов по ключевым метрикам приложения, 57 поток.

Каждые 15 минут DAG сравнивает шесть ключевых метрик ленты и мессенджера
с распределением значений в тот же 15-минутный слот суток за предыдущие
14 дней и присылает алерт в Telegram при выходе за устойчивый IQR-коридор.
"""

import io
import os
from datetime import datetime, timedelta

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import telegram
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from read_db.CH import Getch


DAG_ID = "jaroslav_zinchenko_rqq5838_alert_system"
SOURCE_SCHEMA = "simulator_20260720"
STREAM_NAME = "57 поток"
CHAT_ID = 1058410376
BOT_TOKEN = os.environ.get("ALERT_BOT_TOKEN")

LOOKBACK_DAYS = 14   # сколько предыдущих дней берём в baseline одного слота
IQR_COEF = 1.5        # классический коэффициент Тьюки
MIN_DEVIATION = 0.10   # отклонение от медианы должно быть не меньше 10%

METRICS_META = {
    "feed_active_users": {
        "group": "Лента",
        "title": "Активные пользователи ленты",
        "format": ".0f",
    },
    "views": {"group": "Лента", "title": "Просмотры", "format": ".0f"},
    "likes": {"group": "Лента", "title": "Лайки", "format": ".0f"},
    "ctr": {"group": "Лента", "title": "CTR", "format": ".2%"},
    "messenger_active_users": {
        "group": "Мессенджер",
        "title": "Активные пользователи мессенджера",
        "format": ".0f",
    },
    "messages_sent": {
        "group": "Мессенджер",
        "title": "Отправленные сообщения",
        "format": ".0f",
    },
}

default_args = {
    "owner": "jaroslav-zinchenko-rqq5838",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "start_date": datetime(2026, 8, 20),
}


def load_metrics():
    """Возвращает непрерывный ряд полных 15-минутных интервалов.

    Пустые интервалы явно заполняются нулями: исчезновение всех событий —
    само по себе возможная аномалия и не должно теряться при склейке.
    """
    current_ts = pd.Timestamp(
        Getch(
            "SELECT toStartOfFifteenMinutes(now()) - INTERVAL 15 MINUTE AS ts"
        ).df.iloc[0, 0]
    )
    start_ts = current_ts - timedelta(days=LOOKBACK_DAYS)

    feed_query = f"""
        SELECT
            toStartOfFifteenMinutes(time) AS ts,
            uniqExact(user_id)            AS feed_active_users,
            countIf(action = 'view')      AS views,
            countIf(action = 'like')       AS likes
        FROM {SOURCE_SCHEMA}.feed_actions
        WHERE time >= toDateTime('{start_ts}')
          AND time <  toDateTime('{current_ts}') + INTERVAL 15 MINUTE
        GROUP BY ts
        ORDER BY ts
    """

    message_query = f"""
        SELECT
            toStartOfFifteenMinutes(time) AS ts,
            uniqExact(user_id)            AS messenger_active_users,
            count()                       AS messages_sent
        FROM {SOURCE_SCHEMA}.message_actions
        WHERE time >= toDateTime('{start_ts}')
          AND time <  toDateTime('{current_ts}') + INTERVAL 15 MINUTE
        GROUP BY ts
        ORDER BY ts
    """

    feed = Getch(feed_query).df
    messages = Getch(message_query).df
    metrics = pd.merge(feed, messages, on="ts", how="outer")

    full_grid = pd.DataFrame(
        {"ts": pd.date_range(start=start_ts, end=current_ts, freq="15min")}
    )
    metrics = full_grid.merge(metrics, on="ts", how="left").sort_values("ts")

    count_columns = [
        "feed_active_users", "views", "likes",
        "messenger_active_users", "messages_sent",
    ]
    metrics[count_columns] = metrics[count_columns].fillna(0)
    metrics["ctr"] = (
        metrics["likes"] / metrics["views"].replace(0, np.nan)
    ).fillna(0.0)
    return metrics.reset_index(drop=True), current_ts


def get_same_slot_baseline(metrics, metric, current_ts):
    """Берёт ровно тот же час:минута за каждый из LOOKBACK_DAYS дней."""
    expected_timestamps = [
        current_ts - timedelta(days=day) for day in range(1, LOOKBACK_DAYS + 1)
    ]
    baseline = metrics.loc[metrics["ts"].isin(expected_timestamps), ["ts", metric]]
    return baseline.dropna().sort_values("ts").reset_index(drop=True)


def check_anomaly(current_value, baseline_values):
    """Возвращает признак аномалии и параметры устойчивого IQR-интервала."""
    values = np.asarray(baseline_values, dtype=float)
    if len(values) < 7 or pd.isna(current_value):
        return False, 0.0, None, None, None

    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    low = max(0.0, q1 - IQR_COEF * iqr)
    high = q3 + IQR_COEF * iqr
    median = float(np.median(values))

    if median == 0:
        deviation = 0.0 if current_value == 0 else float("inf")
    else:
        deviation = (current_value - median) / median

    outside_interval = current_value < low or current_value > high
    material_deviation = abs(deviation) >= MIN_DEVIATION
    return outside_interval and material_deviation, deviation, low, high, median


def build_plot(baseline, metric, current_ts, current_value, low, high, median):
    """Строит график сопоставимых слотов, не смешивая разные часы суток."""
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(
        baseline["ts"], baseline[metric], marker="o",
        label="Тот же 15-минутный слот в предыдущие дни",
    )
    ax.scatter(
        [current_ts], [current_value], color="red", s=70, zorder=5,
        label="Текущее значение",
    )
    ax.axhspan(low, high, color="green", alpha=0.15, label="IQR-коридор")
    ax.axhline(median, color="green", linestyle="--", label="Медиана")
    ax.set_title(f"{STREAM_NAME}. {METRICS_META[metric]['title']}")
    ax.set_xlabel("Дата сопоставимого интервала")
    ax.set_ylabel("Значение")
    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()

    image = io.BytesIO()
    image.name = f"{metric}.png"
    fig.savefig(image, format="png", dpi=130)
    plt.close(fig)
    image.seek(0)
    return image


def format_alert(metric, current_ts, current_value, deviation, median, low, high):
    """Формирует самодостаточное сообщение для расследования инцидента."""
    meta = METRICS_META[metric]
    value = format(current_value, meta["format"])
    baseline_value = format(median, meta["format"])
    low_value = format(low, meta["format"])
    high_value = format(high, meta["format"])
    deviation_text = "не определено (медиана = 0)"
    if np.isfinite(deviation):
        deviation_text = f"{deviation:+.1%}"

    return (
        f"🚨 {STREAM_NAME}. Обнаружена аномалия\n"
        f"Метрика: {meta['title']}\n"
        f"Срез: {meta['group']}\n"
        f"Интервал: {current_ts}\n"
        f"Текущее значение: {value}\n"
        f"Медиана за {LOOKBACK_DAYS} сопоставимых дней: {baseline_value}\n"
        f"Отклонение: {deviation_text}\n"
        f"Ожидаемый коридор: [{low_value}; {high_value}]"
    )


def send_alert(text, image):
    """Отправляет алерт в Telegram либо печатает его в лог Airflow."""
    if BOT_TOKEN:
        bot = telegram.Bot(token=BOT_TOKEN)
        bot.send_photo(chat_id=CHAT_ID, photo=image, caption=text)
    else:
        # Нет доступа к Telegram — печатаем алерт, как разрешено заданием.
        # График в этом случае остаётся в переменной image (BytesIO).
        print(text)
        print("Telegram не настроен: график сохранён в BytesIO для этой задачи.")


@dag(
    dag_id=DAG_ID,
    default_args=default_args,
    schedule_interval="*/15 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["Карпов", "Telegram", STREAM_NAME, "alerts", "anomaly-detection"],
)
def alert_system():
    @task()
    def run_checks():
        metrics, current_ts = load_metrics()
        current_row = metrics.loc[metrics["ts"] == current_ts]
        if current_row.empty:
            raise ValueError("Не найден ожидаемый последний полный 15-минутный интервал")

        anomalies_found = 0
        for metric in METRICS_META:
            current_value = float(current_row.iloc[0][metric])
            baseline = get_same_slot_baseline(metrics, metric, current_ts)
            is_anomaly, deviation, low, high, median = check_anomaly(
                current_value, baseline[metric].values
            )
            if not is_anomaly:
                continue

            anomalies_found += 1
            text = format_alert(metric, current_ts, current_value, deviation, median, low, high)
            image = build_plot(baseline, metric, current_ts, current_value, low, high, median)
            try:
                send_alert(text, image)
            finally:
                image.close()

        if anomalies_found == 0:
            print(f"[{current_ts}] Аномалий не найдено. Проверено метрик: {len(METRICS_META)}.")
        else:
            print(f"[{current_ts}] Отправлено алертов: {anomalies_found}.")

    run_checks()


alert_system_dag = alert_system()
