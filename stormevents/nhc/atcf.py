from datetime import datetime
from enum import Enum
import ftplib
import io
import itertools
from os import PathLike
from pathlib import Path
from typing import Iterable, List, TextIO, Union

import geopandas
from geopandas import GeoDataFrame
import pandas
from pandas import DataFrame, Series
import typepigeon

from stormevents.nhc.storms import nhc_storms

ATCF_RECORD_START_YEAR = 1850

# suppress `SettingWithCopyWarning`
pandas.options.mode.chained_assignment = None

# https://www.nrlmry.navy.mil/atcf_web/docs/database/new/abrdeck.html
ATCF_FIELDS = {
    # BASIN - basin, e.g. WP, IO, SH, CP, EP, AL, SL
    'BASIN': 'basin',
    # CY - annual cyclone number: 1 through 99
    'CY': 'storm_number',
    # YYYYMMDDHH - Warning Date-Time-Group: 0000010100 through 9999123123. (note, 4 digit year)
    'YYYYMMDDHH': 'datetime',
    # TECHNUM/MIN - objective technique sorting number, minutes for best track: 00 - 99
    'TECHNUM/MIN': 'advisory_number',
    # TECH - acronym for each objective technique or CARQ or WRNG, BEST for best track.
    'TECH': 'advisory',
    # TAU - forecast period: -24 through 240 hours, 0 for best-track, negative taus used for CARQ and WRNG records.
    'TAU': 'forecast_hours',
    # LatN/S - Latitude (tenths of degrees) for the DTG: 0 through 900, N/S is the hemispheric index.
    'LatN/S': 'latitude',
    # LonE/W - Longitude (tenths of degrees) for the DTG: 0 through 1800, E/W is the hemispheric index.
    'LonE/W': 'longitude',
    # VMAX - Maximum sustained wind speed in knots: 0 through 300.
    'VMAX': 'max_sustained_wind_speed',
    # MSLP - Minimum sea level pressure, 1 through 1100 MB.
    'MSLP': 'central_pressure',
    # TY - Level of tc development: DB - disturbance, TD - tropical depression, TS - tropical storm, TY - typhoon, ST - super typhoon, TC - tropical cyclone, HU - hurricane, SD - subtropical depression, SS - subtropical storm, EX - extratropical systems, IN - inland, DS - dissipating, LO - low, WV - tropical wave, ET - extrapolated, XX - unknown.
    'TY': 'development_level',
    # RAD - Wind intensity (kts) for the radii defined in this record: 34, 50, 64.
    'RAD': 'isotach_radius',
    # WINDCODE - Radius code: AAA - full circle, QQQ - quadrant (NNQ, NEQ, EEQ, SEQ, SSQ, SWQ, WWQ, NWQ)
    'WINDCODE': 'isotach_quadrant_code',
    # RAD1 - If full circle, radius of specified wind intensity, If semicircle or quadrant, radius of specified wind intensity of circle portion specified in radius code. 0 - 1200 nm.
    'RAD1': 'isotach_radius_for_NEQ',
    # RAD2 - If full circle this field not used, If semicicle, radius (nm) of specified wind intensity for semicircle not specified in radius code, If quadrant, radius (nm) of specified wind intensity for 2nd quadrant (counting clockwise from quadrant specified in radius code). 0 through 1200 nm.
    'RAD2': 'isotach_radius_for_SEQ',
    # RAD3 - If full circle or semicircle this field not used, If quadrant, radius (nm) of specified wind intensity for 3rd quadrant (counting clockwise from quadrant specified in radius code). 0 through 1200 nm.
    'RAD3': 'isotach_radius_for_NWQ',
    # RAD4 - If full circle or semicircle this field not used, If quadrant, radius (nm) of specified wind intensity for 4th quadrant (counting clockwise from quadrant specified in radius code). 0 through 1200 nm.
    'RAD4': 'isotach_radius_for_SWQ',
    # RADP - pressure in millibars of the last closed isobar, 900 - 1050 mb.
    'RADP': 'background_pressure',
    # RRP - radius of the last closed isobar in nm, 0 - 9999 nm.
    'RRP': 'radius_of_last_closed_isobar',
    # MRD - radius of max winds, 0 - 999 nm.
    'MRD': 'radius_of_maximum_winds',
    # GUSTS - gusts, 0 through 995 kts.
    'GUSTS': 'gust_speed',
    # EYE - eye diameter, 0 through 999 nm.
    'EYE': 'eye_diameter',
    # SUBREGION - subregion code: A - Arabian Sea, B - Bay of Bengal, C - Central Pacific, E - Eastern Pacific, L - Atlantic, P - South Pacific (135E - 120W), Q - South Atlantic, S - South IO (20E - 135E), W - Western Pacific
    'SUBREGION': 'subregion_code',
    # MAXSEAS - max seas: 0 through 999 ft.
    'MAXSEAS': 'maximum_wave_height',
    # INITIALS - Forecaster's initials, used for tau 0 WRNG, up to 3 chars.
    'INITIALS': 'forecaster_initials',
    # DIR - storm direction in compass coordinates, 0 - 359 degrees.
    'DIR': 'direction',
    # SPEED - storm speed, 0 - 999 kts.
    'SPEED': 'speed',
    # STORMNAME - literal storm name, NONAME or INVEST. TCcyx used pre-1999, where: cy = Annual cyclone number 01 through 99, x = Subregion code: W, A, B, S, P, C, E, L, Q.
    'STORMNAME': 'name',
    # user data section as indicated by USERDEFINED parameter.
    'USERDEFINED': 'extra_values',
}

