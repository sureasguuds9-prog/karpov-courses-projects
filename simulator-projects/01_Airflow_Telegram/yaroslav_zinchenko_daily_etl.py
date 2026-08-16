"""Daily ETL for feed and messenger activity in the Karpov simulator.

Target table: test.yaroslav_zinchenko_daily_etl
Grain: event_date x dimension x dimension_value.
"""

from datetime import datetime, timedelta
from io import StringIO

import pandas as pd
import requests
from airflow.decorators import dag, task


DAG_ID = "jaroslav_zinchenko_rqq5838_daily_etl"
SOURCE_SCHEMA = "simulator_20260720"
FINAL_TABLE = "yaroslav_zinchenko_daily_etl"

CH_HOST = "http://clickhouse.lab.karpov.courses:8123"
CH_READ_USER = "student"
CH_READ_PASSWORD = "dpo_python_2020"
CH_WRITE_USER = "student-rw"
CH_WRITE_PASSWORD = "656e2b0c9c"

METRIC_COLUMNS = [
    "views",
    "likes",
    "messages_received",
    "messages_sent",
    "users_received",
    "users_sent",
]

default_args = {
    "owner": "jaroslav-zinchenko-rqq5838",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 8, 1),
}


def ch_query(query):
    """Run a SELECT query and return its TSV result as a DataFrame."""
    response = requests.post(
        CH_HOST,
        data=query.encode("utf-8"),
        auth=(CH_READ_USER, CH_READ_PASSWORD),
        timeout=300,
    )
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text), sep="\t")


def ch_execute(query):
    """Run a ClickHouse DDL/DML query."""
    response = requests.post(
        CH_HOST,
        data=query.encode("utf-8"),
        auth=(CH_WRITE_USER, CH_WRITE_PASSWORD),
        timeout=300,
    )
    response.raise_for_status()


def dataframe_to_tsv(dataframe):
    """Serialize a DataFrame for a compact and predictable XCom payload."""
    return dataframe.to_csv(index=False, sep="\t")


def dataframe_from_tsv(payload):
    """Restore a DataFrame passed through XCom."""
    return pd.read_csv(StringIO(payload), sep="\t")


