from datetime import datetime
from functools import lru_cache
from typing import Iterable, List, Union

from bs4 import BeautifulSoup
import pandas
import requests

RECORDS_START_YEAR = 2008


@lru_cache(maxsize=1)
def nhc_storms(year: int = None) -> pandas.DataFrame:
    """
    Read list of hurricanes from NHC based on year

    :param year: storm year
    :return: table of storms
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

    storms = pandas.DataFrame(rows, columns=['id', 'name', 'long_name', 'year'],)
    storms.set_index('id', inplace=True)

    return storms