FORT_22_FIELDS = {
    # Time Record number in column 29. There can be multiple lines for a given time record depending on the number of isotachs reported in the ATCF File
    'RECORD': 'record_number',
    # number of isotachs reported in the ATCF file for the corresponding Time record.
    'ISOTACHS': 'num_isotachs',
    # Columns 31-34 indicate the selection of radii for that particular isotach. 0 indicates do not use this radius, and 1 indicates use this radius and corresponding wind speed.
    'ISOTACHSEL1': 'isotach_select_1',
    'ISOTACHSEL2': 'isotach_select_2',
    'ISOTACHSEL3': 'isotach_select_3',
    'ISOTACHSEL4': 'isotach_select_4',
    # Columns 35-38 are the designated Rmax values computed for each of the quadrants selected for each particular isotach.
    'RMAXQUADRANT1': 'radius_of_maximum_winds_quadrant_1',
    'RMAXQUADRANT2': 'radius_of_maximum_winds_quadrant_2',
    'RMAXQUADRANT3': 'radius_of_maximum_winds_quadrant_3',
    'RMAXQUADRANT4': 'radius_of_maximum_winds_quadrant_4',
    # Column 39 is the Holland B parameter computed using the formulas outlines in the Holland paper, and implemented using the aswip program.
    'HOLLANDB': 'holland_b',
    # Column 40-43 is the quadrant-varying Holland B parameter
    'HOLLANDB1': 'holland_b_quadrant_1',
    'HOLLANDB2': 'holland_b_quadrant_2',
    'HOLLANDB3': 'holland_b_quadrant_3',
    'HOLLANDB4': 'holland_b_quadrant_4',
    # Column 44-47 are the quadrant-varying Vmax calculated at the top of the planetary boundary (a wind reduction factor is applied to reduce the wind speed at the boundary to the 10-m surface)
    'VMAX1': 'max_sustained_wind_speed_1',
    'VMAX2': 'max_sustained_wind_speed_2',
    'VMAX3': 'max_sustained_wind_speed_3',
    'VMAX4': 'max_sustained_wind_speed_4',
}

