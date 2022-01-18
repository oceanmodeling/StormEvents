import pandas
import pytest

from stormevents.nhc import VortexTrack
from stormevents.stormevent import StormEvent
from stormevents.usgs import StormHighWaterMarks


@pytest.fixture
def florence2018() -> StormEvent:
    return StormEvent('florence', 2018)


def test_storm_lookup():
    florence2018 = StormEvent('florence', 2018)
    paine2016 = StormEvent.from_nhc_code('EP172016')
    henri2021 = StormEvent.from_usgs_id(310)

    with pytest.raises(ValueError):
        StormEvent('nonexistent', 2021)

    with pytest.raises(ValueError):
        StormEvent.from_nhc_code('nonexistent')

    with pytest.raises(ValueError):
        StormEvent.from_nhc_code('AL992021')

    with pytest.raises(ValueError):
        StormEvent.from_nhc_code(-1)

    assert paine2016.name == 'PAINE'
    assert paine2016.year == 2016
    assert paine2016.nhc_code == 'EP172016'
    assert paine2016.usgs_id is None

    assert florence2018.name == 'FLORENCE'
    assert florence2018.year == 2018
    assert florence2018.nhc_code == 'AL062018'
    assert florence2018.usgs_id == 283

    assert henri2021.name == 'HENRI'
    assert henri2021.year == 2021
    assert henri2021.nhc_code == 'AL082021'
    assert henri2021.usgs_id == 310


def test_track(florence2018):
    track = florence2018.track()

    reference_track = VortexTrack('florence2018')

    assert track == reference_track


def test_high_water_marks(florence2018):
    high_water_marks = florence2018.high_water_marks()

    reference_high_water_marks = StormHighWaterMarks(
        name=florence2018.name, year=florence2018.year
    ).data

    pandas.testing.assert_frame_equal(high_water_marks, reference_high_water_marks)
