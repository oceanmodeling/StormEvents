from datetime import datetime
from datetime import timedelta

import pandas
import pytest
import shapely
from shapely.geometry import box

from stormevents.nhc import nhc_storms
from stormevents.stormevent import StormEvent
from stormevents.stormevent import StormStatus
from tests import check_reference_directory
from tests import OUTPUT_DIRECTORY
from tests import REFERENCE_DIRECTORY


@pytest.fixture
def florence2018() -> StormEvent:
    return StormEvent("florence", 2018)


@pytest.fixture
def ida2021() -> StormEvent:
    return StormEvent("florence", 2018)


def test_storm_event_lookup():
    florence2018 = StormEvent("florence", 2018)
    paine2016 = StormEvent.from_nhc_code("EP172016")
    henri2021 = StormEvent.from_usgs_id(310)
    ida2021 = StormEvent("ida", 2021)

    with pytest.raises(ValueError):
        StormEvent("nonexistent", 2021)

    with pytest.raises(ValueError):
        StormEvent.from_nhc_code("nonexistent")

    with pytest.raises(ValueError):
        StormEvent.from_nhc_code("AL992021")

    with pytest.raises(ValueError):
        StormEvent.from_nhc_code(-1)

    with pytest.raises(ValueError):
        StormEvent.from_usgs_id(-1)

    assert florence2018.name == "FLORENCE"
    assert florence2018.year == 2018
    assert florence2018.basin == "AL"
    assert florence2018.number == 6
    assert florence2018._StormEvent__data_start == datetime(2018, 8, 30, 6)
    assert florence2018.nhc_code == "AL062018"
    assert florence2018.usgs_id == 283
    assert florence2018.start_date == datetime(2018, 8, 30, 6)
    assert florence2018.end_date == datetime(2018, 9, 18, 12)
    assert (
        repr(florence2018)
        == "StormEvent(name='FLORENCE', year=2018, start_date=Timestamp('2018-08-30 06:00:00'), end_date=Timestamp('2018-09-18 12:00:00'))"
    )

    assert paine2016.name == "PAINE"
    assert paine2016.year == 2016
    assert paine2016.nhc_code == "EP172016"
    assert paine2016.usgs_id is None
    assert paine2016.start_date == datetime(2016, 9, 18)
    assert paine2016.end_date == datetime(2016, 9, 21, 12)

    assert henri2021.name == "HENRI"
    assert henri2021.year == 2021
    assert henri2021.nhc_code == "AL082021"
    assert henri2021.usgs_id == 310
    assert henri2021.start_date == datetime(2021, 8, 20, 18)
    assert henri2021.end_date == datetime(2021, 8, 24, 18)

    assert ida2021.name == "IDA"
    assert ida2021.year == 2021
    assert ida2021.nhc_code == "AL092021"
    assert ida2021.usgs_id == 312
    assert ida2021.start_date == datetime(2021, 8, 27, 18)
    assert ida2021.end_date == datetime(2021, 9, 4, 18)


def test_storm_event_time_interval():
    florence2018 = StormEvent("florence", 2018, start_date=timedelta(days=-2))
    paine2016 = StormEvent.from_nhc_code("EP172016", end_date=timedelta(days=1))
    henri2021 = StormEvent.from_usgs_id(
        310, start_date=timedelta(days=-4), end_date=timedelta(days=-2)
    )
    ida2021 = StormEvent(
        "ida", 2021, start_date=datetime(2021, 8, 30), end_date=datetime(2021, 9, 1)
    )

    # test times outside base interval
    StormEvent("florence", 2018, start_date=timedelta(days=30))
    StormEvent("florence", 2018, start_date=datetime(2018, 10, 1))

    assert florence2018.start_date == datetime(2018, 9, 16, 12)
    assert florence2018.end_date == datetime(2018, 9, 18, 12)
    assert (
        repr(florence2018)
        == "StormEvent(name='FLORENCE', year=2018, start_date=Timestamp('2018-09-16 12:00:00'), end_date=Timestamp('2018-09-18 12:00:00'))"
    )

    assert paine2016.start_date == datetime(2016, 9, 18)
    assert paine2016.end_date == datetime(2016, 9, 19)
    assert (
        repr(paine2016)
        == "StormEvent(name='PAINE', year=2016, start_date=Timestamp('2016-09-18 00:00:00'), end_date=Timestamp('2016-09-19 00:00:00'))"
    )

    assert henri2021.start_date == datetime(2021, 8, 20, 18)
    assert henri2021.end_date == datetime(2021, 8, 22, 18)
    assert (
        repr(henri2021)
        == "StormEvent(name='HENRI', year=2021, start_date=Timestamp('2021-08-20 18:00:00'), end_date=Timestamp('2021-08-22 18:00:00'))"
    )

    assert ida2021.start_date == datetime(2021, 8, 30)
    assert ida2021.end_date == datetime(2021, 9, 1)
    assert (
        repr(ida2021)
        == "StormEvent(name='IDA', year=2021, start_date=datetime.datetime(2021, 8, 30, 0, 0), end_date=datetime.datetime(2021, 9, 1, 0, 0))"
    )