@dag(
    dag_id=DAG_ID,
    default_args=default_args,
    schedule_interval="0 11 * * *",
    catchup=False,
    tags=["karpov", "etl", "clickhouse"],
)
def daily_activity_etl():
    @task()
    def extract_feed(processing_date):
        """Calculate daily feed views and likes for every user."""
        query = f"""
            SELECT
                toDate(time) AS event_date,
                user_id,
                any(gender) AS gender,
                any(age) AS age,
                any(os) AS os,
                countIf(action = 'view') AS views,
                countIf(action = 'like') AS likes
            FROM {SOURCE_SCHEMA}.feed_actions
            WHERE toDate(time) = toDate('{processing_date}')
            GROUP BY event_date, user_id
            FORMAT TSVWithNames
        """
        return dataframe_to_tsv(ch_query(query))

    @task()
    def extract_messages(processing_date):
        """Calculate daily sent and received message metrics per user."""
        query = f"""
            WITH
            sent AS (
                SELECT
                    toDate(time) AS event_date,
                    user_id,
                    count() AS messages_sent,
                    uniqExact(receiver_id) AS users_sent
                FROM {SOURCE_SCHEMA}.message_actions
                WHERE toDate(time) = toDate('{processing_date}')
                GROUP BY event_date, user_id
            ),
            received AS (
                SELECT
                    toDate(ma.time) AS event_date,
                    ma.receiver_id AS user_id,
                    count() AS messages_received,
                    uniqExact(ma.user_id) AS users_received
                FROM {SOURCE_SCHEMA}.message_actions AS ma
                WHERE toDate(ma.time) = toDate('{processing_date}')
                GROUP BY event_date, ma.receiver_id
            ),
            message_metrics AS (
                SELECT
                    event_date,
                    user_id,
                    received.messages_received AS messages_received,
                    sent.messages_sent AS messages_sent,
                    received.users_received AS users_received,
                    sent.users_sent AS users_sent
                FROM sent
                FULL OUTER JOIN received USING (event_date, user_id)
            ),
            profiles AS (
                SELECT
                    user_id,
                    argMax(gender, time) AS gender,
                    argMax(age, time) AS age,
                    argMax(os, time) AS os
                FROM (
                    SELECT user_id, gender, age, os, time
                    FROM {SOURCE_SCHEMA}.feed_actions
                    WHERE toDate(time) <= toDate('{processing_date}')

                    UNION ALL

                    SELECT user_id, gender, age, os, time
                    FROM {SOURCE_SCHEMA}.message_actions
                    WHERE toDate(time) <= toDate('{processing_date}')
                )
                GROUP BY user_id
            )
            SELECT
                message_metrics.event_date AS event_date,
                message_metrics.user_id AS user_id,
                profiles.gender AS gender,
                profiles.age AS age,
                profiles.os AS os,
                message_metrics.messages_received AS messages_received,
                message_metrics.messages_sent AS messages_sent,
                message_metrics.users_received AS users_received,
                message_metrics.users_sent AS users_sent
            FROM message_metrics
            LEFT JOIN profiles USING (user_id)
            FORMAT TSVWithNames
        """
        return dataframe_to_tsv(ch_query(query))

    @task()
    def merge_user_metrics(feed_tsv, messages_tsv):
        """Combine feed and messenger data at user-day grain."""
        feed = dataframe_from_tsv(feed_tsv)
        messages = dataframe_from_tsv(messages_tsv)

        merged = feed.merge(
            messages,
            how="outer",
            on=["event_date", "user_id"],
            suffixes=("_feed", "_message"),
        )

        for column in ["gender", "age", "os"]:
            merged[column] = merged[f"{column}_feed"].combine_first(
                merged[f"{column}_message"]
            )

        merged[METRIC_COLUMNS] = merged[METRIC_COLUMNS].fillna(0).astype("int64")

        missing_profile = merged[["gender", "age", "os"]].isna().any(axis=1)
        if missing_profile.any():
            raise ValueError(
                "No gender, age or OS profile for "
                f"{int(missing_profile.sum())} users"
            )

        columns = [
            "event_date",
            "user_id",
            "gender",
            "age",
            "os",
            *METRIC_COLUMNS,
        ]
        return dataframe_to_tsv(merged[columns])

    def aggregate_dimension(user_metrics_tsv, dimension):
        data = dataframe_from_tsv(user_metrics_tsv)
        result = data.groupby(["event_date", dimension], as_index=False)[
            METRIC_COLUMNS
        ].sum()
        result.insert(1, "dimension", dimension)
        result = result.rename(columns={dimension: "dimension_value"})
        result["dimension_value"] = result["dimension_value"].astype(str)
        return dataframe_to_tsv(result)

    @task()
    def aggregate_by_gender(user_metrics_tsv):
        return aggregate_dimension(user_metrics_tsv, "gender")

    @task()
    def aggregate_by_age(user_metrics_tsv):
        return aggregate_dimension(user_metrics_tsv, "age")

    @task()
    def aggregate_by_os(user_metrics_tsv):
        return aggregate_dimension(user_metrics_tsv, "os")

    @task()
    def load_to_clickhouse(gender_tsv, age_tsv, os_tsv, processing_date):
        """Create the target and replace only the processed daily partition."""
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS test.{FINAL_TABLE} (
                event_date Date,
                dimension String,
                dimension_value String,
                views UInt64,
                likes UInt64,
                messages_received UInt64,
                messages_sent UInt64,
                users_received UInt64,
                users_sent UInt64
            )
            ENGINE = MergeTree
            PARTITION BY toYYYYMM(event_date)
            ORDER BY (event_date, dimension, dimension_value)
        """
        ch_execute(create_table_query)

        # Makes manual retries safe: a date can exist in the table only once.
        delete_date_query = f"""
            ALTER TABLE test.{FINAL_TABLE}
            DELETE WHERE event_date = toDate('{processing_date}')
            SETTINGS mutations_sync = 2
        """
        ch_execute(delete_date_query)

        result = pd.concat(
            [
                dataframe_from_tsv(gender_tsv),
                dataframe_from_tsv(age_tsv),
                dataframe_from_tsv(os_tsv),
            ],
            ignore_index=True,
        )
        result = result[
            ["event_date", "dimension", "dimension_value", *METRIC_COLUMNS]
        ]

        insert_query = (
            f"INSERT INTO test.{FINAL_TABLE} "
            "FORMAT TSVWithNames\n"
            + result.to_csv(index=False, sep="\t")
        )
        ch_execute(insert_query)

    # For a daily schedule Airflow's logical date represents the previous
    # completed data interval, so {{ ds }} is the day that must be processed.
    processing_date = "{{ ds }}"

    feed_tsv = extract_feed(processing_date)
    messages_tsv = extract_messages(processing_date)
    user_metrics_tsv = merge_user_metrics(feed_tsv, messages_tsv)

    gender_tsv = aggregate_by_gender(user_metrics_tsv)
    age_tsv = aggregate_by_age(user_metrics_tsv)
    os_tsv = aggregate_by_os(user_metrics_tsv)

    load_to_clickhouse(
        gender_tsv,
        age_tsv,
        os_tsv,
        processing_date,
    )


daily_activity_etl_dag = daily_activity_etl()