EXTRA_ATCF_FIELDS = {
    # DEPTH - system depth, D-deep, M-medium, S-shallow, X-unknown
    'DEPTH': 'depth_code',
    # SEAS - Wave height for radii defined in SEAS1-SEAS4, 0-99 ft.
    'SEAS': 'isowave',
    # SEASCODE - Radius code: AAA - full circle,  QQQ - quadrant (NNQ, NEQ, EEQ, SEQ, SSQ, SWQ, WWQ, NWQ)
    'SEASCODE': 'isowave_quadrant_code',
    # SEAS1 - first quadrant seas radius as defined by SEASCODE, 0 through 999 nm.
    'SEAS1': 'isowave_radius_for_NEQ',
    # SEAS2 - second quadrant seas radius as defined by SEASCODE, 0 through 999 nm.
    'SEAS2': 'isowave_radius_for_SEQ',
    # SEAS3 - third quadrant seas radius as defined by SEASCODE, 0 through 999 nm.
    'SEAS3': 'isowave_radius_for_NWQ',
    # SEAS4 - fourth quadrant seas radius as defined by SEASCODE, 0 through 999 nm.
    'SEAS4': 'isowave_radius_for_SWQ',
    # user data section as indicated by USERDEFINED parameter.
    'USERDEFINED': 'extra_values',
}


def atcf_files(
    file_deck: 'ATCF_FileDeck' = None, mode: 'ATCF_Mode' = None, year: int = None
) -> List[str]:
    if file_deck is None:
        return list(
            itertools.chain(
                *(
                    atcf_files(file_deck=file_deck.value, mode=mode, year=year)
                    for file_deck in ATCF_FileDeck
                )
            )
        )

    if mode is None:
        return list(
            itertools.chain(
                *(
                    atcf_files(file_deck=file_deck, mode=mode.value, year=year)
                    for mode in ATCF_Mode
                )
            )
        )

    if not isinstance(file_deck, ATCF_FileDeck):
        file_deck = typepigeon.convert_value(file_deck, ATCF_FileDeck)

    if not isinstance(mode, ATCF_Mode):
        mode = typepigeon.convert_value(mode, ATCF_Mode)

    if mode == ATCF_Mode.HISTORICAL and year is None or isinstance(year, Iterable):
        if year is None:
            year = range(ATCF_RECORD_START_YEAR, datetime.today().year + 1)
        return list(
            itertools.chain(
                *(atcf_files(file_deck=file_deck, mode=mode, year=entry) for entry in year)
            )
        )

    url = atcf_url(file_deck=file_deck, mode=mode, year=year)
    hostname, directory = url.split('/', 3)[2:]
    ftp = ftplib.FTP(hostname.replace('ftp://', ''), 'anonymous', '')

    filenames = [
        filename
        for filename, metadata in ftp.mlsd(directory)
        if metadata['type'] == 'file' and filename[0] == file_deck.value
    ]

    filenames = sorted((filename for filename in filenames), reverse=True)

    if year is not None:
        filenames = [filename for filename in filenames if str(year) in filename]

    return [url + filename for filename in filenames]


class ATCF_FileDeck(Enum):
    """
    These formats specified by the Automated Tropical Cyclone Forecast (ATCF) System.
    The contents of each type of data file is described at http://hurricanes.ral.ucar.edu/realtime/
    """

    ADVISORY = 'a'
    BEST = 'b'  # "best track"
    FIXED = 'f'  # https://www.nrlmry.navy.mil/atcf_web/docs/database/new/newfdeck.txt


class ATCF_Mode(Enum):
    HISTORICAL = 'ARCHIVE'
    REALTIME = 'aid_public'


class ATCF_Advisory(Enum):
    BEST = 'BEST'
    OFCL = 'OFCL'
    OFCP = 'OFCP'
    HMON = 'HMON'
    CARQ = 'CARQ'
    HWRF = 'HWRF'


