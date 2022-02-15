from datetime import datetime, timedelta
from enum import Enum
import ftplib
import gzip
import io
import itertools
import logging
from os import PathLike
import socket
from typing import Any, Dict, Iterable, List, TextIO, Union

from dateutil.parser import parse as parse_date
import geopandas
from geopandas import GeoDataFrame
import numpy
import pandas
from pandas import DataFrame, Series
import typepigeon

from stormevents.nhc.storms import nhc_storms

ATCF_RECORD_START_YEAR = 1850

# suppress `SettingWithCopyWarning`
pandas.options.mode.chained_assignment = None


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

    if mode == ATCF_Mode.historical and year is None or isinstance(year, Iterable):
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

    a = 'a'
    b = 'b'  # "best track"
    f = 'f'  # https://www.nrlmry.navy.mil/atcf_web/docs/database/new/newfdeck.txt


class ATCF_Mode(Enum):
    historical = 'ARCHIVE'
    realtime = 'aid_public'


class ATCF_RecordType(Enum):
    best = 'BEST'
    ofcl = 'OFCL'
    ofcp = 'OFCP'
    hmon = 'HMON'
    carq = 'CARQ'
    hwrf = 'HWRF'


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
            mode = ATCF_Mode.historical
        else:
            mode = ATCF_Mode.realtime

    if not isinstance(file_deck, ATCF_FileDeck):
        try:
            file_deck = typepigeon.convert_value(file_deck, ATCF_FileDeck)
        except ValueError:
            file_deck = None
    if file_deck is None:
        file_deck = ATCF_FileDeck.a

    if not isinstance(mode, ATCF_Mode):
        try:
            mode = typepigeon.convert_value(mode, ATCF_Mode)
        except ValueError:
            mode = None

    if mode == ATCF_Mode.historical:
        if year is None:
            raise ValueError('NHC storm code not given')
        nhc_dir = f'archive/{year}'
        suffix = '.dat.gz'
    else:
        if file_deck == ATCF_FileDeck.a:
            nhc_dir = 'aid_public'
            suffix = '.dat.gz'
        elif file_deck == ATCF_FileDeck.b:
            nhc_dir = 'btk'
            suffix = '.dat'
        elif file_deck == ATCF_FileDeck.f:
            nhc_dir = 'fix'
            suffix = '.dat'
        else:
            raise NotImplementedError(f'filedeck "{file_deck}" is not implemented')

    url = f'ftp://ftp.nhc.noaa.gov/atcf/{nhc_dir}/'

    if nhc_code is not None:
        url += f'{file_deck.value}{nhc_code.lower()}{suffix}'

    return url


def get_atcf_file(
    nhc_code: str, file_deck: ATCF_FileDeck = None, mode: ATCF_Mode = None
) -> io.BytesIO:
    url = atcf_url(file_deck=file_deck, nhc_code=nhc_code, mode=mode).replace('ftp://', "")
    logging.info(f'Downloading storm data from {url}')

    hostname, filename = url.split('/', 1)

    handle = io.BytesIO()

    try:
        ftp = ftplib.FTP(hostname, 'anonymous', "")
        ftp.encoding = 'utf-8'
        ftp.retrbinary(f'RETR {filename}', handle.write)
    except socket.gaierror:
        raise ConnectionError(f'cannot connect to {hostname}')

    return handle


def normalize_atcf_value(value: Any, to_type: type, round_digits: int = None,) -> Any:
    if type(value).__name__ == 'Quantity':
        value = value.magnitude
    if not (value is None or pandas.isna(value) or value == ''):
        if round_digits is not None and issubclass(to_type, (int, float)):
            if isinstance(value, str):
                value = float(value)
            value = round(value, round_digits)
        value = typepigeon.convert_value(value, to_type)
    return value


