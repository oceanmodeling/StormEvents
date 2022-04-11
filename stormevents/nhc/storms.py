from datetime import datetime
from functools import lru_cache
import re
from typing import Iterable

from bs4 import BeautifulSoup
import numpy
import pandas
import requests

NHC_GIS_ARCHIVE_START_YEAR = 2008


@lru_cache(maxsize=None)
def nhc_storms(year: int = None) -> pandas.DataFrame:
    """
    retrieve a list of hurricanes from NHC since 1851

    :param year: storm year
    :return: table of storms

    >>> nhc_storms()
                    name class  year basin  number    source          start_date            end_date
    nhc_code
    AL021851     UNNAMED    HU  1851    AL       2   ARCHIVE 1851-07-05 12:00:00 1851-07-05 12:00:00
    AL031851     UNNAMED    TS  1851    AL       3   ARCHIVE 1851-07-10 12:00:00 1851-07-10 12:00:00
    AL041851     UNNAMED    HU  1851    AL       4   ARCHIVE 1851-08-16 00:00:00 1851-08-27 18:00:00
    AL051851     UNNAMED    TS  1851    AL       5   ARCHIVE 1851-09-13 00:00:00 1851-09-16 18:00:00
    AL061851     UNNAMED    TS  1851    AL       6   ARCHIVE 1851-10-16 00:00:00 1851-10-19 18:00:00
    ...              ...   ...   ...   ...     ...       ...                 ...                 ...
    CP902021      INVEST    LO  2021    CP      90  METWATCH 2021-07-24 12:00:00                 NaT
    CP912021      INVEST    DB  2021    CP      91  METWATCH 2021-08-07 18:00:00                 NaT
    EP922021      INVEST    DB  2021    EP      92  METWATCH 2021-06-05 06:00:00                 NaT
    EP712022  GENESIS001    DB  2022    EP      71   GENESIS 2022-01-20 12:00:00                 NaT
    EP902022      INVEST    LO  2022    EP      90  METWATCH 2022-01-20 12:00:00                 NaT
    [2714 rows x 8 columns]
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

    storms = storms[
        [
            'nhc_code',
            'name',
            'class',
            'year',
            'basin',
            'number',
            'source',
            'start_date',
            'end_date',
        ]
    ]

    if year is not None:
        if isinstance(year, Iterable) and not isinstance(year, str):
            storms = storms[storms['year'].isin(year)]
        else:
            storms = storms[storms['year'] == int(year)]

    storms['nhc_code'] = storms['nhc_code'].str.strip()
    storms.set_index('nhc_code', inplace=True)

    gis_archive_storms = nhc_storms_gis_archive(year=year)
    gis_archive_storms = gis_archive_storms.drop(
        gis_archive_storms[gis_archive_storms.index.isin(storms.index)].index
    )
    if len(gis_archive_storms) > 0:
        gis_archive_storms[['start_date', 'end_date']] = pandas.to_datetime(numpy.nan)
        storms = pandas.concat([storms, gis_archive_storms[storms.columns]])

    for string_column in ['name', 'class', 'source']:
        storms.loc[storms[string_column].str.len() == 0, string_column] = pandas.NA
        storms[string_column] = storms[string_column].str.strip()
        storms[string_column] = storms[string_column].astype('string')

    storms.sort_values(['year', 'number', 'basin'], inplace=True)

    return storms


@lru_cache(maxsize=None)
def nhc_storms_archive(year: int = None) -> pandas.DataFrame:
    url = 'https://ftp.nhc.noaa.gov/atcf/archive/storm.table'

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

    storms = storms[
        [
            'nhc_code',
            'name',
            'class',
            'year',
            'basin',
            'number',
            'source',
            'start_date',
            'end_date',
        ]
    ]

    if year is not None:
        if isinstance(year, Iterable) and not isinstance(year, str):
            storms = storms[storms['year'].isin(year)]
        else:
            storms = storms[storms['year'] == int(year)]

    storms['nhc_code'] = storms['nhc_code'].str.strip()
    storms.set_index('nhc_code', inplace=True)

    storms.sort_values(['year', 'number', 'basin'], inplace=True)

    for string_column in ['name', 'class', 'source']:
        storms.loc[storms[string_column].str.len() == 0, string_column] = pandas.NA
        storms[string_column] = storms[string_column].str.strip()
        storms[string_column] = storms[string_column].astype('string')

    return storms


@lru_cache(maxsize=None)
def nhc_storms_gis_archive(year: int = None) -> pandas.DataFrame:
    """
    retrieve list of hurricanes from GIS archive since 2008

    :param year: storm year
    :return: table of storms

    >>> nhc_storms_gis_archive()
                   name class  year basin  number       source
    nhc_code
    AL012008     ARTHUR    TS  2008    AL       1  GIS_ARCHIVE
    AL022008     BERTHA    HU  2008    AL       2  GIS_ARCHIVE
    AL032008  CRISTOBAL    TS  2008    AL       3  GIS_ARCHIVE
    AL042008      DOLLY    HU  2008    AL       4  GIS_ARCHIVE
    AL052008    EDOUARD    TS  2008    AL       5  GIS_ARCHIVE
         ...        ...   ...   ...   ...     ...          ...
    EP152021       OLAF    HU  2021    EP      15  GIS_ARCHIVE
    EP162021     PAMELA    HU  2021    EP      16  GIS_ARCHIVE
    EP172021       RICK    HU  2021    EP      17  GIS_ARCHIVE
    EP182021      TERRY    TS  2021    EP      18  GIS_ARCHIVE
    EP192021     SANDRA    TS  2021    EP      19  GIS_ARCHIVE
    [523 rows x 6 columns]
    """

    if year is None:
        year = list(range(NHC_GIS_ARCHIVE_START_YEAR, datetime.today().year + 1))

    if isinstance(year, Iterable) and not isinstance(year, str):
        years = sorted(pandas.unique(year))
        return pandas.concat(
            [
                nhc_storms_gis_archive(year)
                for year in years
                if year is not None and year >= NHC_GIS_ARCHIVE_START_YEAR
            ]
        )
    elif not isinstance(year, int):
        year = int(year)

    url = 'http://www.nhc.noaa.gov/gis/archive_wsurge.php'
    response = requests.get(url, params={'year': year})
    if not response.ok:
        response.raise_for_status()
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

    storms['number'] = storms.index.str.slice(2, 4).astype(int)
    storms['basin'] = storms.index.str.slice(0, 2)

    storms['class'] = None
    storms.loc[
        storms['long_name'].str.contains('Tropical Cyclone', flags=re.IGNORECASE)
        | storms['long_name'].str.contains('Hurricane', flags=re.IGNORECASE),
        'class',
    ] = 'HU'
    storms.loc[
        storms['long_name'].str.contains('Tropical Storm', flags=re.IGNORECASE), 'class',
    ] = 'TS'
    storms.loc[
        storms['long_name'].str.contains('Tropical Depression', flags=re.IGNORECASE), 'class',
    ] = 'TD'
    storms.loc[
        storms['long_name'].str.contains('Subtropical', flags=re.IGNORECASE), 'class',
    ] = 'ST'

    storms['source'] = 'GIS_ARCHIVE'

    storms.sort_values(['year', 'basin', 'number'], inplace=True)

    for string_column in ['name', 'class', 'source']:
        storms.loc[storms[string_column].str.len() == 0, string_column] = pandas.NA
        storms[string_column] = storms[string_column].str.strip()
        storms[string_column] = storms[string_column].astype('string')

    return storms[['name', 'class', 'year', 'basin', 'number', 'source']]
