from enum import Enum
import ftplib
from typing import Any, List
from urllib.error import URLError

import pandas
from pandas import Series


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


def normalize_atcf_value(value: Any, to_type: type, round_digits: int = None) -> Any:
    if type(value).__name__ == 'Quantity':
        value = value.magnitude
    if issubclass(to_type, Enum):
        try:
            value = to_type[value]
        except (KeyError, ValueError):
            try:
                value = to_type(value)
            except (KeyError, ValueError):
                raise ValueError(
                    f'unrecognized entry "{value}"; must be one of {list(to_type)}'
                )
    elif not pandas.isna(value) and value is not None and value != "":
        if round_digits is not None and issubclass(to_type, (int, float)):
            if isinstance(value, str):
                value = float(value)
            value = round(value, round_digits)
        value = to_type(value)
    return value
