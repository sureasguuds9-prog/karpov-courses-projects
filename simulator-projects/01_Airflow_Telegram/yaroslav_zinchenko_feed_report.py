"""Ежедневный Telegram-отчёт по ленте новостей, 57 поток."""

import io
import os
from datetime import datetime, timedelta

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import telegram
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from read_db.CH import Getch


DAG_ID = "jaroslav_zinchenko_rqq5838_feed_report"
SOURCE_TABLE = "simulator_20260720.feed_actions"
STREAM_NAME = "57 поток"
CHAT_ID = 1058410376
BOT_TOKEN = os.environ.get("REPORT_BOT_TOKEN")

default_args = {
    "owner": "jaroslav-zinchenko-rqq5838",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 8, 14),
}


def report_date_from_context(context):
    """Определить последний полный день для планового или ручного запуска."""
    interval_end = context.get("data_interval_end")
    if interval_end is None:
        interval_end = datetime.now()
    return (interval_end - timedelta(days=1)).date()


def build_plot(metrics):
    """Построить четыре графика и сохранить их в памяти в формате PNG."""
    sns.set_theme(style="whitegrid", palette="deep")
    figure, axes = plt.subplots(2, 2, figsize=(14, 9))
    plot_specs = [
        ("dau", "DAU — дневная аудитория", "Пользователи"),
        ("views", "Просмотры", "Количество"),
        ("likes", "Лайки", "Количество"),
        ("ctr", "CTR — доля лайков от просмотров", "%"),
    ]

    for axis, (column, title, ylabel) in zip(axes.flat, plot_specs):
        sns.lineplot(
            data=metrics,
            x="event_date",
            y=column,
            marker="o",
            linewidth=2,
            ax=axis,
        )
        axis.set_title(title, fontsize=13, fontweight="bold")
        axis.set_xlabel("")
        axis.set_ylabel(ylabel)
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        axis.tick_params(axis="x", rotation=30)
        if column == "ctr":
            axis.yaxis.set_major_formatter(lambda value, _: f"{value:.1f}%")

    start_date = metrics["event_date"].min().strftime("%d.%m.%Y")
    end_date = metrics["event_date"].max().strftime("%d.%m.%Y")
    figure.suptitle(
        f"{STREAM_NAME}. Метрики ленты за 7 дней: {start_date}–{end_date}",
        fontsize=16,
        fontweight="bold",
    )
    figure.tight_layout(rect=[0, 0, 1, 0.95])

    plot_object = io.BytesIO()
    figure.savefig(plot_object, format="png", dpi=150, bbox_inches="tight")
    plot_object.seek(0)
    plot_object.name = "feed_metrics_7_days.png"
    plt.close(figure)
    return plot_object


@dag(
    dag_id=DAG_ID,
    default_args=default_args,
    schedule_interval="0 11 * * *",
    catchup=False,
    tags=["Карпов", "Telegram", STREAM_NAME, "отчёт по ленте"],
)
def feed_report():
    @task()
    def extract_metrics():
        context = get_current_context()
        report_date = report_date_from_context(context)
        start_date = report_date - timedelta(days=6)

        query = f"""
            SELECT
                toDate(time) AS event_date,
                uniqExact(user_id) AS dau,
                countIf(action = 'view') AS views,
                countIf(action = 'like') AS likes,
                round(100.0 * likes / nullIf(views, 0), 2) AS ctr
            FROM {SOURCE_TABLE}
            WHERE toDate(time) BETWEEN toDate('{start_date}')
                                    AND toDate('{report_date}')
            GROUP BY event_date
            ORDER BY event_date
        """
        metrics = Getch(query).df
        metrics["event_date"] = pd.to_datetime(metrics["event_date"])

        expected_dates = pd.date_range(start=start_date, end=report_date, freq="D")
        actual_dates = pd.DatetimeIndex(metrics["event_date"])
        missing_dates = expected_dates.difference(actual_dates)
        if not missing_dates.empty:
            missing = ", ".join(date.strftime("%Y-%m-%d") for date in missing_dates)
            raise ValueError(f"Нет данных за даты: {missing}")

        return metrics.to_json(orient="split", date_format="iso")

    @task()
    def send_report(metrics_json):
        metrics = pd.read_json(io.StringIO(metrics_json), orient="split")
        metrics["event_date"] = pd.to_datetime(metrics["event_date"])
        yesterday = metrics.iloc[-1]

        report_date = yesterday["event_date"].strftime("%d.%m.%Y")
        message = (
            f"{STREAM_NAME}. Отчёт по ленте за {report_date}\n\n"
            f"DAU (дневная аудитория): {int(yesterday['dau']):,}\n"
            f"Просмотры: {int(yesterday['views']):,}\n"
            f"Лайки: {int(yesterday['likes']):,}\n"
            f"CTR (доля лайков от просмотров): {float(yesterday['ctr']):.2f}%"
        ).replace(",", " ")

        bot = telegram.Bot(token=BOT_TOKEN)
        bot.send_message(chat_id=CHAT_ID, text=message)
        bot.send_photo(chat_id=CHAT_ID, photo=build_plot(metrics))

    send_report(extract_metrics())


feed_report_dag = feed_report()
