from copy import copy
from datetime import timedelta
import sys

import numpy
import pytest
from pytest_socket import SocketBlockedError

from stormevents.nhc.storms import nhc_storms, nhc_storms_gis_archive
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

    storms = [
        ('michael', 2018),
        ('florence', 2018),
        ('irma', 2017),
        ('maria', 2017),
        ('harvey', 2017),
        ('sandy', 2012),
        ('irene', 2011),
        ('ike', 2008),
        ('isabel', 2003),
    ]

    for storm in storms:
        track = VortexTrack.from_storm_name(*storm, file_deck='b')
        track.to_file(
            output_directory / f'{track.name.lower()}{track.year}.fort.22', overwrite=True
        )

    check_reference_directory(output_directory, reference_directory)


def test_vortex_track_isotachs():
    track_1 = VortexTrack('florence2018')
    track_2 = VortexTrack('florence2018', file_deck='a')

    track_1.isotachs(34)
    track_2.isotachs(34)


def test_vortex_track_properties():
    track = VortexTrack('florence2018', file_deck='a')

    assert len(track) == 10090

    track.start_date = timedelta(days=1)

    assert len(track) == 10080

    track.end_date = timedelta(days=-1)

    assert len(track) == 9894

    track.advisories = 'OFCL'

    assert len(track) == 1249

    track.end_date = None

    assert len(track) == 1289

    track.nhc_code = 'AL072018'

    assert len(track) == 175


def test_vortex_track_tracks():
    track = VortexTrack.from_storm_name('florence', 2018, file_deck='a')

    tracks = track.tracks

    assert len(tracks) == 4
    assert len(tracks['OFCL']) == 77
    assert len(tracks['OFCL']['20180831T000000']) == 13


@pytest.mark.disable_socket
def test_vortex_track_from_file():
    input_directory = INPUT_DIRECTORY / 'test_vortex_track_from_file'
    output_directory = OUTPUT_DIRECTORY / 'test_vortex_track_from_file'
    reference_directory = REFERENCE_DIRECTORY / 'test_vortex_track_from_file'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    track_1 = VortexTrack.from_file(input_directory / 'irma2017_fort.22')
    track_2 = VortexTrack.from_file(input_directory / 'AL062018.dat')

    assert track_1.nhc_code == 'AL112017'
    assert track_1.name == 'IRMA'
    assert track_2.nhc_code == 'AL062018'
    assert track_2.name == 'FLORENCE'

    track_1.to_file(output_directory / 'irma2017_fort.22', overwrite=True)
    track_2.to_file(output_directory / 'florence2018_fort.22', overwrite=True)

    check_reference_directory(output_directory, reference_directory)


def test_vortex_track_to_file():
    output_directory = OUTPUT_DIRECTORY / 'test_vortex_track_to_file'
    reference_directory = REFERENCE_DIRECTORY / 'test_vortex_track_to_file'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    track_1 = VortexTrack.from_storm_name('florence', 2018)
    track_1.to_file(output_directory / 'florence2018_best.dat', overwrite=True)
    track_1.to_file(output_directory / 'florence2018_best.fort.22', overwrite=True)

    track_2 = VortexTrack.from_storm_name('florence', 2018, file_deck='a')
    track_2.to_file(output_directory / 'florence2018_all.dat', overwrite=True)
    track_2.to_file(output_directory / 'florence2018_all.fort.22', overwrite=True)
    track_2.to_file(
        output_directory / 'florence2018_OFCL.dat', advisory='OFCL', overwrite=True
    )
    track_2.to_file(
        output_directory / 'florence2018_OFCL.fort.22', advisory='OFCL', overwrite=True
    )

    check_reference_directory(output_directory, reference_directory)


def test_vortex_track_distances():
    track_1 = VortexTrack.from_storm_name('florence', 2018)
    track_2 = VortexTrack.from_storm_name('florence', 2018, file_deck='a', advisories=['OFCL'])

    assert numpy.isclose(track_1.distances['BEST']['20180830T060000'], 8725961.838567913)
    assert numpy.isclose(track_2.distances['OFCL']['20180831T000000'], 8882602.389540724)


def test_vortex_track_recompute_velocity():
    output_directory = OUTPUT_DIRECTORY / 'test_vortex_track_recompute_velocity'
    reference_directory = REFERENCE_DIRECTORY / 'test_vortex_track_recompute_velocity'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    track = VortexTrack('irma2017')

    track.data.at[5, 'longitude'] -= 0.1
    track.data.at[5, 'latitude'] += 0.1

    track.to_file(output_directory / 'irma2017_fort.22', overwrite=True)

    check_reference_directory(output_directory, reference_directory)


def test_vortex_track_file_decks():
    output_directory = OUTPUT_DIRECTORY / 'test_vortex_track_file_decks'
    reference_directory = REFERENCE_DIRECTORY / 'test_vortex_track_file_decks'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    file_decks = {
        'a': {
            'start_date': '2018-09-11 06:00',
            'end_date': None,
            'advisories': ['OFCL', 'HWRF', 'HMON', 'CARQ'],
        },
        'b': {
            'start_date': '2018-09-11 06:00',
            'end_date': '2018-09-18 06:00',
            'advisories': ['BEST'],
        },
    }

    for file_deck, values in file_decks.items():
        for advisory in values['advisories']:
            track = VortexTrack(
                'al062018',
                start_date=values['start_date'],
                end_date=values['end_date'],
                file_deck=file_deck,
                advisories=advisory,
            )

            track.to_file(output_directory / f'{file_deck}-deck_{advisory}.22', overwrite=True)

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

    track_1 = VortexTrack.from_file(input_directory / 'fort.22')
    track_1.to_file(output_directory / 'vortex_1.22', overwrite=True)

    track_2 = VortexTrack.from_file(track_1.filename)
    track_2.to_file(output_directory / 'vortex_2.22', overwrite=True)

    track_3 = copy(track_1)
    track_3.to_file(output_directory / 'vortex_3.22', overwrite=True)

    assert track_1 == track_2
    assert track_1 != track_3  # these are not the same because of the velocity recalculation

    check_reference_directory(output_directory, reference_directory)
