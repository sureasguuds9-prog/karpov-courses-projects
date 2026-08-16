"""Ежедневный Telegram-отчёт о работе всего приложения, 57 поток."""

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


DAG_ID = "jaroslav_zinchenko_rqq5838_app_report"
SOURCE_SCHEMA = "simulator_20260720"
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


def percent_change(current, previous):
    """Посчитать изменение к предыдущему дню в процентах."""
    if previous == 0:
        return None
    return 100.0 * (current - previous) / previous


def change_label(current, previous):
    """Подготовить короткую подпись изменения к предыдущему дню."""
    change = percent_change(current, previous)
    if change is None:
        return "нет базы для сравнения"
    return f"{change:+.1f}% к предыдущему дню"


def business_signals(current, previous):
    """Сформировать осторожные бизнес-сигналы без причинных утверждений."""
    audience_change = percent_change(current["app_dau"], previous["app_dau"])
    message_change = percent_change(
        current["messages_per_sender"], previous["messages_per_sender"]
    )
    ctr_change = current["ctr"] - previous["ctr"]
    overlap_change = current["overlap_share"] - previous["overlap_share"]

    if audience_change is None or abs(audience_change) < 1:
        audience_signal = "общая дневная аудитория остаётся стабильной"
    elif audience_change > 0:
        audience_signal = f"общая дневная аудитория выросла на {audience_change:.1f}%"
    else:
        audience_signal = f"общая дневная аудитория снизилась на {abs(audience_change):.1f}%"

    if abs(ctr_change) < 0.1:
        feed_signal = "CTR ленты практически не изменился"
    elif ctr_change > 0:
        feed_signal = f"CTR ленты вырос на {ctr_change:.2f} п.п."
    else:
        feed_signal = f"CTR ленты снизился на {abs(ctr_change):.2f} п.п."

    if message_change is None or abs(message_change) < 1:
        messenger_signal = "число сообщений на отправителя стабильно"
    elif message_change > 0:
        messenger_signal = (
            f"число сообщений на отправителя выросло на {message_change:.1f}%"
        )
    else:
        messenger_signal = (
            f"число сообщений на отправителя снизилось на {abs(message_change):.1f}%"
        )

    overlap_direction = "выросла" if overlap_change >= 0 else "снизилась"
    overlap_signal = (
        f"доля пользователей обеих частей {overlap_direction} "
        f"на {abs(overlap_change):.2f} п.п."
    )
    return audience_signal, feed_signal, messenger_signal, overlap_signal


def build_plot(metrics):
    """Построить графики аудитории и активности за семь дней."""
    sns.set_theme(style="whitegrid", palette="deep")
    figure, axes = plt.subplots(3, 2, figsize=(15, 14))
    dates = metrics["event_date"]

    audience_axis = axes[0, 0]
    for column, title in [
        ("app_dau", "Всё приложение"),
        ("feed_dau", "Лента"),
        ("messenger_dau", "Мессенджер"),
    ]:
        sns.lineplot(
            data=metrics,
            x="event_date",
            y=column,
            marker="o",
            linewidth=2,
            label=title,
            ax=audience_axis,
        )
    audience_axis.set_title("Динамика дневной аудитории")
    audience_axis.set_ylabel("Пользователи")

    composition_axis = axes[0, 1]
    composition_axis.stackplot(
        dates,
        metrics["feed_only_dau"],
        metrics["messenger_only_dau"],
        metrics["both_dau"],
        labels=["Только лента", "Только мессенджер", "Обе части"],
        alpha=0.85,
    )
    composition_axis.set_title("Состав аудитории приложения")
    composition_axis.set_ylabel("Пользователи")
    composition_axis.legend(loc="upper left")

    chart_specs = [
        (axes[1, 0], "views", "Просмотры ленты", "Количество"),
        (axes[1, 1], "likes", "Лайки в ленте", "Количество"),
        (axes[2, 0], "ctr", "CTR — доля лайков от просмотров", "%"),
        (axes[2, 1], "messages", "Отправленные сообщения", "Количество"),
    ]
    for axis, column, title, ylabel in chart_specs:
        sns.lineplot(
            data=metrics,
            x="event_date",
            y=column,
            marker="o",
            linewidth=2,
            ax=axis,
        )
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        if column == "ctr":
            axis.yaxis.set_major_formatter(lambda value, _: f"{value:.1f}%")

    for axis in axes.flat:
        axis.set_xlabel("")
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        axis.tick_params(axis="x", rotation=30)

    start_date = metrics["event_date"].min().strftime("%d.%m.%Y")
    end_date = metrics["event_date"].max().strftime("%d.%m.%Y")
    figure.suptitle(
        f"{STREAM_NAME}. Работа приложения за 7 дней: {start_date}–{end_date}",
        fontsize=17,
        fontweight="bold",
    )
    figure.tight_layout(rect=[0, 0, 1, 0.97])

    plot_object = io.BytesIO()
    figure.savefig(plot_object, format="png", dpi=150, bbox_inches="tight")
    plot_object.seek(0)
    plot_object.name = "метрики_приложения_7_дней.png"
    plt.close(figure)
    return plot_object


def build_csv(metrics):
    """Подготовить подробную таблицу метрик для самостоятельного анализа."""
    column_names = {
        "event_date": "дата",
        "app_dau": "дневная_аудитория_приложения",
        "feed_dau": "дневная_аудитория_ленты",
        "messenger_dau": "отправители_в_мессенджере",
        "both_dau": "пользователи_обеих_частей",
        "feed_only_dau": "только_лента",
        "messenger_only_dau": "только_мессенджер",
        "views": "просмотры",
        "likes": "лайки",
        "ctr": "ctr_проценты",
        "messages": "сообщения",
        "actions_per_user": "действия_на_пользователя",
        "messages_per_sender": "сообщения_на_отправителя",
        "overlap_share": "доля_пользователей_обеих_частей_проценты",
    }
    export = metrics.rename(columns=column_names).copy()
    export["дата"] = export["дата"].dt.strftime("%Y-%m-%d")

    csv_object = io.BytesIO(export.to_csv(index=False, sep=";").encode("utf-8-sig"))
    csv_object.name = "метрики_приложения_7_дней.csv"
    return csv_object