def test_storm_event_track(florence2018, ida2021):
    reference_directory = REFERENCE_DIRECTORY / "test_storm_event_track"
    output_directory = OUTPUT_DIRECTORY / "test_storm_event_track"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    florence_track = florence2018.track()
    ida_track = ida2021.track()

    florence_track.to_file(output_directory / "florence2018.fort.22")
    ida_track.to_file(output_directory / "ida2021.fort.22")

    check_reference_directory(output_directory, reference_directory)


def test_storm_event_track_forecast_time(florence2018):
    florence_track = florence2018.track(file_deck="a", forecast_time="09-10-2018")
    assert len(florence_track.data.track_start_time.unique()) == 1


def test_storm_event_high_water_marks(florence2018):
    reference_directory = REFERENCE_DIRECTORY / "test_storm_event_high_water_marks"
    output_directory = OUTPUT_DIRECTORY / "test_storm_event_high_water_marks"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    flood = florence2018.flood_event

    high_water_marks = flood.high_water_marks()
    high_water_marks.to_csv(output_directory / "florence2018_hwm.csv")

    check_reference_directory(output_directory, reference_directory)


def test_storm_event_coops_product_within_isotach(florence2018):
    null_data = florence2018.coops_product_within_isotach(
        "water_level",
        wind_speed=34,
        end_date=florence2018.start_date + timedelta(hours=1),
    )

    tidal_data = florence2018.coops_product_within_isotach(
        "water_level",
        wind_speed=34,
        start_date=datetime(2018, 9, 13),
        end_date=datetime(2018, 9, 14),
    )

    assert len(null_data.data_vars) == 0
    assert list(tidal_data.data_vars) == ["v", "s", "f", "q"]

    assert null_data["t"].sizes == {}
    assert tidal_data.sizes["nos_id"] > 0
    assert tidal_data.sizes["t"] > 0


def test_storm_event_coops_product_within_region(florence2018):
    null_tidal_data = florence2018.coops_product_within_region(
        "water_level",
        region=shapely.geometry.box(0, 0, 1, 1),
        start_date=florence2018.start_date,
        end_date=florence2018.start_date + timedelta(minutes=1),
    )

    east_coast = shapely.geometry.box(-85, 25, -65, 45)

    east_coast_tidal_data = florence2018.coops_product_within_region(
        "water_level",
        region=east_coast,
        start_date=datetime(2018, 9, 13, 23, 59),
        end_date=datetime(2018, 9, 14),
    )

    assert len(null_tidal_data.data_vars) == 0
    assert list(east_coast_tidal_data.data_vars) == ["v", "s", "f", "q"]

    assert null_tidal_data["t"].sizes == {}
    assert east_coast_tidal_data.sizes["nos_id"] > 0
    assert east_coast_tidal_data.sizes["t"] > 0


def test_status():
    florence2018 = StormEvent("florence", 2018)
    paine2016 = StormEvent.from_nhc_code("EP172016")
    henri2021 = StormEvent.from_usgs_id(310)
    ida2021 = StormEvent("ida", 2021)

    assert florence2018.status == StormStatus.HISTORICAL
    assert paine2016.status == StormStatus.HISTORICAL
    assert henri2021.status == StormStatus.HISTORICAL
    assert ida2021.status == StormStatus.HISTORICAL

    # TODO: fails due to issue #78
    # How could it pass before in early 2023?!


#    storms = nhc_storms()
#    latest_storm_entry = storms[
#        ((storms["class"] == "HU") | (storms["class"] == "TS"))
#        & (storms["number"] < 60)
#    ].iloc[-1]
#    latest_storm = StormEvent.from_nhc_code(latest_storm_entry.name)
#    age = datetime.today() - latest_storm_entry["end_date"]
#    if pandas.isna(latest_storm_entry["end_date"]) or age < timedelta(days=1):
#        if datetime.today() - latest_storm_entry["start_date"] > timedelta(days=30):
#            assert latest_storm.status == StormStatus.HISTORICAL
#        else:
#            assert latest_storm.status == StormStatus.REALTIME
#    else:
#        assert latest_storm.status == StormStatus.HISTORICAL
