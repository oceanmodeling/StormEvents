from copy import copy
from datetime import datetime, timedelta

from dateutil.parser import parse as parse_date
import pytest
from pytest_socket import SocketBlockedError

from stormevents.nhc import nhc_storms
from stormevents.nhc.storms import nhc_gis_storms
from stormevents.nhc.track import VortexTrack
from tests import (
    check_reference_directory,
    INPUT_DIRECTORY,
    OUTPUT_DIRECTORY,
    REFERENCE_DIRECTORY,
)


def test_nhc_gis_storms():
    reference_directory = REFERENCE_DIRECTORY / 'test_nhc_gis_storms'
    output_directory = OUTPUT_DIRECTORY / 'test_nhc_gis_storms'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    storms = nhc_gis_storms(year=tuple(range(2008, 2021 + 1)))

    storms.to_csv(output_directory / 'storms.csv')

    check_reference_directory(output_directory, reference_directory)


def test_nhc_storms():
    output_directory = OUTPUT_DIRECTORY / 'test_nhc_storms'
    reference_directory = REFERENCE_DIRECTORY / 'test_nhc_storms'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    storms = nhc_storms(year=tuple(range(1851, 2021 + 1)))
    storms.to_csv(output_directory / 'storms.csv')

    check_reference_directory(output_directory, reference_directory)


def test_VortexTrack():
    output_directory = OUTPUT_DIRECTORY / 'test_VortexTrack'
    reference_directory = REFERENCE_DIRECTORY / 'test_VortexTrack'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    tracks = [
        'michael2018',
        'florence2018',
        'irma2017',
        'maria2017',
        'harvey2017',
        'sandy2012',
        'irene2011',
        'ike2008',
        'isabel2003',
    ]

    tracks = [
        VortexTrack(storm, file_deck='a', start_date=timedelta(days=-1)) for storm in tracks
    ]

    for track in tracks:
        track.write(output_directory / f'{track.name}{track.year}.fort.22', overwrite=True)

    check_reference_directory(output_directory, reference_directory)


def test_VortexTrack_filters():
    track = VortexTrack('florence2018', file_deck='a')

    assert len(track) == 10234

    track.start_date = timedelta(days=1)

    assert len(track) == 10224

    track.end_date = datetime(2018, 9, 20)

    assert len(track) == 10165

    track.record_type = 'OFCL'

    assert len(track) == 1313

    track.end_date = None

    assert len(track) == 1335

    track.nhc_code = 'AL072018'

    assert len(track) == 175


def test_from_fort22():
    input_directory = INPUT_DIRECTORY / 'test_from_fort22'
    output_directory = OUTPUT_DIRECTORY / 'test_from_fort22'
    reference_directory = REFERENCE_DIRECTORY / 'test_from_fort22'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    vortex = VortexTrack.from_fort22(fort22=input_directory / 'irma2017_fort.22',)

    assert vortex.nhc_code == 'AL112017'
    assert vortex.name == 'IRMA'

    vortex.write(output_directory / 'irma2017_fort.22', overwrite=True)

    check_reference_directory(output_directory, reference_directory)


def test_from_atcf():
    input_directory = INPUT_DIRECTORY / 'test_from_atcf'
    output_directory = OUTPUT_DIRECTORY / 'test_from_atcf'
    reference_directory = REFERENCE_DIRECTORY / 'test_from_atcf'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    vortex = VortexTrack.from_atcf_file(atcf=input_directory / 'florence2018_atcf.trk',)

    assert vortex.nhc_code == 'BT02008'
    assert vortex.name == 'WRT00001'

    vortex.write(output_directory / 'florence2018_fort.22', overwrite=True)

    check_reference_directory(output_directory, reference_directory)


def test_recompute_velocity():
    output_directory = OUTPUT_DIRECTORY / 'test_recompute_velocity'
    reference_directory = REFERENCE_DIRECTORY / 'test_recompute_velocity'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    vortex = VortexTrack('irma2017')

    vortex.data.at[5, 'longitude'] -= 0.1
    vortex.data.at[5, 'latitude'] += 0.1

    vortex.write(output_directory / 'irma2017_fort.22', overwrite=True)

    check_reference_directory(output_directory, reference_directory)


def test_vortex_types():
    output_directory = OUTPUT_DIRECTORY / 'test_vortex_types'
    reference_directory = REFERENCE_DIRECTORY / 'test_vortex_types'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    file_decks = {
        'a': {
            'start_date': parse_date('2018-09-11 06:00'),
            'end_date': None,
            'record_types': ['OFCL', 'HWRF', 'HMON', 'CARQ'],
        },
        'b': {
            'start_date': parse_date('2018-09-11 06:00'),
            'end_date': parse_date('2018-09-18 06:00'),
            'record_types': ['BEST'],
        },
    }

    for file_deck, values in file_decks.items():
        for record_type in values['record_types']:
            cyclone = VortexTrack(
                'al062018',
                start_date=values['start_date'],
                end_date=values['end_date'],
                file_deck=file_deck,
                record_type=record_type,
            )

            cyclone.write(
                output_directory / f'{file_deck}-deck_{record_type}.txt', overwrite=True
            )

    check_reference_directory(output_directory, reference_directory)


@pytest.mark.disable_socket
def test_no_internet():
    input_directory = INPUT_DIRECTORY / 'test_no_internet'
    output_directory = OUTPUT_DIRECTORY / 'test_no_internet'
    reference_directory = REFERENCE_DIRECTORY / 'test_no_internet'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    with pytest.raises((ConnectionError, SocketBlockedError)):
        VortexTrack(storm='florence2018')

    with pytest.raises((ConnectionError, SocketBlockedError)):
        VortexTrack(storm='al062018', start_date='20180911', end_date=None)

    vortex_1 = VortexTrack.from_fort22(input_directory / 'fort.22')
    vortex_1.write(output_directory / 'vortex_1.22', overwrite=True)

    vortex_2 = VortexTrack.from_fort22(vortex_1.filename)
    vortex_2.write(output_directory / 'vortex_2.22', overwrite=True)

    vortex_3 = copy(vortex_1)
    vortex_3.write(output_directory / 'vortex_3.22', overwrite=True)

    assert vortex_1 == vortex_2
    assert vortex_1 == vortex_3

    check_reference_directory(output_directory, reference_directory)
