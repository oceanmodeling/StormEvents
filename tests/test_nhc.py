from copy import copy
from datetime import timedelta

import numpy
import pandas
import pytest
from pytest_socket import SocketBlockedError

from stormevents.nhc.storms import nhc_storms
from stormevents.nhc.storms import nhc_storms_gis_archive
from stormevents.nhc.track import VortexTrack
from tests import check_reference_directory
from tests import INPUT_DIRECTORY
from tests import OUTPUT_DIRECTORY
from tests import REFERENCE_DIRECTORY


def test_nhc_gis_storms():
    storms = nhc_storms_gis_archive(year=tuple(range(2008, 2021 + 1)))

    assert len(storms) > 0

    storm_1 = storms.loc["AL012008"]
    assert storm_1["name"] == "ARTHUR"
    assert storm_1["class"] == "TS"
    assert storm_1["year"] == 2008
    assert storm_1["basin"] == "AL"
    assert storm_1["number"] == 1

    storm_2 = storms.loc["EP182021"]
    assert storm_2["name"] == "TERRY"
    assert storm_2["class"] == "TS"
    assert storm_2["year"] == 2021
    assert storm_2["basin"] == "EP"
    assert storm_2["number"] == 18


def test_nhc_storms():
    storms = nhc_storms(year=tuple(range(1851, 2021 + 1)))

    assert len(storms) > 0

    storm_1 = storms.loc["AL021851"]
    assert storm_1["name"] == "UNNAMED"
    assert storm_1["class"] == "HU"
    assert storm_1["year"] == 1851
    assert storm_1["basin"] == " AL"
    assert storm_1["number"] == 2

    storm_2 = storms.loc["AL212021"]
    assert storm_2["name"] == "WANDA"
    assert storm_2["class"] == "TS"
    assert storm_2["year"] == 2021
    assert storm_2["basin"] == " AL"
    assert storm_2["number"] == 21


def test_vortex_track():
    output_directory = OUTPUT_DIRECTORY / "test_vortex_track"
    reference_directory = REFERENCE_DIRECTORY / "test_vortex_track"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    storms = [
        ("michael", 2018),
        ("florence", 2018),
        ("irma", 2017),
        ("maria", 2017),
        ("harvey", 2017),
        ("sandy", 2012),
        ("irene", 2011),
        ("ike", 2008),
        ("isabel", 2003),
    ]

    for storm in storms:
        track = VortexTrack.from_storm_name(*storm, file_deck="b")
        track.to_file(
            output_directory / f"{track.name.lower()}{track.year}.fort.22",
            overwrite=True,
        )

    check_reference_directory(output_directory, reference_directory)


def test_vortex_track_isotachs():
    track_1 = VortexTrack("florence2018")
    track_2 = VortexTrack("florence2018", file_deck="a")

    track_1.isotachs(34)
    track_2.isotachs(34)


def test_vortex_track_properties():
    track = VortexTrack("florence2018", file_deck="a")

    assert len(track) == 10090

    track.start_date = timedelta(days=1)

    assert len(track) == 10080

    track.end_date = timedelta(days=-1)

    assert len(track) == 9894

    track.advisories = "OFCL"

    assert len(track) == 1249

    track.end_date = None

    assert len(track) == 1289

    track.nhc_code = "AL072018"

    assert len(track) == 175


def test_vortex_track_tracks():
    track = VortexTrack.from_storm_name("florence", 2018, file_deck="a")

    tracks = track.tracks

    assert len(tracks) == 4
    assert len(tracks["OFCL"]) == 77
    assert len(tracks["OFCL"]["20180831T000000"]) == 13


