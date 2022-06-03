import sys
from datetime import datetime

import pytest
from shapely.geometry import box

from stormevents.coops.tidalstations import coops_product_within_region
from stormevents.coops.tidalstations import COOPS_Station
from stormevents.coops.tidalstations import coops_stations
from stormevents.coops.tidalstations import coops_stations_within_region
from tests import check_reference_directory
from tests import OUTPUT_DIRECTORY
from tests import REFERENCE_DIRECTORY


# TODO figure out why retrieved stations are different in Python 3.6
@pytest.mark.skipif(
    sys.version_info < (3, 7),
    reason="stations list differences in Python 3.6",
)
def test_coops_stations():
    stations = coops_stations()

    assert len(stations) > 0
    assert list(stations.columns) == [
        "nws_id",
        "name",
        "state",
        "status",
        "removed",
        "geometry",
    ]


# TODO figure out why retrieved stations are different in Python 3.6
@pytest.mark.skipif(
    sys.version_info < (3, 7),
    reason="stations list differences in Python 3.6",
)
def test_coops_stations_within_region():
    reference_directory = REFERENCE_DIRECTORY / "test_coops_stations_within_region"
    output_directory = OUTPUT_DIRECTORY / "test_coops_stations_within_region"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    region = box(-83, 25, -75, 36)

    stations = coops_stations_within_region(region=region)

    assert len(stations) == 45

    stations.to_csv(output_directory / "stations.csv")

    check_reference_directory(output_directory, reference_directory)


def test_coops_product_within_region():
    reference_directory = REFERENCE_DIRECTORY / "test_coops_product_within_region"
    output_directory = OUTPUT_DIRECTORY / "test_coops_product_within_region"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    region = box(-83, 25, -75, 36)

    start_date = datetime(2021, 1, 1)
    end_date = datetime(2021, 1, 1, 0, 10)

    data = coops_product_within_region(
        "water_level",
        region=region,
        start_date=start_date,
        end_date=end_date,
    )

    data.to_netcdf(output_directory / "data.nc")

    check_reference_directory(output_directory, reference_directory)


def test_coops_station():
    reference_directory = REFERENCE_DIRECTORY / "test_coops_station"
    output_directory = OUTPUT_DIRECTORY / "test_coops_station"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    start_date = datetime(2021, 1, 1)
    end_date = datetime(2021, 1, 1, 0, 10)

    station_1 = COOPS_Station(1612480)
    station_2 = COOPS_Station("OOUH1")
    station_3 = COOPS_Station("Calcasieu Test Station")
    station_4 = COOPS_Station(9414458)

    assert station_1.nos_id == 1612480
    assert station_1.nws_id == "MOKH1"
    assert station_1.name == "Mokuoloe"
    assert station_2.nos_id == 1612340
    assert station_2.nws_id == "OOUH1"
    assert station_2.name == "Honolulu"
    assert station_3.nos_id == 9999531
    assert station_3.nws_id == ""
    assert station_3.name == "Calcasieu Test Station"
    assert station_4.nos_id == 9414458
    assert station_4.nws_id == "ZSMC1"
    assert station_4.name == "San Mateo Bridge"
    assert not station_4.current

    station_1.constituents.to_csv(output_directory / "station1612480_constituents.csv")
    station_2.constituents.to_csv(output_directory / "station1612340_constituents.csv")
    assert len(station_3.constituents) == 0
    station_4.constituents.to_csv(output_directory / "station9414458_constituents.csv")

    station_1_data = station_1.product("water_level", start_date, end_date)

    station_2_data = station_2.product("water_level", start_date, end_date)

    station_3_data = station_3.product("water_level", start_date, end_date)

    station_4_data = station_4.product(
        "water_level", "2005-03-30", "2005-03-30 02:00:00"
    )

    assert station_1_data.sizes == {"nos_id": 1, "t": 2}
    assert station_2_data.sizes == {"nos_id": 1, "t": 2}
    assert len(station_3_data["t"]) == 0
    assert station_4_data.sizes == {"nos_id": 1, "t": 21}

    check_reference_directory(output_directory, reference_directory)