@dag(
    dag_id=DAG_ID,
    default_args=default_args,
    schedule_interval="0 11 * * *",
    catchup=False,
    tags=["Карпов", "Telegram", STREAM_NAME, "всё приложение"],
)
def app_report():
    @task()
    def extract_metrics():
        context = get_current_context()
        report_date = report_date_from_context(context)
        start_date = report_date - timedelta(days=6)

        query = f"""
            WITH
            raw_user_daily AS (
                SELECT
                    toDate(time) AS event_date,
                    user_id,
                    countIf(action = 'view') AS feed_views_raw,
                    countIf(action = 'like') AS feed_likes_raw,
                    toUInt64(0) AS sent_messages_raw
                FROM {SOURCE_SCHEMA}.feed_actions
                WHERE toDate(time) BETWEEN toDate('{start_date}')
                                        AND toDate('{report_date}')
                GROUP BY event_date, user_id

                UNION ALL

                SELECT
                    toDate(time) AS event_date,
                    user_id,
                    toUInt64(0) AS feed_views_raw,
                    toUInt64(0) AS feed_likes_raw,
                    count() AS sent_messages_raw
                FROM {SOURCE_SCHEMA}.message_actions
                WHERE toDate(time) BETWEEN toDate('{start_date}')
                                        AND toDate('{report_date}')
                GROUP BY event_date, user_id
            ),
            user_daily AS (
                SELECT
                    event_date,
                    user_id,
                    sum(feed_views_raw) AS user_views,
                    sum(feed_likes_raw) AS user_likes,
                    sum(sent_messages_raw) AS user_messages
                FROM raw_user_daily
                GROUP BY event_date, user_id
            ),
            daily_metrics AS (
                SELECT
                    event_date,
                    uniqExact(user_id) AS total_app_dau,
                    uniqExactIf(
                        user_id,
                        user_views + user_likes > 0
                    ) AS total_feed_dau,
                    uniqExactIf(user_id, user_messages > 0)
                        AS total_messenger_dau,
                    uniqExactIf(
                        user_id,
                        user_views + user_likes > 0 AND user_messages > 0
                    ) AS total_both_dau,
                    sum(user_views) AS total_views,
                    sum(user_likes) AS total_likes,
                    sum(user_messages) AS total_messages
                FROM user_daily
                GROUP BY event_date
            )
            SELECT
                event_date,
                total_app_dau AS app_dau,
                total_feed_dau AS feed_dau,
                total_messenger_dau AS messenger_dau,
                total_both_dau AS both_dau,
                total_feed_dau - total_both_dau AS feed_only_dau,
                total_messenger_dau - total_both_dau AS messenger_only_dau,
                total_views AS views,
                total_likes AS likes,
                round(100.0 * total_likes / nullIf(total_views, 0), 2) AS ctr,
                total_messages AS messages,
                round(
                    (total_views + total_likes + total_messages)
                    / nullIf(total_app_dau, 0),
                    2
                )
                    AS actions_per_user,
                round(total_messages / nullIf(total_messenger_dau, 0), 2)
                    AS messages_per_sender,
                round(100.0 * total_both_dau / nullIf(total_app_dau, 0), 2)
                    AS overlap_share
            FROM daily_metrics
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
        current = metrics.iloc[-1]
        previous = metrics.iloc[-2]
        signals = business_signals(current, previous)

        report_date = current["event_date"].strftime("%d.%m.%Y")
        message = (
            f"{STREAM_NAME}. Отчёт по всему приложению за {report_date}\n\n"
            f"ПРИЛОЖЕНИЕ ЦЕЛИКОМ\n"
            f"Дневная аудитория: {int(current['app_dau']):,} "
            f"({change_label(current['app_dau'], previous['app_dau'])})\n"
            f"Действий на пользователя: {float(current['actions_per_user']):.2f}\n\n"
            f"АУДИТОРИЯ ПО ЧАСТЯМ\n"
            f"Лента: {int(current['feed_dau']):,}\n"
            f"Мессенджер, отправители: {int(current['messenger_dau']):,}\n"
            f"Обе части: {int(current['both_dau']):,} "
            f"({float(current['overlap_share']):.2f}% общей аудитории)\n\n"
            f"ЛЕНТА НОВОСТЕЙ\n"
            f"Просмотры: {int(current['views']):,}\n"
            f"Лайки: {int(current['likes']):,}\n"
            f"CTR, доля лайков от просмотров: {float(current['ctr']):.2f}%\n\n"
            f"МЕССЕНДЖЕР\n"
            f"Отправленные сообщения: {int(current['messages']):,}\n"
            f"Сообщений на отправителя: "
            f"{float(current['messages_per_sender']):.2f}\n\n"
            f"БИЗНЕС-СИГНАЛЫ\n"
            f"• {signals[0]}.\n"
            f"• {signals[1]}.\n"
            f"• {signals[2]}.\n"
            f"• {signals[3]}."
        ).replace(",", " ")

        bot = telegram.Bot(token=BOT_TOKEN)
        bot.send_message(chat_id=CHAT_ID, text=message)
        bot.send_photo(chat_id=CHAT_ID, photo=build_plot(metrics))
        bot.send_document(chat_id=CHAT_ID, document=build_csv(metrics))

    send_report(extract_metrics())


app_report_dag = app_report()
