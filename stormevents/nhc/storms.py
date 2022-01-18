from datetime import datetime
from functools import lru_cache
from typing import Iterable

from bs4 import BeautifulSoup
import numpy
import pandas
import requests

WSURGE_RECORDS_START_YEAR = 2008


@lru_cache(maxsize=None)
def wsurge_storms(year: int = None):
    """
    retrieve list of hurricanes from WSURGE that have GIS files available since 2008

    :param year: storm year
    :return: table of storms

    >>> wsurge_storms()
                   name                 long_name  year
    nhc_code
    AL012008     ARTHUR     Tropical Storm ARTHUR  2008
    AL022008     BERTHA          Hurricane BERTHA  2008
    AL032008  CRISTOBAL  Tropical Storm CRISTOBAL  2008
    AL042008      DOLLY           Hurricane DOLLY  2008
    AL052008    EDOUARD    Tropical Storm EDOUARD  2008
                 ...                       ...   ...
    EP152021       OLAF            Hurricane OLAF  2021
    EP162021     PAMELA          Hurricane PAMELA  2021
    EP172021       RICK            Hurricane RICK  2021
    EP182021      TERRY      Tropical Storm TERRY  2021
    EP192021     SANDRA     Tropical Storm SANDRA  2021

    [523 rows x 3 columns]
    """

    if year is None:
        year = list(range(WSURGE_RECORDS_START_YEAR, datetime.today().year + 1))

    if isinstance(year, Iterable) and not isinstance(year, str):
        years = sorted(pandas.unique(year))
        return pandas.concat(
            [
                wsurge_storms(year)
                for year in years
                if year is not None and year >= WSURGE_RECORDS_START_YEAR
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


@lru_cache(maxsize=None)
def nhc_storms(year: int = None) -> pandas.DataFrame:
    """
    retrieve a list of hurricanes from NHC since 1851

    :param year: storm year
    :return: table of storms

    >>> nhc_storms()
                    name class  ...             end_date    source
    nhc_code                    ...
    AL021851     UNNAMED    HU  ...  1851-07-05 12:00:00   ARCHIVE
    AL031851     UNNAMED    TS  ...  1851-07-10 12:00:00   ARCHIVE
    AL041851     UNNAMED    HU  ...  1851-08-27 18:00:00   ARCHIVE
    AL051851     UNNAMED    TS  ...  1851-09-16 18:00:00   ARCHIVE
    AL061851     UNNAMED    TS  ...  1851-10-19 18:00:00   ARCHIVE
                  ...   ...  ...                  ...       ...
    EP192021      SANDRA    TD  ...                  NaN   WARNING
    EP732021  GENESIS030    DB  ...  2021-10-30 12:00:00   GENESIS
    EP742021  GENESIS031    DB  ...  2021-11-05 00:00:00   GENESIS
    EP752021  GENESIS032    DB  ...  2021-11-07 12:00:00   GENESIS
    EP922021      INVEST    DB  ...                  NaN  METWATCH

    [2693 rows x 6 columns]
    """

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
    storms = pandas.read_csv(
        url,
        header=0,
        names=columns,
        parse_dates=['start_date', 'end_date'],
        date_parser=lambda x: pandas.to_datetime(x.strip(), format='%Y%m%d%H')
        if x.strip() != '9999999999'
        else numpy.nan,
    )

    storms = storms.astype(
        {'start_date': 'datetime64[s]', 'end_date': 'datetime64[s]'}, copy=False,
    )

    storms = storms[['nhc_code', 'name', 'class', 'year', 'start_date', 'end_date', 'source']]

    for string_column in ['nhc_code', 'name', 'class', 'source']:
        storms[string_column] = storms[string_column].str.strip()
        storms[string_column][storms[string_column].str.len() == 0] = None

    if year is not None:
        if isinstance(year, Iterable) and not isinstance(year, str):
            storms = storms[storms['year'].isin(year)]
        else:
            storms = storms[storms['year'] == int(year)]

    storms.set_index('nhc_code', inplace=True)

    return storms
