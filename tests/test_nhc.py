from copy import copy
from datetime import datetime, timedelta

from dateutil.parser import parse as parse_date
import pytest
from pytest_socket import SocketBlockedError

from stormevents.nhc.storms import nhc_storms, nhc_storms_gis_archive
from stormevents.nhc.track import VortexTrack
from tests import (INPUT_DIRECTORY, OUTPUT_DIRECTORY, REFERENCE_DIRECTORY,
                   check_reference_directory)


def test_nhc_gis_storms():
    reference_directory = REFERENCE_DIRECTORY / 'test_nhc_gis_storms'
    output_directory = OUTPUT_DIRECTORY / 'test_nhc_gis_storms'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    storms = nhc_storms_gis_archive(year=tuple(range(2008, 2021 + 1)))

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


def test_vortex_track():
    output_directory = OUTPUT_DIRECTORY / 'test_vortex_track'
    reference_directory = REFERENCE_DIRECTORY / 'test_vortex_track'

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
        VortexTrack(storm, file_deck='a', start_date=timedelta(days=-1)) for
        storm in tracks
    ]

    for track in tracks:
        track.write(output_directory / f'{track.name}{track.year}.fort.22',
                    overwrite=True)

    check_reference_directory(output_directory, reference_directory)


def test_vortex_track_properties():
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


@pytest.mark.disable_socket
def test_vortex_track_from_file():
    input_directory = INPUT_DIRECTORY / 'test_vortex_track_from_file'
    output_directory = OUTPUT_DIRECTORY / 'test_vortex_track_from_file'
    reference_directory = REFERENCE_DIRECTORY / 'test_vortex_track_from_file'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    track_1 = VortexTrack.from_fort22(
        fort22=input_directory / 'irma2017_fort.22', )
    track_2 = VortexTrack.from_atcf_file(atcf=input_directory / 'atcf.trk', )

    assert track_1.nhc_code == 'AL112017'
    assert track_1.name == 'IRMA'
    assert track_2.nhc_code == 'BT02008'
    assert track_2.name == 'WRT00001'

    track_1.write(output_directory / 'irma2017_fort.22', overwrite=True)
    track_2.write(output_directory / 'fromatcf_fort.22', overwrite=True)

    check_reference_directory(output_directory, reference_directory)


def test_vortex_track_recompute_velocity():
    output_directory = OUTPUT_DIRECTORY / 'test_vortex_track_recompute_velocity'
    reference_directory = REFERENCE_DIRECTORY / 'test_vortex_track_recompute_velocity'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    track = VortexTrack('irma2017')

    track.data.at[5, 'longitude'] -= 0.1
    track.data.at[5, 'latitude'] += 0.1

    track.write(output_directory / 'irma2017_fort.22', overwrite=True)

    check_reference_directory(output_directory, reference_directory)


def test_vortex_track_file_decks():
    output_directory = OUTPUT_DIRECTORY / 'test_vortex_track_file_decks'
    reference_directory = REFERENCE_DIRECTORY / 'test_vortex_track_file_decks'

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
            track = VortexTrack(
                    'al062018',
                    start_date=values['start_date'],
                    end_date=values['end_date'],
                    file_deck=file_deck,
                    record_type=record_type,
            )

            track.write(
                    output_directory / f'{file_deck}-deck_{record_type}.22',
                    overwrite=True
            )

    check_reference_directory(output_directory, reference_directory)


@pytest.mark.disable_socket
def test_vortex_track_no_internet():
    input_directory = INPUT_DIRECTORY / 'test_vortex_track_no_internet'
    output_directory = OUTPUT_DIRECTORY / 'test_vortex_track_no_internet'
    reference_directory = REFERENCE_DIRECTORY / 'test_vortex_track_no_internet'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    with pytest.raises((ConnectionError, SocketBlockedError)):
        VortexTrack(storm='florence2018')

    with pytest.raises((ConnectionError, SocketBlockedError)):
        VortexTrack(storm='al062018', start_date='20180911', end_date=None)

    track_1 = VortexTrack.from_fort22(input_directory / 'fort.22')
    track_1.write(output_directory / 'vortex_1.22', overwrite=True)

    track_2 = VortexTrack.from_fort22(track_1.filename)
    track_2.write(output_directory / 'vortex_2.22', overwrite=True)

    track_3 = copy(track_1)
    track_3.write(output_directory / 'vortex_3.22', overwrite=True)

    assert track_1 == track_2
    assert track_1 == track_3

    check_reference_directory(output_directory, reference_directory)