def get_atcf_entry(
    year: int, basin: str = None, storm_number: int = None, storm_name: str = None,
) -> Series:
    storms = nhc_storms(year=year)

    if storm_name is None and (basin is None and storm_number is None):
        raise ValueError('need either storm name + year OR basin + storm number + year')

    if basin is not None:
        storms = storms[storms['basin'].str.contains(basin.upper())]
    if storm_number is not None:
        storms = storms[storms['number'] == storm_number]
    if storm_name is not None:
        storms = storms[storms['name'].str.contains(storm_name.upper())]

    if len(storms) > 0:
        storms['name'] = storms['name'].str.strip()
        storms['class'] = storms['class'].str.strip()
        storms['basin'] = storms['basin'].str.strip()
        storms['source'] = storms['source'].str.strip()
        return storms.iloc[0]
    else:
        message = f'no storms with given info'
        if storm_name is not None:
            message = f'{message} ("{storm_name}")'
        else:
            message = f'{message} ("{basin}{storm_number}")'
        message = f'{message} found in {year}'
        raise ValueError(message)


def atcf_url(
    nhc_code: str = None, file_deck: ATCF_FileDeck = None, mode: ATCF_Mode = None, year=None,
) -> str:
    if nhc_code is not None:
        year = int(nhc_code[4:])

    if mode is None:
        if nhc_code is None:
            raise ValueError('NHC storm code not given')
        entry = get_atcf_entry(basin=nhc_code[:2], storm_number=int(nhc_code[2:4]), year=year)
        if entry['source'] == 'ARCHIVE':
            mode = ATCF_Mode.HISTORICAL
        else:
            mode = ATCF_Mode.REALTIME

    if not isinstance(file_deck, ATCF_FileDeck):
        try:
            file_deck = typepigeon.convert_value(file_deck, ATCF_FileDeck)
        except ValueError:
            file_deck = None
    if file_deck is None:
        file_deck = ATCF_FileDeck.ADVISORY

    if not isinstance(mode, ATCF_Mode):
        try:
            mode = typepigeon.convert_value(mode, ATCF_Mode)
        except ValueError:
            mode = None

    if mode == ATCF_Mode.HISTORICAL:
        if year is None:
            raise ValueError('NHC storm code not given')
        nhc_dir = f'archive/{year}'
        suffix = '.dat.gz'
    else:
        if file_deck == ATCF_FileDeck.ADVISORY:
            nhc_dir = 'aid_public'
            suffix = '.dat.gz'
        elif file_deck == ATCF_FileDeck.BEST:
            nhc_dir = 'btk'
            suffix = '.dat'
        elif file_deck == ATCF_FileDeck.FIXED:
            nhc_dir = 'fix'
            suffix = '.dat'
        else:
            raise NotImplementedError(f'filedeck "{file_deck}" is not implemented')

    url = f'ftp://ftp.nhc.noaa.gov/atcf/{nhc_dir}/'

    if nhc_code is not None:
        url += f'{file_deck.value}{nhc_code.lower()}{suffix}'

    return url


