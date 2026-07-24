import numpy as np
import pandas as pd
import pytest

from src.retention import calculate_retention


def unix(date: str) -> int:
    return int(pd.Timestamp(date, tz="UTC").timestamp())


@pytest.fixture
def sample_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    registrations = pd.DataFrame(
        {
            "reg_ts": [unix("2024-01-01"), unix("2024-01-01"), unix("2024-01-02")],
            "uid": [1, 2, 3],
        }
    )
    authorizations = pd.DataFrame(
        {
            "auth_ts": [
                unix("2024-01-01"),
                unix("2024-01-02"),
                unix("2024-01-03"),
                unix("2024-01-01"),
                unix("2024-01-03"),
                unix("2024-01-02"),
                unix("2024-01-03"),
            ],
            "uid": [1, 1, 1, 2, 2, 3, 3],
        }
    )
    return registrations, authorizations


def test_retention_values_and_percent_scale(sample_data):
    registrations, authorizations = sample_data
    result = calculate_retention(
        registrations, authorizations, max_days=2, as_percent=True
    )

    assert result.loc[pd.Timestamp("2024-01-01"), 0] == 100.0
    assert result.loc[pd.Timestamp("2024-01-01"), 1] == 50.0
    assert result.loc[pd.Timestamp("2024-01-01"), 2] == 100.0
    assert result.loc[pd.Timestamp("2024-01-02"), 1] == 100.0


def test_incomplete_lifetime_is_masked(sample_data):
    registrations, authorizations = sample_data
    result = calculate_retention(registrations, authorizations, max_days=2)

    assert np.isnan(result.loc[pd.Timestamp("2024-01-02"), 2])


def test_cohort_date_filter(sample_data):
    registrations, authorizations = sample_data
    result = calculate_retention(
        registrations,
        authorizations,
        start_date="2024-01-02",
        end_date="2024-01-02",
        max_days=1,
    )

    assert list(result.index) == [pd.Timestamp("2024-01-02")]


def test_inputs_are_not_mutated(sample_data):
    registrations, authorizations = sample_data
    original_registrations = registrations.copy(deep=True)
    original_authorizations = authorizations.copy(deep=True)

    calculate_retention(registrations, authorizations, max_days=1)

    pd.testing.assert_frame_equal(registrations, original_registrations)
    pd.testing.assert_frame_equal(authorizations, original_authorizations)


def test_duplicate_registration_is_rejected(sample_data):
    registrations, authorizations = sample_data
    duplicated = pd.concat([registrations, registrations.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="ровно один раз"):
        calculate_retention(duplicated, authorizations)
