"""Cohort retention calculation for mobile-game players."""

from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

import numpy as np
import pandas as pd


FrameLike: TypeAlias = pd.DataFrame | str | Path


def _load_data(data: FrameLike, required_columns: set[str]) -> pd.DataFrame:
    """Return a defensive DataFrame copy and validate its schema."""
    if isinstance(data, pd.DataFrame):
        frame = data.copy()
    else:
        frame = pd.read_csv(data, sep=";", usecols=list(required_columns))

    missing = required_columns.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"В данных отсутствуют обязательные столбцы: {missing_text}")
    return frame.loc[:, sorted(required_columns)].copy()


def _to_utc_date(values: pd.Series, column_name: str) -> pd.Series:
    """Convert Unix seconds to naive UTC calendar dates."""
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.isna().any():
        raise ValueError(f"Столбец {column_name} содержит пустые или нечисловые значения")
    return pd.to_datetime(numeric, unit="s", utc=True).dt.tz_convert(None).dt.normalize()


def calculate_retention(
    reg_data: FrameLike,
    auth_data: FrameLike,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
    max_days: int = 14,
    *,
    as_percent: bool = False,
    mask_incomplete: bool = True,
) -> pd.DataFrame:
    """Calculate classic day-N retention by registration cohort.

    Parameters
    ----------
    reg_data:
        DataFrame or path to a semicolon-separated file with ``reg_ts`` and ``uid``.
    auth_data:
        DataFrame or path to a semicolon-separated file with ``auth_ts`` and ``uid``.
    start_date, end_date:
        Optional inclusive cohort boundaries. Dates use ``YYYY-MM-DD`` format.
    max_days:
        Maximum lifetime day shown in the result. Day 0 is included.
    as_percent:
        Return values on a 0–100 scale instead of shares on a 0–1 scale.
    mask_incomplete:
        Replace cells not yet observable by ``NaN`` to prevent right-censoring from
        being mistaken for zero retention.

    Returns
    -------
    pandas.DataFrame
        Rows are registration dates, columns are lifetime days, and values are the
        share (or percentage) of cohort users active on exactly that day.
    """
    if not isinstance(max_days, int) or max_days < 0:
        raise ValueError("max_days должен быть целым неотрицательным числом")

    registrations = _load_data(reg_data, {"reg_ts", "uid"})
    authorizations = _load_data(auth_data, {"auth_ts", "uid"})

    if registrations["uid"].isna().any() or authorizations["uid"].isna().any():
        raise ValueError("uid не должен содержать пропуски")
    if registrations["uid"].duplicated().any():
        raise ValueError("В таблице регистраций uid должен встречаться ровно один раз")

    registrations["cohort_date"] = _to_utc_date(registrations["reg_ts"], "reg_ts")
    authorizations["auth_date"] = _to_utc_date(authorizations["auth_ts"], "auth_ts")

    if start_date is not None:
        start = pd.Timestamp(start_date).normalize()
        registrations = registrations.loc[registrations["cohort_date"] >= start]
    if end_date is not None:
        end = pd.Timestamp(end_date).normalize()
        registrations = registrations.loc[registrations["cohort_date"] <= end]

    if registrations.empty:
        raise ValueError("После фильтрации не осталось регистрационных когорт")

    cohorts = registrations.loc[:, ["uid", "cohort_date"]]
    cohort_sizes = cohorts.groupby("cohort_date", sort=True)["uid"].nunique()

    activity = authorizations.merge(cohorts, on="uid", how="inner", validate="many_to_one")
    activity["lifetime_day"] = (activity["auth_date"] - activity["cohort_date"]).dt.days
    activity = activity.loc[activity["lifetime_day"].between(0, max_days)]

    lifetime_columns = pd.RangeIndex(max_days + 1, name="lifetime_day")
    active_users = (
        activity.groupby(["cohort_date", "lifetime_day"], observed=True)["uid"]
        .nunique()
        .unstack(fill_value=0)
        .reindex(index=cohort_sizes.index, columns=lifetime_columns, fill_value=0)
    )
    retention = active_users.div(cohort_sizes, axis="index")

    observation_end = authorizations["auth_date"].max()
    if mask_incomplete and pd.notna(observation_end):
        for day in lifetime_columns:
            unavailable = retention.index + pd.to_timedelta(day, unit="D") > observation_end
            retention.loc[unavailable, day] = np.nan

    if as_percent:
        retention = retention.mul(100)

    retention.index.name = "cohort_date"
    retention.attrs["cohort_sizes"] = cohort_sizes
    retention.attrs["active_users"] = active_users
    retention.attrs["observation_end"] = observation_end
    retention.attrs["scale"] = "percent" if as_percent else "share"
    return retention
