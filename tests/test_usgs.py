import sys

import pytest

from stormevents.usgs.highwatermarks import (
    EventStatus,
    EventType,
    FloodEventHighWaterMarks,
    HighWaterMarksQuery,
    StormHighWaterMarks,
    usgs_highwatermark_events,
    usgs_highwatermark_storms,
)
from tests import check_reference_directory, OUTPUT_DIRECTORY, REFERENCE_DIRECTORY


def test_usgs_highwatermark_events():
    reference_directory = REFERENCE_DIRECTORY / 'test_usgs_highwatermark_events'
    output_directory = OUTPUT_DIRECTORY / 'test_usgs_highwatermark_events'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    usgs_highwatermark_events(event_status=EventStatus.COMPLETED)

    events = usgs_highwatermark_events(
        year=tuple(range(2003, 2020 + 1)),
        event_type=EventType.HURRICANE,
        event_status=EventStatus.COMPLETED,
    )

    events.to_csv(output_directory / 'events.csv')

    check_reference_directory(output_directory, reference_directory)


def test_usgs_highwatermark_storms():
    reference_directory = REFERENCE_DIRECTORY / 'test_usgs_highwatermark_storms'
    output_directory = OUTPUT_DIRECTORY / 'test_usgs_highwatermark_storms'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    storms = usgs_highwatermark_storms(year=tuple(range(2003, 2020 + 1)))

    storms.to_csv(output_directory / 'storms.csv')

    check_reference_directory(output_directory, reference_directory)


@pytest.mark.skipif(
    sys.version_info < (3, 10), reason='floating point differences before python 3.10',
)
def test_FloodEventHighWaterMarks():
    reference_directory = REFERENCE_DIRECTORY / 'test_FloodEventHighWaterMarks'
    output_directory = OUTPUT_DIRECTORY / 'test_FloodEventHighWaterMarks'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    flood_1 = FloodEventHighWaterMarks.from_csv(
        reference_directory / 'florence2018.csv', 'Florence Sep 2018'
    )
    flood_2 = FloodEventHighWaterMarks.from_name('Irma September 2017')

    with pytest.raises(ValueError):
        StormHighWaterMarks.from_name('nonexistent')

    assert flood_2.data().shape == (506, 53)
    assert flood_1 != flood_2
    flood_1.data().to_csv(output_directory / 'florence2018.csv')

    check_reference_directory(output_directory, reference_directory)


def test_HighWaterMarksQuery():
    query_1 = HighWaterMarksQuery(182)
    query_2 = HighWaterMarksQuery(23, hwm_quality='EXCELLENT')
    query_3 = HighWaterMarksQuery('nonexistent')

    assert len(query_1.data) == 506
    assert len(query_2.data) == 148

    with pytest.raises(ValueError):
        query_3.data

    query_1.hwm_quality = 'EXCELLENT', 'GOOD'
    query_2.hwm_quality = 'EXCELLENT', 'GOOD'
    query_3.hwm_quality = 'EXCELLENT', 'GOOD'

    assert len(query_1.data) == 277
    assert len(query_2.data) == 628

    with pytest.raises(ValueError):
        query_3.data

    query_3.event_id = 189

    assert len(query_3.data) == 116
