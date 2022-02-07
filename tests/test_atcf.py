import pytest

from stormevents.nhc.atcf import ATCF_FileDeck, atcf_files, ATCF_Mode, get_atcf_entry


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
