from datetime import datetime, timedelta

import pandas
import pytest

from stormevents.nhc import VortexTrack
from stormevents.stormevent import StormEvent
from stormevents.usgs import StormHighWaterMarks


@pytest.fixture
def florence2018() -> StormEvent:
    return StormEvent('florence', 2018)


@pytest.fixture
def ida2021() -> StormEvent:
    return StormEvent('florence', 2018)


def test_storm_lookup():
    florence2018 = StormEvent('florence', 2018)
    paine2016 = StormEvent.from_nhc_code('EP172016')
    henri2021 = StormEvent.from_usgs_id(310)
    ida2021 = StormEvent('ida', 2021)

    with pytest.raises(ValueError):
        StormEvent('nonexistent', 2021)

    with pytest.raises(ValueError):
        StormEvent.from_nhc_code('nonexistent')

    with pytest.raises(ValueError):
        StormEvent.from_nhc_code('AL992021')

    with pytest.raises(ValueError):
        StormEvent.from_nhc_code(-1)

    with pytest.raises(ValueError):
        StormEvent.from_usgs_id(-1)

    assert florence2018.name == 'FLORENCE'
    assert florence2018.year == 2018
    assert florence2018.basin == 'AL'
    assert florence2018.number == 6
    assert florence2018._StormEvent__data_start == datetime(2018, 8, 30, 6)
    assert florence2018.nhc_code == 'AL062018'
    assert florence2018.usgs_id == 283
    assert florence2018.start_date == datetime(2018, 8, 30, 6)
    assert florence2018.end_date == datetime(2018, 9, 18, 12)
    assert repr(florence2018) == "StormEvent('FLORENCE', 2018)"

    assert paine2016.name == 'PAINE'
    assert paine2016.year == 2016
    assert paine2016.nhc_code == 'EP172016'
    assert paine2016.usgs_id is None
    assert paine2016.start_date == datetime(2016, 9, 18)
    assert paine2016.end_date == datetime(2016, 9, 21, 12)

    assert henri2021.name == 'HENRI'
    assert henri2021.year == 2021
    assert henri2021.nhc_code == 'AL082021'
    assert henri2021.usgs_id == 310
    assert henri2021.start_date == datetime(2021, 8, 20, 18)
    assert henri2021.end_date == datetime(2021, 8, 27, 18)

    assert ida2021.name == 'IDA'
    assert ida2021.year == 2021
    assert ida2021.nhc_code == 'AL092021'
    assert ida2021.usgs_id == 312
    assert ida2021.start_date == datetime(2021, 8, 27, 18)
    assert ida2021.end_date == datetime(2021, 9, 4, 6)


def test_time_interval():
    florence2018 = StormEvent('florence', 2018, start_date=timedelta(days=-2))
    paine2016 = StormEvent.from_nhc_code('EP172016', end_date=timedelta(days=1))
    henri2021 = StormEvent.from_usgs_id(
        310, start_date=timedelta(days=-4), end_date=timedelta(days=-2)
    )
    ida2021 = StormEvent(
        'ida', 2021, start_date=datetime(2021, 8, 30), end_date=datetime(2021, 9, 1)
    )

    with pytest.raises(ValueError):
        StormEvent('florence', 2018, start_date=timedelta(days=30))

    with pytest.raises(ValueError):
        StormEvent('florence', 2018, start_date=datetime(2018, 10, 1))

    assert florence2018.start_date == datetime(2018, 9, 16, 12)
    assert florence2018.end_date == datetime(2018, 9, 18, 12)
    assert (
        repr(florence2018) == "StormEvent('FLORENCE', 2018, start_date='2018-09-16 12:00:00')"
    )

    assert paine2016.start_date == datetime(2016, 9, 18)
    assert paine2016.end_date == datetime(2016, 9, 19)
    assert repr(paine2016) == "StormEvent('PAINE', 2016, end_date='2016-09-19 00:00:00')"

    assert henri2021.start_date == datetime(2021, 8, 23, 18)
    assert henri2021.end_date == datetime(2021, 8, 25, 18)
    assert (
        repr(henri2021)
        == "StormEvent('HENRI', 2021, start_date='2021-08-23 18:00:00', end_date='2021-08-25 18:00:00')"
    )

    assert ida2021.start_date == datetime(2021, 8, 30)
    assert ida2021.end_date == datetime(2021, 9, 1)
    assert (
        repr(ida2021)
        == "StormEvent('IDA', 2021, start_date='2021-08-30 00:00:00', end_date='2021-09-01 00:00:00')"
    )


def test_track(florence2018, ida2021):
    florence_track = florence2018.track()
    ida_track = ida2021.track()

    florence_reference_track = VortexTrack.from_storm_name(
        florence2018.name,
        florence2018.year,
        start_date=florence2018.start_date,
        end_date=florence2018.end_date,
    )
    ida_reference_track = VortexTrack.from_storm_name(
        ida2021.name, ida2021.year, start_date=ida2021.start_date, end_date=ida2021.end_date
    )

    pandas.testing.assert_frame_equal(florence_track.data, florence_reference_track.data)
    pandas.testing.assert_frame_equal(ida_track.data, ida_reference_track.data)

    assert florence_track == florence_reference_track
    assert ida_track == ida_reference_track


def test_high_water_marks(florence2018):
    high_water_marks = florence2018.high_water_marks

    reference_high_water_marks = StormHighWaterMarks(
        name=florence2018.name, year=florence2018.year
    ).data

    pandas.testing.assert_frame_equal(high_water_marks, reference_high_water_marks)


def test_tidal_data_within_isotach(florence2018):
    null_data = florence2018.tidal_data_within_isotach(34, end_date=timedelta(hours=12))

    tidal_data = florence2018.tidal_data_within_isotach(
        34, start_date=datetime(2018, 9, 13, 23), end_date=datetime(2018, 9, 14)
    )

    assert null_data['t'].sizes == {}

    assert list(tidal_data.data_vars) == ['v', 's', 'f', 'q']
    assert tidal_data.sizes == {'t': 11, 'nos_id': 10}


def test_tidal_data_within_bounding_box(florence2018):
    null_data = florence2018.tidal_data_within_bounding_box(
        end_date=florence2018.start_date + timedelta(minutes=1)
    )

    tidal_data = florence2018.tidal_data_within_bounding_box(
        start_date=datetime(2018, 9, 13, 23, 59), end_date=datetime(2018, 9, 14)
    )

    assert null_data['t'].sizes == {}

    assert list(tidal_data.data_vars) == ['v', 's', 'f', 'q']
    assert tidal_data.sizes == {'t': 1, 'nos_id': 8}
