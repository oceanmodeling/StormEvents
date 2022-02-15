from datetime import datetime, timedelta

from shapely import ops

from stormevents import VortexTrack
from stormevents.coops.tidalstations import (
    coops_data_within_region,
    COOPS_Station,
    coops_stations,
    coops_stations_within_region,
)
from tests import check_reference_directory, OUTPUT_DIRECTORY, REFERENCE_DIRECTORY


def test_coops_stations():
    stations = coops_stations()

    assert stations.columns.to_list() == ['nws_id', 'name', 'state', 'removed', 'geometry']


def test_coops_stations_within_region():
    track = VortexTrack('florence2018', file_deck='b')
    combined_wind_swaths = ops.unary_union(list(track.wind_swaths(34).values()))

    stations = coops_stations_within_region(region=combined_wind_swaths)

    assert len(stations) == 10


def test_coops_data_within_region():
    track = VortexTrack('florence2018', file_deck='b')
    combined_wind_swaths = ops.unary_union(list(track.wind_swaths(34).values()))

    data = coops_data_within_region(
        region=combined_wind_swaths,
        start_date=datetime.now() - timedelta(hours=1),
        end_date=datetime.now(),
    )

    assert len(data['nos_id']) == 10


def test_COOPS_Station():
    reference_directory = REFERENCE_DIRECTORY / 'test_COOPS_Station'
    output_directory = OUTPUT_DIRECTORY / 'test_COOPS_Station'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    start_date = datetime(2021, 1, 1)
    end_date = datetime(2021, 1, 1, 0, 10)

    station_1 = COOPS_Station(1612480)
    station_2 = COOPS_Station('OOUH1')
    station_3 = COOPS_Station('Calcasieu Test Station')

    station_1_data = station_1.get(start_date, end_date)
    station_1_constituents = station_1.constituents

    station_2_data = station_2.get(start_date, end_date)
    station_2_constituents = station_2.constituents

    station_3_data = station_3.get(start_date, end_date)
    station_3_constituents = station_3.constituents

    assert station_1.nos_id == 1612480
    assert station_1.nws_id == 'MOKH1'
    assert station_1.name == 'Mokuoloe'
    assert station_2.nos_id == 1612340
    assert station_2.nws_id == 'OOUH1'
    assert station_2.name == 'Honolulu'
    assert station_3.nos_id == 9999531
    assert station_3.nws_id == ''
    assert station_3.name == 'Calcasieu Test Station'

    station_1_constituents.to_csv(output_directory / 'station1612480_constituents.csv')
    station_2_constituents.to_csv(output_directory / 'station1612340_constituents.csv')

    assert len(station_3_data['t']) == 0
    assert len(station_3_constituents) == 0

    assert station_1_data.sizes == {'nos_id': 1, 't': 2}
    assert station_2_data.sizes == {'nos_id': 1, 't': 2}

    check_reference_directory(output_directory, reference_directory)