@pytest.mark.disable_socket
def test_vortex_track_from_file():
    input_directory = INPUT_DIRECTORY / "test_vortex_track_from_file"
    output_directory = OUTPUT_DIRECTORY / "test_vortex_track_from_file"
    reference_directory = REFERENCE_DIRECTORY / "test_vortex_track_from_file"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    track_1 = VortexTrack.from_file(input_directory / "irma2017_fort.22")
    track_2 = VortexTrack.from_file(input_directory / "AL062018.dat")

    assert track_1.nhc_code == "AL112017"
    assert track_1.name == "IRMA"
    assert track_2.nhc_code == "AL062018"
    assert track_2.name == "FLORENCE"

    track_1.to_file(output_directory / "irma2017_fort.22", overwrite=True)
    track_2.to_file(output_directory / "florence2018_fort.22", overwrite=True)

    check_reference_directory(output_directory, reference_directory)


def test_vortex_track_to_file():
    output_directory = OUTPUT_DIRECTORY / "test_vortex_track_to_file"
    reference_directory = REFERENCE_DIRECTORY / "test_vortex_track_to_file"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    track_1 = VortexTrack.from_storm_name("florence", 2018)
    track_1.to_file(output_directory / "florence2018_best.dat", overwrite=True)
    track_1.to_file(
        output_directory / "florence2018_best.fort.22", advisory="BEST", overwrite=True
    )

    track_2 = VortexTrack.from_storm_name("florence", 2018, file_deck="a")
    track_2.to_file(output_directory / "florence2018_all.dat", overwrite=True)
    track_2.to_file(output_directory / "florence2018_all.fort.22", overwrite=True)
    track_2.to_file(
        output_directory / "florence2018_OFCL.dat", advisory="OFCL", overwrite=True
    )
    track_2.to_file(
        output_directory / "florence2018_OFCL.fort.22", advisory="OFCL", overwrite=True
    )

    check_reference_directory(output_directory, reference_directory)


def test_vortex_track_distances():
    track_1 = VortexTrack.from_storm_name("florence", 2018)
    track_2 = VortexTrack.from_storm_name(
        "florence", 2018, file_deck="a", advisories=["OFCL"]
    )

    assert numpy.isclose(
        track_1.distances["BEST"]["20180830T060000"], 8725961.838567913
    )
    assert numpy.isclose(
        track_2.distances["OFCL"]["20180831T000000"], 3499027.5307995058
    )


def test_vortex_track_recompute_velocity():
    output_directory = OUTPUT_DIRECTORY / "test_vortex_track_recompute_velocity"
    reference_directory = REFERENCE_DIRECTORY / "test_vortex_track_recompute_velocity"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    track = VortexTrack("irma2017")

    track.data.at[5, "longitude"] -= 0.1
    track.data.at[5, "latitude"] += 0.1

    track.to_file(output_directory / "irma2017_fort.22", overwrite=True)

    check_reference_directory(output_directory, reference_directory)


def test_vortex_track_file_decks():
    output_directory = OUTPUT_DIRECTORY / "test_vortex_track_file_decks"
    reference_directory = REFERENCE_DIRECTORY / "test_vortex_track_file_decks"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    file_decks = {
        "a": {
            "start_date": "2018-09-11 06:00",
            "end_date": None,
            "advisories": ["OFCL", "HWRF", "HMON", "CARQ"],
        },
        "b": {
            "start_date": "2018-09-11 06:00",
            "end_date": "2018-09-18 06:00",
            "advisories": ["BEST"],
        },
    }

    for file_deck, values in file_decks.items():
        for advisory in values["advisories"]:
            track = VortexTrack(
                "al062018",
                start_date=values["start_date"],
                end_date=values["end_date"],
                file_deck=file_deck,
                advisories=advisory,
            )

            track.to_file(
                output_directory / f"{file_deck}-deck_{advisory}.22", overwrite=True
            )

    check_reference_directory(output_directory, reference_directory)