def read_atcf(
    atcf: Union[PathLike, io.BytesIO, TextIO], record_types: List[ATCF_RecordType] = None,
) -> GeoDataFrame:
    if record_types is not None:
        record_types = [
            typepigeon.convert_value(record_type, str) for record_type in record_types
        ]

    if isinstance(atcf, io.BytesIO):
        # test if Gzip file
        atcf.seek(0)  # rewind
        first_two_bytes = atcf.read(2)
        atcf.seek(0)  # rewind
        if first_two_bytes == b'\x1f\x8b':
            atcf = gzip.GzipFile(fileobj=atcf)
        elif len(first_two_bytes) == 0:
            raise ValueError('empty file')
    else:
        try:
            if not isinstance(atcf, TextIO):
                atcf = open(atcf)
            atcf = atcf.readlines()
        except (FileNotFoundError, OSError):
            # check if the entire track file was passed as a string
            atcf = str(atcf).splitlines()
            if len(atcf) == 1:
                raise

    records = []
    for line in atcf:
        if isinstance(line, bytes):
            line = line.decode('UTF-8')
        if record_types is None or line.split(',')[4].strip() in record_types:
            try:
                records.append(read_atcf_line(line))
            except ValueError:
                pass

    if len(records) == 0:
        raise ValueError(f'no records found with type(s) "{record_types}"')

    data = DataFrame(records)

    return GeoDataFrame(
        data, geometry=geopandas.points_from_xy(data['longitude'], data['latitude'])
    )


def read_atcf_line(line: str) -> Dict[str, Any]:
    """
    https://dtcenter.org/metplus-practical-session-guide-july-2019/metplus-practical-session-guide-july-2019/session-5-trkintfeature-relative/met-tool-tc-pairs
    https://www.nrlmry.navy.mil/atcf_web/docs/database/new/abdeck.txt

    :param line: ATCF line
    :return: dictionary record of parsed values
    """

    line = [value.strip() for value in line.split(',')]

    for index, value in enumerate(line):
        if isinstance(value, str) and r'\n' in value:
            line[index] = value.replace(r'\n', '')

    record = {
        'basin': line[0],
        'storm_number': line[1],
    }

    record['record_type'] = line[4]

    # computing the actual datetime based on record_type
    minutes = '00'
    if record['record_type'] == 'BEST':
        # Add minutes line to base datetime
        if len(line[3]) > 0:
            minutes = line[3]

    record['datetime'] = parse_date(f'{line[2]}{minutes}')

    # Add forecast period to base datetime
    forecast_hours = int(line[5])
    if forecast_hours != 0:
        record['datetime'] += timedelta(hours=forecast_hours)

    latitude = line[6]
    if 'N' in latitude:
        latitude = float(latitude.strip('N'))
    elif 'S' in latitude:
        latitude = float(latitude.strip('S')) * -1
    latitude *= 0.1
    record['latitude'] = latitude

    longitude = line[7]
    if 'E' in longitude:
        longitude = float(longitude.strip('E')) * 0.1
    elif 'W' in longitude:
        longitude = float(longitude.strip('W')) * -0.1
    record['longitude'] = longitude

    record.update(
        {
            'max_sustained_wind_speed': normalize_atcf_value(line[8], int),
            'central_pressure': normalize_atcf_value(line[9], int),
            'development_level': line[10],
        }
    )

    try:
        record['isotach'] = normalize_atcf_value(line[11], int)
    except ValueError:
        raise Exception(
            'Error: No radial wind information for this storm; '
            'parametric wind model cannot be built.'
        )

    record.update(
        {
            'quadrant': line[12],
            'radius_for_NEQ': normalize_atcf_value(line[13], int),
            'radius_for_SEQ': normalize_atcf_value(line[14], int),
            'radius_for_SWQ': normalize_atcf_value(line[15], int),
            'radius_for_NWQ': normalize_atcf_value(line[16], int),
        }
    )

    if len(line) > 18:
        record.update(
            {
                'background_pressure': normalize_atcf_value(line[17], int),
                'radius_of_last_closed_isobar': normalize_atcf_value(line[18], int),
                'radius_of_maximum_winds': normalize_atcf_value(line[19], int),
            }
        )
    else:
        record.update(
            {
                'background_pressure': numpy.nan,
                'radius_of_last_closed_isobar': numpy.nan,
                'radius_of_maximum_winds': numpy.nan,
            }
        )

    if len(line) > 23:
        record.update(
            {
                'direction': normalize_atcf_value(line[25], int),
                'speed': normalize_atcf_value(line[26], int),
            }
        )
    else:
        record.update(
            {'direction': numpy.nan, 'speed': numpy.nan,}
        )

    if len(line) > 27:
        storm_name = line[27]
    else:
        storm_name = ''

    record['name'] = storm_name

    return record
