import pytest

from stormevents.nhc.atcf import ATCF_FileDeck, atcf_files, ATCF_Mode, atcf_url, get_atcf_entry


def test_atcf_url():
    url_1 = atcf_url(nhc_code='AL062018')
    url_2 = atcf_url(mode='current', file_deck='a')
    url_3 = atcf_url(mode='historical', file_deck='a', year=2018)

    assert url_1 == 'ftp://ftp.nhc.noaa.gov/atcf/archive/2018/aal062018.dat.gz'
    assert url_2 == 'ftp://ftp.nhc.noaa.gov/atcf/aid_public/'
    assert url_3 == 'ftp://ftp.nhc.noaa.gov/atcf/archive/2018/'


def test_atcf_storm_ids():
    a_realtime = atcf_files(file_deck=ATCF_FileDeck.a, mode=ATCF_Mode.realtime)
    abf_realtime = atcf_files(mode=ATCF_Mode.realtime)
    a_2014_2015 = atcf_files(file_deck=ATCF_FileDeck.a, year=range(2014, 2015))
    abf_2014_2015 = atcf_files(year=range(2014, 2015))

    assert len(a_realtime) == 67
    assert len(abf_realtime) == 150
    assert len(a_2014_2015) == 32
    assert len(abf_2014_2015) == 96


def test_get_atcf_entry():
    storm_1 = get_atcf_entry(year=2018, basin='AL', storm_number=6)
    storm_2 = get_atcf_entry(year=2018, storm_name='florence')

    with pytest.raises(ValueError):
        get_atcf_entry(year=2018, basin=None, storm_name=None, storm_number=None)
    with pytest.raises(ValueError):
        get_atcf_entry(year=2018, basin='EP', storm_name='nonexistent')
    with pytest.raises(ValueError):
        get_atcf_entry(year=2018, basin='EP', storm_number=99)

    assert storm_1['name'] == 'FLORENCE'
    assert storm_2['basin'] == 'AL' and storm_2['number'] == 6
