from datetime import datetime
from functools import lru_cache
from typing import Iterable

from bs4 import BeautifulSoup
import pandas
import requests

WSURGE_RECORDS_START_YEAR = 2008
NHC_RECORDS_START_YEAR = 1851


@lru_cache(maxsize=1)
def wsurge_storms(year: int = None):
    """
    read list of hurricanes from NHC based on year

    :param year: storm year
    :return: table of storms

    >>> wsurge_storms()
                   name                 long_name  year
    nhc_code
    al012008     ARTHUR     Tropical Storm ARTHUR  2008
    al022008     BERTHA          Hurricane BERTHA  2008
    al032008  CRISTOBAL  Tropical Storm CRISTOBAL  2008
    al042008      DOLLY           Hurricane DOLLY  2008
    al052008    EDOUARD    Tropical Storm EDOUARD  2008
    ...             ...                       ...   ...
    ep152021       OLAF            Hurricane OLAF  2021
    ep162021     PAMELA          Hurricane PAMELA  2021
    ep172021       RICK            Hurricane RICK  2021
    ep182021      TERRY      Tropical Storm TERRY  2021
    ep192021     SANDRA     Tropical Storm SANDRA  2021
    """

    if year is None:
        year = list(range(WSURGE_RECORDS_START_YEAR, datetime.today().year + 1))

    if isinstance(year, Iterable) and not isinstance(year, str):
        years = sorted(pandas.unique(year))
        return pandas.concat(
            [
                nhc_storms(year)
                for year in years
                if year is not None and year >= NHC_RECORDS_START_YEAR
            ]
        )
    elif not isinstance(year, int):
        year = int(year)

    url = 'http://www.nhc.noaa.gov/gis/archive_wsurge.php'
    response = requests.get(url, params={'year': year})
    soup = BeautifulSoup(response.content, features='html.parser')
    table = soup.find('table')

    rows = []
    for row in table.find_all('tr')[1:]:
        identifier, long_name = (entry.text for entry in row.find_all('td'))
        short_name = long_name.split()[-1]
        rows.append((f'{identifier}{year}', short_name, long_name, year))

    storms = pandas.DataFrame(rows, columns=['nhc_code', 'name', 'long_name', 'year'])
    storms['nhc_code'] = storms['nhc_code'].str.upper()
    storms.set_index('nhc_code', inplace=True)

    return storms


@lru_cache(maxsize=1)
def nhc_storms(year: int = None) -> pandas.DataFrame:
    """
    read list of hurricanes from NHC based on year

    :param year: storm year
    :return: table of storms

    >>> nhc_storms()
                    name type  year  start_date    end_date     source
    nhc_code
    AL021851     UNNAMED   HU  1851  1851070512  1851070512    ARCHIVE
    AL031851     UNNAMED   TS  1851  1851071012  1851071012    ARCHIVE
    AL041851     UNNAMED   HU  1851  1851081600  1851082718    ARCHIVE
    AL051851     UNNAMED   TS  1851  1851091300  1851091618    ARCHIVE
    AL061851     UNNAMED   TS  1851  1851101600  1851101918    ARCHIVE
               ...  ...   ...         ...         ...        ...
    EP192021      SANDRA   TD  2021  2021110106  9999999999    WARNING
    EP732021  GENESIS030   DB  2021  2021102712  2021103012    GENESIS
    EP742021  GENESIS031   DB  2021  2021102918  2021110500    GENESIS
    EP752021  GENESIS032   DB  2021  2021110106  2021110712    GENESIS
    EP922021      INVEST   DB  2021  2021060506  9999999999   METWATCH
    """

    if year < NHC_RECORDS_START_YEAR:
        raise ValueError(
            f'GIS Data is not available for storms before {NHC_RECORDS_START_YEAR}'
        )

    url = 'https://ftp.nhc.noaa.gov/atcf/index/storm_list.txt'
    columns = [
        'name',
        'basin',
        2,
        3,
        4,
        5,
        6,
        'number',
        'year',
        'class',
        10,
        'start_date',
        'end_date',
        13,
        14,
        15,
        16,
        17,
        'source',
        19,
        'nhc_code',
    ]
    storms = pandas.read_csv(url, header=0, names=columns)

    if year is not None:
        storms = storms[storms['year'].isin(year)]

    storms = storms[['nhc_code', 'name', 'class', 'year', 'start_date', 'end_date', 'source']]
    storms.set_index('nhc_code', inplace=True)

    return storms
