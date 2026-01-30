from copy import copy
from datetime import timedelta

import numpy
import pandas
import pytest
from pytest_socket import SocketBlockedError

import stormevents
from stormevents.nhc.storms import nhc_storms
from stormevents.nhc.storms import nhc_storms_gis_archive
from stormevents.nhc.track import VortexTrack, chavas_2025_Pc, courtney_knaff_2009_Pc
from stormevents.nhc.const import get_RMW_regression_coefs, RMWFillMethod, PcFillMethod
from tests import check_reference_directory
from tests import INPUT_DIRECTORY
from tests import OUTPUT_DIRECTORY
from tests import REFERENCE_DIRECTORY


def test_pcfill():
    input_directory = INPUT_DIRECTORY / "test_pcfill"
    output_directory = OUTPUT_DIRECTORY / "test_pcfill"
    reference_directory = REFERENCE_DIRECTORY / "test_pcfill"
    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    for input_filename in input_directory.iterdir():

        track_o = VortexTrack.from_file(input_directory / input_filename.name)

        data = track_o.data.copy()

        # Usee the chavas (2025) regression method to guess pressure
        data["central_pressure"] = chavas_2025_Pc(data)

        track_c = VortexTrack(data)

        track_c.to_file(
            output_directory / f"{input_filename.name[:-4]}_chavas.dat", overwrite=True
        )

        track_cr = VortexTrack.from_file(
            reference_directory / f"{input_filename.name[:-4]}_chavas.dat"
        )

        # use the Courtney & Knaff (2009) regression method to guess pressure
        data["central_pressure"] = courtney_knaff_2009_Pc(data)

        track_ck = VortexTrack(data)

        track_ck.to_file(
            output_directory / f"{input_filename.name[:-4]}_courtney.dat",
            overwrite=True,
        )

        track_ckr = VortexTrack.from_file(
            reference_directory / f"{input_filename.name[:-4]}_courtney.dat"
        )

        diff = abs(track_ck.data.central_pressure - track_ckr.data.central_pressure)

    check_reference_directory(output_directory, reference_directory)
