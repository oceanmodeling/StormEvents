from datetime import timedelta
from enum import Enum
import ftplib
from functools import wraps
import gzip
import io
import logging
from os import PathLike
import socket
import time
from typing import Any, Dict, List, TextIO, Union
from urllib.error import URLError

from dateutil.parser import parse as parse_date
import numpy
import pandas
from pandas import DataFrame, Series
import typepigeon


def atcf_storm_ids(file_deck: 'ATCF_FileDeck' = None, mode: 'ATCF_Mode' = None) -> List[str]:
    if file_deck is None:
        file_deck = ATCF_FileDeck.a
    elif not isinstance(file_deck, ATCF_FileDeck):
        file_deck = normalize_atcf_value(file_deck, ATCF_FileDeck)

    url = atcf_url(file_deck=file_deck, mode=mode).replace('ftp://', "")
    hostname, directory = url.split('/', 1)
    ftp = ftplib.FTP(hostname, 'anonymous', "")

    filenames = [
        filename for filename, metadata in ftp.mlsd(directory) if metadata['type'] == 'file'
    ]
    if file_deck is not None:
        filenames = [filename for filename in filenames if filename[0] == file_deck.value]

    return sorted((filename.split('.')[0] for filename in filenames), reverse=True)


def atcf_id_from_storm_name(storm_name: str, year: int) -> str:
    return get_atcf_entry(storm_name=storm_name, year=year)[20].strip()


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
    url = 'ftp://ftp.nhc.noaa.gov/atcf/archive/storm.table'

    try:
        storm_table = pandas.read_csv(url, header=None)
    except URLError:
        raise ConnectionError(f'cannot connect to "{url}"')

    if basin is not None and storm_number is not None:
        rows = storm_table[
            (storm_table[1] == f'{basin.upper():>3}') & (storm_table[7] == storm_number)
        ]
    elif storm_name is not None:
        rows = storm_table[storm_table[0].str.contains(storm_name.upper())]
    else:
        raise ValueError('need either storm name + year OR basin + storm number + year')

    if len(rows) > 0:
        rows = rows[rows[8] == int(year)]
        if len(rows) > 0:
            return list(rows.iterrows())[0][1]
        else:
            raise ValueError(
                f'no storms with given info ("{storm_name}" / "{basin}{storm_number}") found in year "{year}"'
            )


def atcf_url(
    file_deck: ATCF_FileDeck = None, storm_id: str = None, mode: ATCF_Mode = None,
) -> str:
    if storm_id is not None:
        year = int(storm_id[4:])
    else:
        year = None

    if mode is None:
        entry = get_atcf_entry(basin=storm_id[:2], storm_number=int(storm_id[2:4]), year=year)
        mode = entry[18].strip()

    if file_deck is not None and not isinstance(file_deck, ATCF_FileDeck):
        try:
            file_deck = normalize_atcf_value(file_deck, ATCF_FileDeck)
        except ValueError:
            file_deck = None
    if file_deck is None:
        file_deck = ATCF_FileDeck.a

    if mode is not None and not isinstance(mode, ATCF_Mode):
        try:
            mode = normalize_atcf_value(mode, ATCF_Mode)
        except ValueError:
            mode = None
    if mode is None:
        mode = ATCF_Mode.realtime

    if mode == ATCF_Mode.historical:
        nhc_dir = f'archive/{year}'
        suffix = '.dat.gz'
    elif mode == ATCF_Mode.realtime:
        if file_deck == ATCF_FileDeck.a:
            nhc_dir = 'aid_public'
            suffix = '.dat.gz'
        elif file_deck == ATCF_FileDeck.b:
            nhc_dir = 'btk'
            suffix = '.dat'
        else:
            raise NotImplementedError(f'filedeck "{file_deck}" is not implemented')
    else:
        raise NotImplementedError(f'mode "{mode}" is not implemented')

    url = f'ftp://ftp.nhc.noaa.gov/atcf/{nhc_dir}/'

    if storm_id is not None:
        url += f'{file_deck.value}{storm_id.lower()}{suffix}'

    return url


def get_atcf_file(
    storm_id: str, file_deck: ATCF_FileDeck = None, mode: ATCF_Mode = None
) -> io.BytesIO:
    url = atcf_url(file_deck=file_deck, storm_id=storm_id, mode=mode).replace('ftp://', "")
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
    atcf: Union[PathLike, io.BytesIO, TextIO],
    allowed_record_types: List[ATCF_RecordType] = None,
) -> DataFrame:
    if allowed_record_types is not None:
        allowed_record_types = [
            typepigeon.convert_value(record_type, str) for record_type in allowed_record_types
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
        except FileNotFoundError:
            # check if the entire track file was passed as a string
            atcf = str(atcf).splitlines()
            if len(atcf) == 1:
                raise

    records = []
    for line in atcf:
        if isinstance(line, bytes):
            line = line.decode('UTF-8')
        if allowed_record_types is None or line.split(',')[4].strip() in allowed_record_types:
            records.append(read_atcf_line(line))

    if len(records) == 0:
        raise ValueError(f'no records found with type(s) "{allowed_record_types}"')

    return DataFrame.from_records(records)


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
        storm_name = line[27].strip()
    else:
        storm_name = ''

    record['name'] = storm_name

    return record


def retry(
    exception_to_check: Exception,
    tries: int = 4,
    delay: float = 3,
    backoff: int = 2,
    logger: logging.Logger = None,
):
    """
    Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param exception_to_check: the exception to check. may be a tuple of exceptions to check
    :param tries: number of times to try (not retry) before giving up
    :param delay: initial delay between retries in seconds
    :param backoff: backoff multiplier e.g. value of 2 will double the delay each retry
    :param logger: logger to use. If None, print
    """

    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exception_to_check as e:
                    msg = '%s, Retrying in %d seconds...' % (str(e), mdelay)
                    if logger is not None:
                        logger.warning(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry
