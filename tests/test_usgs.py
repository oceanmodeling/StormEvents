# ! /usr/bin/env python

import pandas

from stormevents.usgs import usgs_highwatermark_events
from stormevents.usgs.highwatermarks import (
    EventType,
    HighWaterMarks,
    usgs_highwatermark_storms,
)
from tests import REFERENCE_DIRECTORY


def test_usgs_highwatermark_events():
    reference_directory = REFERENCE_DIRECTORY / 'test_usgs_highwatermark_events'

    events = usgs_highwatermark_events(
        event_type=EventType.HURRICANE, year=tuple(range(2003, 2020 + 1))
    )

    reference_events = pandas.read_csv(reference_directory / 'events.csv', index_col='usgs_id')

    pandas.testing.assert_frame_equal(events, reference_events)


def test_usgs_highwatermark_storms():
    reference_directory = REFERENCE_DIRECTORY / 'test_usgs_highwatermark_storms'

    storms = usgs_highwatermark_storms(year=tuple(range(2003, 2020 + 1)))

    reference_storms = pandas.read_csv(
        reference_directory / 'storms.csv', index_col='usgs_id', na_values=''
    )

    pandas.testing.assert_frame_equal(storms, reference_storms)


def test_HurricaneHighWaterMarks():
    reference_directory = REFERENCE_DIRECTORY / 'test_StormHighWaterMarks'

    hwm_florence2018 = HighWaterMarks.from_csv(reference_directory / 'florence2018.csv')

    reference_hwm = pandas.read_csv(
        reference_directory / 'florence2018.csv', index_col='hwm_id'
    )

    pandas.testing.assert_frame_equal(hwm_florence2018.data, reference_hwm)
