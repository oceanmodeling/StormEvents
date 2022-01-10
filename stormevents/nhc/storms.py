from datetime import datetime
from functools import lru_cache
from typing import Iterable

from bs4 import BeautifulSoup
import pandas
import requests

RECORDS_START_YEAR = 2008


@lru_cache(maxsize=1)
def nhc_storms(year: int = None) -> pandas.DataFrame:
    """
    read list of hurricanes from NHC based on year

    :param year: storm year
    :return: table of storms

    >>> nhc_storms()
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

    [523 rows x 3 columns]
    """

    if year is None:
        year = list(range(RECORDS_START_YEAR, datetime.today().year + 1))

    if isinstance(year, Iterable) and not isinstance(year, str):
        years = sorted(pandas.unique(year))
        return pandas.concat(
            [
                nhc_storms(year)
                for year in years
                if year is not None and year >= RECORDS_START_YEAR
            ]
        )
    elif not isinstance(year, int):
        year = int(year)

    if year < RECORDS_START_YEAR:
        raise ValueError(f'GIS Data is not available for storms before {RECORDS_START_YEAR}')

    url = 'http://www.nhc.noaa.gov/gis/archive_wsurge.php'
    response = requests.get(url, params={'year': year})
    soup = BeautifulSoup(response.content, features='html.parser')
    table = soup.find('table')

    rows = []
    for row in table.find_all('tr')[1:]:
        identifier, long_name = (entry.text for entry in row.find_all('td'))
        short_name = long_name.split()[-1]
        rows.append((f'{identifier}{year}', short_name, long_name, year))

    storms = pandas.DataFrame(rows, columns=['nhc_code', 'name', 'long_name', 'year'],)
    storms.set_index('nhc_code', inplace=True)

    return storms
