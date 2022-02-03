from datetime import datetime, timedelta

import numpy
import pytest

from stormevents.utilities import relative_to_time_interval, subset_time_interval


def test_subset_time_interval():
    interval_1 = subset_time_interval(
        datetime(2020, 1, 1),
        datetime(2021, 1, 1),
        datetime(2020, 2, 1),
        datetime(2020, 11, 1),
    )
    interval_2 = subset_time_interval('2020-01-01', '2021-01-01', '2020-02-01', '2020-11-01')
    interval_3 = subset_time_interval(
        '2020-01-01', '2021-01-01', '2020-02-01', -1 * 31 * 24 * 60 * 60
    )

    with pytest.raises(ValueError):
        subset_time_interval('2021-01-01', '2020-01-01', '2020-02-01', '2020-11-01')

    with pytest.raises(ValueError):
        subset_time_interval('2020-01-01', '2021-01-01', '2020-11-01', '2020-02-01')

    with pytest.raises(ValueError):
        subset_time_interval(None, '2021-01-01', '2020-02-01', '2020-11-01')

    with pytest.raises(ValueError):
        subset_time_interval('2020-01-01', numpy.nan, '2020-02-01', '2020-11-01')

    assert interval_1 == (datetime(2020, 2, 1), datetime(2020, 11, 1))
    assert interval_2 == (datetime(2020, 2, 1), datetime(2020, 11, 1))
    assert interval_3 == (datetime(2020, 2, 1), datetime(2020, 12, 1))


def test_relative_to_time_interval():
    time_1 = relative_to_time_interval(
        datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2020, 2, 1),
    )
    time_2 = relative_to_time_interval('2020-01-01', '2021-01-01', '2020-02-01')
    time_3 = relative_to_time_interval('2020-01-01', '2021-01-01', timedelta(days=30 * 3))
    time_4 = relative_to_time_interval('2020-01-01', '2021-01-01', 5 * 24 * 60 * 60)

    with pytest.raises(ValueError):
        relative_to_time_interval('2021-01-01', '2020-01-01', '2020-02-01')

    with pytest.raises(ValueError):
        relative_to_time_interval('2021-01-01', '2020-01-01', '2020-02-01')

    with pytest.raises(ValueError):
        relative_to_time_interval('2020-01-01', '2021-01-01', '2021-02-01')

    with pytest.raises(ValueError):
        relative_to_time_interval('2020-01-01', '2021-01-01', None)

    with pytest.raises(ValueError):
        relative_to_time_interval(numpy.nan, '2021-01-01', '2020-02-01')

    assert time_1 == datetime(2020, 2, 1)
    assert time_2 == datetime(2020, 2, 1)
    assert time_3 == datetime(2020, 3, 31)
    assert time_4 == datetime(2020, 1, 6)
