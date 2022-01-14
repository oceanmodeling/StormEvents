from datetime import datetime, timedelta

import pandas

from stormevents.coops.tidalstations import COOPS_Station, coops_stations
from tests import REFERENCE_DIRECTORY


def test_coops_stations():
    stations = coops_stations()

    assert stations.columns.to_list() == [
        'NWS ID',
        'Latitude',
        'Longitude',
        'State',
        'Station Name',
        'Removed Date/Time',
    ]


def test_COOPS_Station():
    reference_directory = REFERENCE_DIRECTORY / 'test_COOPS_Station'

    station_1 = COOPS_Station(1612480)
    station_2 = COOPS_Station('OOUH1')

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

    pandas.testing.assert_frame_equal(station_1_constituents, station_1_reference_constituents)
    pandas.testing.assert_frame_equal(station_2_constituents, station_2_reference_constituents)
    assert station_1_data.columns.to_list() == ['station', 't', 'v', 's', 'f', 'q']
    assert station_2_data.columns.to_list() == ['station', 't', 'v', 's', 'f', 'q']
