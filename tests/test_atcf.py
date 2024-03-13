import pytest
from datetime import datetime

from stormevents.nhc.atcf import ATCF_FileDeck
from stormevents.nhc.atcf import atcf_files
from stormevents.nhc.atcf import ATCF_Mode
from stormevents.nhc.atcf import atcf_url
from stormevents.nhc.atcf import get_atcf_entry


def test_atcf_url():
    url_1 = atcf_url(nhc_code="AL062018")
    url_2 = atcf_url(mode="REALTIME", file_deck="a")
    url_3 = atcf_url(mode="HISTORICAL", file_deck="a", year=2018)

    assert url_1 == "ftp://ftp.nhc.noaa.gov/atcf/archive/2018/aal062018.dat.gz"
    assert url_2 == "ftp://ftp.nhc.noaa.gov/atcf/aid_public/"
    assert url_3 == "ftp://ftp.nhc.noaa.gov/atcf/archive/2018/"


def test_atcf_nhc_codes():
    # Some months of the year this will return empty, resulting in
    # the test to fail! Also testing for all (mode=ATCF_Mode.HISTORICAL)
    # can be very slow.
    #    a_realtime = atcf_files(file_deck=ATCF_FileDeck.ADVISORY, mode=ATCF_Mode.REALTIME)
    #    abf_realtime = atcf_files(mode=ATCF_Mode.REALTIME)
    # Using -2 to avoid test failure in months when the prior year's data
    # has not been moved to the the archive url.
    ref_year = datetime.now().year - 2
    a_historical = atcf_files(
        file_deck=ATCF_FileDeck.ADVISORY, mode=ATCF_Mode.HISTORICAL, year=[ref_year]
    )
    abf_historical = atcf_files(mode=ATCF_Mode.HISTORICAL, year=[ref_year])
    a_2014_2015 = atcf_files(file_deck=ATCF_FileDeck.ADVISORY, year=range(2014, 2015))
    abf_2014_2015 = atcf_files(year=range(2014, 2015))

    #    assert len(a_realtime) > 0
    #    assert len(abf_realtime) > 0
    assert len(a_historical) > 0
    assert len(abf_historical) > 0
    assert len(a_historical) < len(abf_historical)
    assert len(a_2014_2015) > 0
    assert len(abf_2014_2015) > 0


def test_atcf_entry():
    storm_1 = get_atcf_entry(year=2018, basin="AL", storm_number=6)
    storm_2 = get_atcf_entry(year=2018, storm_name="florence")

    with pytest.raises(ValueError):
        get_atcf_entry(year=2018, basin=None, storm_name=None, storm_number=None)
    with pytest.raises(ValueError):
        get_atcf_entry(year=2018, basin="EP", storm_name="nonexistent")
    with pytest.raises(ValueError):
        get_atcf_entry(year=2018, basin="EP", storm_number=99)

    assert get_atcf_entry(year=2020, storm_name="BETA")["name"] == "BETA"
    assert get_atcf_entry(year=2020, storm_name="ETA")["name"] == "ETA"

    assert storm_1["name"] == "FLORENCE"
    assert storm_2["basin"] == "AL" and storm_2["number"] == 6
