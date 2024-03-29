import sys

import pytest

from stormevents.usgs import USGS_Event
from stormevents.usgs import usgs_flood_events
from stormevents.usgs import usgs_flood_storms
from stormevents.usgs import USGS_StormEvent
from stormevents.usgs.base import EventStatus
from stormevents.usgs.base import EventType
from stormevents.usgs.highwatermarks import HighWaterMarksQuery
from tests import check_reference_directory
from tests import INPUT_DIRECTORY
from tests import OUTPUT_DIRECTORY
from tests import REFERENCE_DIRECTORY


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="difference in datetime format before Python 3.10",
)
def test_usgs_flood_events():
    reference_directory = REFERENCE_DIRECTORY / "test_usgs_flood_events"
    output_directory = OUTPUT_DIRECTORY / "test_usgs_flood_events"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    usgs_flood_events(event_status=EventStatus.COMPLETED)

    events = usgs_flood_events(
        year=tuple(range(2003, 2020 + 1)),
        event_type=EventType.HURRICANE,
        event_status=EventStatus.COMPLETED,
    )

    events.to_csv(output_directory / "events.csv")

    check_reference_directory(output_directory, reference_directory)


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="difference in datetime format before Python 3.10",
)
def test_usgs_flood_storms():
    reference_directory = REFERENCE_DIRECTORY / "test_usgs_flood_storms"
    output_directory = OUTPUT_DIRECTORY / "test_usgs_flood_storms"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    storms = usgs_flood_storms(year=tuple(range(2003, 2020 + 1)))

    storms.to_csv(output_directory / "storms.csv")

    check_reference_directory(output_directory, reference_directory)


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="difference in datetime format before Python 3.10",
)
def test_usgs_flood_event():
    input_directory = INPUT_DIRECTORY / "test_usgs_flood_event"
    reference_directory = REFERENCE_DIRECTORY / "test_usgs_flood_event"
    output_directory = OUTPUT_DIRECTORY / "test_usgs_flood_event"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    flood_1 = USGS_Event.from_csv(input_directory / "florence2018.csv")
    flood_2 = USGS_Event.from_name("2017 Irma")

    with pytest.raises(ValueError):
        USGS_StormEvent.from_name("nonexistent")

    assert flood_2.high_water_marks().shape == (506, 53)
    assert flood_1 != flood_2
    flood_1.high_water_marks().to_csv(output_directory / "florence2018.csv")

    check_reference_directory(output_directory, reference_directory)


def test_usgs_high_water_marks_query():
    query_1 = HighWaterMarksQuery(182)
    query_2 = HighWaterMarksQuery(23, quality="EXCELLENT")
    query_3 = HighWaterMarksQuery("nonexistent")

    assert len(query_1.data) == 506
    assert len(query_2.data) == 148

    with pytest.raises(ValueError):
        query_3.data

    query_1.quality = "EXCELLENT", "GOOD"
    query_2.quality = "EXCELLENT", "GOOD"
    query_3.quality = "EXCELLENT", "GOOD"

    assert len(query_1.data) == 277
    assert len(query_2.data) == 628

    with pytest.raises(ValueError):
        query_3.data

    query_3.event_id = 189

    assert len(query_3.data) == 116
