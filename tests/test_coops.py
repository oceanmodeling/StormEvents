from datetime import datetime, timedelta

import pandas

from stormevents.coops.tidalstations import COOPS_Station, coops_stations, COOPS_StationType
from tests import REFERENCE_DIRECTORY


def test_coops_stations():
    stations = coops_stations()
    historical_stations = coops_stations(COOPS_StationType.HISTORICAL)

    assert stations.columns.to_list() == [
        'NOS ID',
        'NWS ID',
        'Latitude',
        'Longitude',
        'State',
        'Station Name',
    ]
    assert historical_stations.columns.to_list() == [
        'NWS ID',
        'NOS ID',
        'Removed Date/Time',
        'Latitude',
        'Longitude',
        'State',
        'Station Name',
    ]


def test_COOPS_Station():
    reference_directory = REFERENCE_DIRECTORY / 'test_COOPS_Station'

    station_1 = COOPS_Station(1612480)
    station_2 = COOPS_Station.from_nws_id('OOUH1')

    station_1_data = station_1.get(datetime.today() - timedelta(days=10))
    station_1_constituents = station_1.constituents

    station_2_data = station_2.get(datetime.today() - timedelta(days=10))
    station_2_constituents = station_2.constituents

    station_1_reference_constituents = pandas.read_csv(
        reference_directory / 'station1612480_constituents.csv', index_col='#',
    )
    station_2_reference_constituents = pandas.read_csv(
        reference_directory / 'station1612340_constituents.csv', index_col='#',
    )

    assert station_1_constituents.equals(station_1_reference_constituents)
    assert station_2_constituents.equals(station_2_reference_constituents)
    assert station_1_data.columns.to_list() == ['t', 'v', 's', 'f', 'q']
    assert station_2_data.columns.to_list() == ['t', 'v', 's', 'f', 'q']
