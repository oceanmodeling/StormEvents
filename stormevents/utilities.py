from datetime import datetime, timedelta
from numbers import Number
from typing import Union

import pandas
import typepigeon


def subset_time_interval(
    start: datetime,
    end: datetime,
    subset_start: Union[datetime, timedelta] = None,
    subset_end: Union[datetime, timedelta] = None,
) -> (datetime, datetime):
    """
    constrain the given time interval to the given subset times

    :param start: start of larger time interval that will be subsetted
    :param end: end of larger time interval that will be subsetted
    :param subset_start: either an absolute date time or a relative time delta; positive time delta adds to the start time, negative time delta subtracts from the end time
    :param subset_end: either an absolute date time or a relative time delta; positive time delta adds to the start time, negative time delta subtracts from the end time
    :return: constrained time interval
    """

    if pandas.isna([start, end]).any():
        raise ValueError(f'cannot parse time interval "{start} - {end}"')

    if not isinstance(start, datetime):
        start = typepigeon.convert_value(start, datetime)
    if not isinstance(end, datetime):
        end = typepigeon.convert_value(end, datetime)

    if start > end:
        raise ValueError(f'given start time ("{start}") ' f'exceeds end time ("{end}")')

    if not pandas.isna(subset_start):
        try:
            subset_start = relative_to_time_interval(start, end, subset_start)
        except ValueError:
            subset_start = start
    else:
        subset_start = start

    if not pandas.isna(subset_end):
        try:
            subset_end = relative_to_time_interval(start, end, subset_end)
        except ValueError:
            subset_end = end
    else:
        subset_end = end

    if subset_start > subset_end:
        raise ValueError(
            f'subset start time ("{subset_start}") '
            f'exceeds subset end time ("{subset_end}")'
        )

    if start <= subset_start <= end and start <= subset_end <= end:
        return subset_start, subset_end
    else:
        raise ValueError(
            f'subsetted time interval ("{subset_start} - {subset_end}") '
            f'exceeds existing time interval ("{start} - {end}")'
        )


def relative_to_time_interval(
    start: datetime, end: datetime, relative: Union[datetime, timedelta],
) -> datetime:
    """
    return the absolute time relative to the time interval

    :param start: start of time interval
    :param end: end of time interval
    :param relative: either an absolute date time or a relative time delta; positive time delta adds to the start time, negative time delta subtracts from the end time
    :return: absolute datetime relative to the time interval
    """

    if pandas.isna([start, end, relative]).any():
        raise ValueError(
            f'cannot parse time interval "{start} - {end}" ir relative time "{relative}"'
        )

    if not isinstance(start, datetime):
        start = typepigeon.convert_value(start, datetime)
    if not isinstance(end, datetime):
        end = typepigeon.convert_value(end, datetime)

    if start > end:
        raise ValueError(f'given start time ("{start}") ' f'exceeds end time ("{end}")')

    if isinstance(relative, timedelta) or isinstance(relative, Number):
        relative = typepigeon.convert_value(relative, timedelta)
        if relative >= timedelta(0):
            relative = start + relative
        else:
            relative = end + relative
    elif not isinstance(relative, datetime):
        relative = typepigeon.convert_value(relative, datetime)

    if start <= relative <= end:
        return relative
    else:
        raise ValueError(
            f'relative time "{relative}" '
            f'not within given time interval ("{start} - {end}")'
        )