def read_atcf(
    atcf: Union[PathLike, io.BytesIO, TextIO],
    advisories: List[ATCF_Advisory] = None,
    fort_22: bool = False,
) -> GeoDataFrame:
    """
    read ATCF format

    :param atcf: path or buffered reader
    :param advisories: allowed advisory types
    :param fort_22: whether to parse `fort.22` fields
    :return: data frame of parsed ATCF data
    """

    if advisories is not None:
        advisories = [typepigeon.convert_value(advisory, str) for advisory in advisories]

    if isinstance(atcf, (str, PathLike, Path)):
        atcf = open(atcf)

    lines = (str(line, 'UTF-8') if isinstance(line, bytes) else line for line in atcf)
    lines = (
        (
            entry.strip()
            for entry in line.split(',', maxsplit=len(ATCF_FIELDS) - 1)
            if ~pandas.isna(line)
        )
        for line in lines
    )

    data = DataFrame.from_records(lines)
    data.rename(
        columns={index: list(ATCF_FIELDS)[index] for index in range(len(data.columns))},
        inplace=True,
    )
    for column in ATCF_FIELDS:
        if column not in data.columns:
            data[column] = pandas.NA
    data.astype(
        {field: 'string' for field in data.columns}, copy=False,
    )

    if 'USERDEFINED' in data and data['USERDEFINED'].str.contains(',').any():
        if fort_22:
            extra_fields = FORT_22_FIELDS
        else:
            extra_fields = EXTRA_ATCF_FIELDS
        try:
            lines = (str(line, 'UTF-8') if isinstance(line, bytes) else line for line in atcf)
            lines = (
                (
                    entry.strip()
                    for entry in line.split(',', maxsplit=len(extra_fields) - 1)
                    if ~pandas.isna(line)
                )
                for line in lines
            )
            extra_data = DataFrame.from_records(lines, columns=list(extra_fields),).astype(
                {field: 'string' for field in extra_fields}
            )
            data = pandas.concat([data.iloc[:, :-1], extra_data], axis=1)
        except ValueError:
            pass

    if advisories is not None and len(advisories) > 0:
        data = data[data['TECH'].isin(advisories)]
        if len(data) == 0:
            raise ValueError(f'no ATCF records found matching "{advisories}"')

    best_track_records = (data['TECH'] == 'BEST') & (
        data.loc[data['TECH'] == 'BEST', 'TECHNUM/MIN'].str.strip().str.len() > 0
    )
    data.loc[best_track_records, 'YYYYMMDDHH'] += data.loc[best_track_records, 'TECHNUM/MIN']
    data.loc[~best_track_records, 'YYYYMMDDHH'] += '00'
    data['YYYYMMDDHH'] = pandas.to_datetime(data['YYYYMMDDHH'], format='%Y%m%d%H%M')

    data.loc[data['LatN/S'].str.endswith('N'), 'LatN/S'] = data['LatN/S'].str.strip('N')
    data.loc[data['LatN/S'].str.endswith('S'), 'LatN/S'] = '-' + data['LatN/S'].str.strip('S')

    data.loc[data['LonE/W'].str.endswith('E'), 'LonE/W'] = data['LonE/W'].str.strip('E')
    data.loc[data['LonE/W'].str.endswith('W'), 'LonE/W'] = '-' + data['LonE/W'].str.strip('W')

    data[['LatN/S', 'LonE/W']] = (
        data[['LatN/S', 'LonE/W']].astype({'LatN/S': float, 'LonE/W': float}, copy=False) / 10
    )

    if pandas.isna(data['RAD']).any():
        raise ValueError(
            'Error: No radial wind information for this storm; '
            'parametric wind model cannot be built.'
        )

    float_fields = [
        field
        for field in (
            'VMAX',
            'MSLP',
            'RAD',
            'RAD1',
            'RAD2',
            'RAD3',
            'RAD4',
            'RADP',
            'RRP',
            'MRD',
            'GUSTS',
            'EYE',
            'MAXSEAS',
            'DIR',
            'SPEED',
            'SEAS',
            'SEAS1',
            'SEAS2',
            'SEAS3',
            'SEAS4',
        )
        if field in data.columns
    ]

    for float_field in float_fields:
        data.loc[
            (data[float_field].str.len() == 0) | pandas.isna(data[float_field]), float_field
        ] = 'NaN'

    data[float_fields] = data[float_fields].astype(float, copy=False)

    data.rename(
        columns={
            **{field: value for field, value in ATCF_FIELDS.items() if field in data.columns},
            **{
                field: value
                for field, value in EXTRA_ATCF_FIELDS.items()
                if field in data.columns
            },
            **{
                field: value
                for field, value in FORT_22_FIELDS.items()
                if field in data.columns
            },
        },
        inplace=True,
    )

    return GeoDataFrame(
        data, geometry=geopandas.points_from_xy(data['longitude'], data['latitude'],)
    )