@pytest.mark.disable_socket
def test_vortex_track_no_internet():
    input_directory = INPUT_DIRECTORY / "test_vortex_track_no_internet"
    output_directory = OUTPUT_DIRECTORY / "test_vortex_track_no_internet"
    reference_directory = REFERENCE_DIRECTORY / "test_vortex_track_no_internet"

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    with pytest.raises((ConnectionError, SocketBlockedError)):
        VortexTrack(storm="florence2018")

    with pytest.raises((ConnectionError, SocketBlockedError)):
        VortexTrack(storm="al062018", start_date="20180911", end_date=None)

    track_1 = VortexTrack.from_file(input_directory / "fort.22", file_deck="b")
    track_1.to_file(output_directory / "vortex_1.22", overwrite=True)

    track_2 = VortexTrack.from_file(track_1.filename)
    track_2.to_file(output_directory / "vortex_2.22", overwrite=True)

    track_3 = copy(track_1)
    track_3.to_file(output_directory / "vortex_3.22", overwrite=True)

    assert track_1 != track_2  # because file_deck is not specified for track_2
    assert track_1 == track_3

    check_reference_directory(output_directory, reference_directory)


def test_vortex_track_forecast_time_init_arg():
    # Test __init__ to accept forecast_time argument
    track = VortexTrack(
        storm="al062018", advisories=["OFCL"], file_deck="a", forecast_time="09-10-2018"
    )

    dates = track.data.track_start_time.unique()
    assert len(dates) == 1
    assert pandas.to_datetime(dates) == pandas.to_datetime("09-10-2018")


def test_vortex_track_forecast_time_fromname_arg():
    # Test from_storm_name to accept forecast_time argument
    track = VortexTrack.from_storm_name(
        "Florence", 2018, advisories=["OFCL"], file_deck="a", forecast_time="09-10-2018"
    )

    dates = track.data.track_start_time.unique()
    assert len(dates) == 1
    assert pandas.to_datetime(dates) == pandas.to_datetime("09-10-2018")


def test_vortex_track_forecast_time_fromfile_arg():
    # Test from_file to accept forecast_time argument
    input_directory = INPUT_DIRECTORY / "test_vortex_track_from_file"

    track = VortexTrack.from_file(
        input_directory / "AL062018.dat", file_deck="a", forecast_time="09-10-2018"
    )

    dates = track.data.track_start_time.unique()
    assert len(dates) == 1
    assert pandas.to_datetime(dates) == pandas.to_datetime("09-10-2018")


# def test_vortex_track_forecast_time_outofbound_date():
#     # Test it raises if forecast time is not between start and end
#     msg = ""
#     try:
#         VortexTrack(
#             "al062018", advisories=["OFCL"], file_deck="a", forecast_time="07-15-2018"
#         )
#     except ValueError as e:
#         msg = str(e)
#
#     assert "forecast time is outside available" in msg


def test_vortex_track_forecast_time_nonforecast_track():
    # Test it raises if a non-forecast track is requested but forecast
    # time is specified
    msg = ""
    try:
        VortexTrack(
            "al062018", advisories=["OFCL"], file_deck="b", forecast_time="07-15-2018"
        )
    except ValueError as e:
        msg = str(e)

    assert "only applies to forecast" in msg


def test_vortex_track_forecast_time_set_value():
    track = VortexTrack.from_storm_name(
        "Florence",
        2018,
        advisories=["OFCL"],
        file_deck="a",
    )
    track.forecast_time = "09-10-2018"

    dates = track.data.track_start_time.unique()

    assert len(dates) == 1
    assert pandas.to_datetime(dates) == pandas.to_datetime("09-10-2018")


def test_vortex_track_forecast_time_unset_value():
    track = VortexTrack.from_storm_name(
        "Florence", 2018, advisories=["OFCL"], file_deck="a", forecast_time="09-10-2018"
    )
    track.forecast_time = None

    dates = track.data.track_start_time.unique()

    assert len(dates) > 1


def test_carq_autofix_ofcl():
    track = VortexTrack.from_storm_name(
        "Florence", 2018, advisories=["OFCL"], file_deck="a"
    )

    variables_of_interest = [
        "central_pressure",
        "background_pressure",
        "radius_of_maximum_winds",
    ]

    assert not (track.data[variables_of_interest] == 0).any(axis=None)
    assert not (track.data[variables_of_interest].isna()).any(axis=None)
