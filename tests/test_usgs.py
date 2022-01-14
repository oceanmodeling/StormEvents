# ! /usr/bin/env python

import pandas

from stormevents import usgs_highwatermark_storms
from stormevents.usgs import usgs_highwatermark_events
from stormevents.usgs.highwatermarks import EventType, HighWaterMarks
from tests import REFERENCE_DIRECTORY


def test_usgs_highwatermark_events():
    reference_directory = REFERENCE_DIRECTORY / 'test_usgs_highwatermark_events'

    events = usgs_highwatermark_events(
        event_type=EventType.HURRICANE, year=tuple(range(2003, 2020 + 1))
    )

    reference_events = pandas.read_csv(reference_directory / 'events.csv', index_col='usgs_id')

    assert events.equals(reference_events)


def test_usgs_highwatermark_storms():
    reference_directory = REFERENCE_DIRECTORY / 'test_usgs_highwatermark_storms'

    storms = usgs_highwatermark_storms(year=tuple(range(2003, 2020 + 1)))

    reference_storms = pandas.read_csv(reference_directory / 'storms.csv', index_col='usgs_id')

    assert storms.equals(reference_storms)


def test_HurricaneHighWaterMarks():
    reference_directory = REFERENCE_DIRECTORY / 'test_HurricaneHighWaterMarks'

    hwm_florence2018 = HighWaterMarks.from_csv(reference_directory / 'florence2018.csv')

    reference_hwm = pandas.read_csv(
        reference_directory / 'florence2018.csv', index_col='hwm_id'
    )

    assert hwm_florence2018.data.equals(reference_hwm)
