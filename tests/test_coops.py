from stormevents.coops.tidalstations import coops_stations, COOPS_StationType


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
