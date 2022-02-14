"""
interface with the NOAA Center for Operational Oceanographic Products and Services (CO-OPS) API
https://api.tidesandcurrents.noaa.gov/api/prod/
"""

from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import Union

import bs4
from bs4 import BeautifulSoup
import numpy
import pandas
from pandas import DataFrame
import requests
from shapely.geometry import box, MultiPolygon, Point, Polygon
import typepigeon
from xarray import Dataset


class COOPS_Product(Enum):
    WATER_LEVEL = (
        'water_level'
        # Preliminary or verified water levels, depending on availability.
    )
    AIR_TEMPERATURE = 'air_temperature'  # Air temperature as measured at the station.
    WATER_TEMPERATURE = 'water_temperature'  # Water temperature as measured at the station.
    WIND = 'wind'  # Wind speed, direction, and gusts as measured at the station.
    AIR_PRESSURE = 'air_pressure'  # Barometric pressure as measured at the station.
    AIR_GAP = 'air_gap'  # Air Gap (distance between a bridge and the water's surface) at the station.
    CONDUCTIVITY = 'conductivity'  # The water's conductivity as measured at the station.
    VISIBILITY = 'visibility'  # Visibility from the station's visibility sensor. A measure of atmospheric clarity.
    HUMIDITY = 'humidity'  # Relative humidity as measured at the station.
    SALINITY = 'salinity'  # Salinity and specific gravity data for the station.
    HOURLY_HEIGHT = 'hourly_height'  # Verified hourly height water level data for the station.
    HIGH_LOW = 'high_low'  # Verified high/low water level data for the station.
    DAILY_MEAN = 'daily_mean'  # Verified daily mean water level data for the station.
    MONTHLY_MEAN = 'monthly_mean'  # Verified monthly mean water level data for the station.
    ONE_MINUTE_WATER_LEVEL = (
        'one_minute_water_level'
        # One minute water level data for the station.
    )
    PREDICTIONS = 'predictions'  # 6 minute predictions water level data for the station.*
    DATUMS = 'datums'  # datums data for the stations.
    CURRENTS = 'currents'  # Currents data for currents stations.
    CURRENTS_PREDICTIONS = (
        'currents_predictions'
        # Currents predictions data for currents predictions stations.
    )


class COOPS_TidalDatum(Enum):
    CRD = 'CRD'  # Columbia River Datum
    IGLD = 'IGLD'  # International Great Lakes Datum
    LWD = 'LWD'  # Great Lakes Low Water Datum (Chart Datum)
    MHHW = 'MHHW'  # Mean Higher High Water
    MHW = 'MHW'  # Mean High Water
    MTL = 'MTL'  # Mean Tide Level
    MSL = 'MSL'  # Mean Sea Level
    MLW = 'MLW'  # Mean Low Water
    MLLW = 'MLLW'  # Mean Lower Low Water
    NAVD = 'NAVD'  # North American Vertical Datum
    STND = 'STND'  # Station Datum


class COOP_VelocityType(Enum):
    SPEED_DIR = 'speed_dir'  # Return results for speed and dirction
    DEFAULT = 'default'  # Return results for velocity major, mean flood direction and mean ebb dirction


class COOPS_Units(Enum):
    METRIC = 'metric'
    ENGLISH = 'english'


class COOPS_TimeZone(Enum):
    GMT = 'gmt'  # Greenwich Mean Time
    LST = 'lst'  # Local Standard Time. The time local to the requested station.
    LST_LDT = 'lst_ldt'  # Local Standard/Local Daylight Time. The time local to the requested station.


class COOPS_Interval(Enum):
    H = 'h'  # Hourly Met data and harmonic predictions will be returned
    HILO = 'hilo'  # High/Low tide predictions for all stations.


class COOPS_StationType(Enum):
    CURRENT = 'current'
    HISTORICAL = 'historical'


class COOPS_Station:
    """
    a specific CO-OPS station
    """

    def __init__(self, id: Union[int, str]):
        """
        :param id: NOS ID, NWS ID, or station name

        from NOS ID:

        >>> COOPS_Station(1612480)
        COOPS_Station(1612480)

        from NWS ID:

        >>> COOPS_Station('OOUH1')
        COOPS_Station(1612340)

        from station name:

        >>> COOPS_Station('San Mateo Bridge')
        COOPS_Station(9414458)
        """

        self.__query = None

        stations = coops_stations()
        if id in stations.index:
            station = stations.loc[id]
        elif id in stations['nws_id'].values:
            station = stations[stations['nws_id'] == id]
        elif id in stations['name'].values:
            station = stations[stations['name'] == id]
        else:
            station = None

        if station is not None and len(station) > 0:
            self.removed_date = station['removed']

            if isinstance(station, DataFrame):
                station = station.iloc[0]

            self.nos_id = station.name
            self.nws_id = station['nws_id']
            self.location = Point(station['x'], station['y'])
            self.state = station['state']
            self.name = station['name']
        else:
            raise ValueError(f'station with "{id}" not found')

    @property
    @lru_cache(maxsize=None)
    def constituents(self) -> DataFrame:
        """
        :return: table of tidal constituents for the current station
        """

        url = f'https://tidesandcurrents.noaa.gov/harcon.html?id={self.nos_id}'
        response = requests.get(url)
        soup = BeautifulSoup(response.content, features='html.parser')
        table = soup.find_all('table', {'class': 'table table-striped'})
        if len(table) > 0:
            table = table[0]
            columns = [field.text for field in table.find('thead').find('tr').find_all('th')]
            constituents = []
            for row in table.find_all('tr')[1:]:
                constituents.append([entry.text for entry in row.find_all('td')])
            constituents = DataFrame(constituents, columns=columns)
            constituents.rename(columns={'Constituent #': '#'}, inplace=True)
            constituents = constituents.astype(
                {
                    '#': numpy.int32,
                    'Amplitude': numpy.float64,
                    'Phase': numpy.float64,
                    'Speed': numpy.float64,
                }
            )
        else:
            constituents = DataFrame(columns=['#', 'Amplitude', 'Phase', 'Speed'])

        constituents.set_index('#', inplace=True)
        return constituents

    def get(
        self,
        start_date: datetime,
        end_date: datetime = None,
        product: COOPS_Product = None,
        datum: COOPS_TidalDatum = None,
        units: COOPS_Units = None,
        time_zone: COOPS_TimeZone = None,
        interval: COOPS_Interval = None,
    ) -> Dataset:
        """
        retrieve data for the current station within the specified parameters

        :param start_date: start date
        :param end_date: end date
        :param product: CO-OPS product
        :param datum: tidal datum
        :param units: either ``metric`` or ``english``
        :param time_zone: time zone of data
        :param interval: time interval of data
        :return: data for the current station within the specified parameters

        >>> COOPS_Station(8632200).get(start_date=datetime(2018, 9, 13), end_date=datetime(2018, 9, 16, 12))
        <xarray.Dataset>
        Dimensions:  (t: 841)
        Coordinates:
          * t        (t) datetime64[ns] 2018-09-13 ... 2018-09-16T12:00:00
            nos_id   int64 8632200
            nws_id   <U5 'KPTV2'
            x        float64 -75.99
            y        float64 37.17
        Data variables:
            v        (t) float32 1.67 1.694 1.73 1.751 1.778 ... 1.602 1.597 1.607 1.605
            s        (t) float32 0.026 0.027 0.034 0.03 ... 0.018 0.018 0.019 0.021
            f        (t) object '0,0,0,0' '0,0,0,0' '0,0,0,0' ... '0,0,0,0' '0,0,0,0'
            q        (t) object 'v' 'v' 'v' 'v' 'v' 'v' 'v' ... 'v' 'v' 'v' 'v' 'v' 'v'
        """

        if self.__query is None:
            self.__query = COOPS_Query(
                station=self,
                start_date=start_date,
                end_date=end_date,
                product=product,
                datum=datum,
                units=units,
                time_zone=time_zone,
                interval=interval,
            )
        else:
            if start_date is None:
                self.__query.start_date = start_date
            if end_date is None:
                self.__query.end_date = end_date
            if product is None:
                self.__query.product = product
            if datum is None:
                self.__query.datum = datum
            if units is None:
                self.__query.units = units
            if time_zone is None:
                self.__query.time_zone = time_zone
            if interval is None:
                self.__query.interval = interval

        data = self.__query.data

        return Dataset(
            data,
            coords={
                'nos_id': self.nos_id,
                'nws_id': self.nws_id,
                'x': self.location.x,
                'y': self.location.y,
            },
        )

    def __str__(self) -> str:
        return f'{self.__class__.__name__} - {self.nos_id} ({self.name}) - {self.location}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.nos_id})'


class COOPS_Query:
    """
    abstraction of an individual query to the CO-OPS API
    https://api.tidesandcurrents.noaa.gov/api/prod/
    """

    URL = 'https://tidesandcurrents.noaa.gov/api/datagetter?'

    def __init__(
        self,
        station: int,
        start_date: datetime,
        end_date: datetime = None,
        product: COOPS_Product = None,
        datum: COOPS_TidalDatum = None,
        units: COOPS_Units = None,
        time_zone: COOPS_TimeZone = None,
        interval: COOPS_Interval = None,
    ):
        """
        instantiate a new query with the specified parameters

        :param station: NOS station ID
        :param start_date: start date
        :param end_date: end date
        :param product: CO-OPS product
        :param datum: station datum
        :param units: one of `metric`, `english`
        :param time_zone: time zone of data
        :param interval: time interval of data
        :return: data for the current station within the specified parameters

        >>> COOPS_Query(1612480, start_date='2022-01-01', end_date='2022-01-03')
        COOPS_Query(1612480, datetime.datetime(2022, 1, 1, 0, 0), datetime.datetime(2022, 1, 3, 0, 0), 'water_level', 'MLLW', 'metric', 'gmt', 'h')
        """

        if not isinstance(station, COOPS_Station):
            station = COOPS_Station(station)
        station = station.nos_id
        if end_date is None:
            end_date = datetime.today()
        if product is None:
            product = COOPS_Product.WATER_LEVEL
        if datum is None:
            datum = COOPS_TidalDatum.STND
        if units is None:
            units = COOPS_Units.METRIC
        if time_zone is None:
            time_zone = COOPS_TimeZone.GMT
        if interval is None:
            interval = COOPS_Interval.H

        self.station = station
        self.start_date = start_date
        self.end_date = end_date
        self.product = product
        self.datum = datum
        self.units = units
        self.time_zone = time_zone
        self.interval = interval

        self.__previous_query = None
        self.__error = None

    @property
    def start_date(self) -> datetime:
        return self.__start_date

    @start_date.setter
    def start_date(self, start_date: datetime):
        self.__start_date = typepigeon.convert_value(start_date, datetime)

    @property
    def end_date(self) -> datetime:
        return self.__end_date

    @end_date.setter
    def end_date(self, end_date: datetime):
        self.__end_date = typepigeon.convert_value(end_date, datetime)

    @property
    def product(self) -> COOPS_Product:
        return self.__product

    @product.setter
    def product(self, product: COOPS_Product):
        self.__product = typepigeon.convert_value(product, COOPS_Product)

    @property
    def datum(self) -> COOPS_TidalDatum:
        return self.__datum

    @datum.setter
    def datum(self, datum: COOPS_TidalDatum):
        self.__datum = typepigeon.convert_value(datum, COOPS_TidalDatum)

    @property
    def units(self) -> COOPS_Units:
        return self.__units

    @units.setter
    def units(self, units: COOPS_Units):
        self.__units = typepigeon.convert_value(units, COOPS_Units)

    @property
    def time_zone(self) -> COOPS_TimeZone:
        return self.__time_zone

    @time_zone.setter
    def time_zone(self, time_zone: COOPS_TimeZone):
        self.__time_zone = typepigeon.convert_value(time_zone, COOPS_TimeZone)

    @property
    def interval(self) -> COOPS_Interval:
        return self.__interval

    @interval.setter
    def interval(self, interval: COOPS_Interval):
        self.__interval = typepigeon.convert_value(interval, COOPS_Interval)

    @property
    def query(self):
        self.__error = None

        start_date = self.start_date
        if start_date is not None and not isinstance(start_date, str):
            start_date = f'{self.start_date:%Y%m%d %H:%M}'
        product = self.product
        if isinstance(product, Enum):
            product = product.value
        datum = self.datum
        if isinstance(datum, Enum):
            datum = datum.value
        units = self.units
        if isinstance(units, Enum):
            units = units.value
        time_zone = self.time_zone
        if isinstance(time_zone, Enum):
            time_zone = time_zone.value
        interval = self.interval
        if isinstance(interval, Enum):
            interval = interval.value

        return {
            'station': self.station,
            'begin_date': start_date,
            'end_date': f'{self.end_date:%Y%m%d %H:%M}',
            'product': product,
            'datum': datum,
            'units': units,
            'time_zone': time_zone,
            'interval': interval,
            'format': 'json',
            'application': 'noaa/nos/csdl/stormevents',
        }

    @property
    def data(self) -> DataFrame:
        """
        :return: data for the current query parameters

        >>> COOPS_Query(1612480, start_date='2022-01-01', end_date='2022-01-03').data
                                 v      s        f  q
        t
        2022-01-01 00:00:00  1.193  0.002  0,0,0,0  p
        2022-01-01 00:06:00  1.180  0.002  1,0,0,0  p
        2022-01-01 00:12:00  1.167  0.002  0,0,0,0  p
        2022-01-01 00:18:00  1.156  0.003  1,0,0,0  p
        2022-01-01 00:24:00  1.147  0.003  0,0,0,0  p
        ...                    ...    ...      ... ..
        2022-01-02 23:36:00  1.229  0.004  1,0,0,0  p
        2022-01-02 23:42:00  1.219  0.003  1,0,0,0  p
        2022-01-02 23:48:00  1.223  0.004  1,0,0,0  p
        2022-01-02 23:54:00  1.217  0.004  0,0,0,0  p
        2022-01-03 00:00:00  1.207  0.002  0,0,0,0  p
        [481 rows x 4 columns]
        """

        if self.__previous_query is None or self.query != self.__previous_query:
            response = requests.get(self.URL, params=self.query)
            data = response.json()
            fields = ['t', 'v', 's', 'f', 'q']
            if 'error' in data:
                self.__error = data['error']['message']
                data = DataFrame(columns=fields)
            else:
                data = DataFrame(data['data'], columns=fields)
                data = data.astype(
                    {'v': numpy.float32, 's': numpy.float32, 'f': 'string', 'q': 'string'},
                    errors='ignore',
                )
                data['t'] = pandas.to_datetime(data['t'])

            data.set_index('t', inplace=True)
            self.__data = data
        return self.__data

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(repr(value) for value in (self.station, self.start_date, self.end_date, self.product.value, self.datum.value, self.units.value, self.time_zone.value, self.interval.value))})'


@lru_cache(maxsize=None)
def __coops_stations_html_tables() -> bs4.element.ResultSet:
    response = requests.get(
        'https://access.co-ops.nos.noaa.gov/nwsproducts.html?type=current',
    )
    soup = BeautifulSoup(response.content, features='html.parser')
    return soup.find_all('div', {'class': 'table-responsive'})


@lru_cache(maxsize=None)
def coops_stations(station_type: COOPS_StationType = None) -> DataFrame:
    """
    retrieve a list of CO-OPS stations with associated metadata

    :param station_type: one of ``current`` or ``historical``
    :return: data frame of stations

    >>> coops_stations()
            nws_id         x          y                          name state removed
    nos_id
    1600012  46125  122.6250  37.750000                     QREB buoy           NaT
    1611400  NWWH1 -159.3750  21.953125                    Nawiliwili    HI     NaT
    1612340  OOUH1 -157.8750  21.312500                      Honolulu    HI     NaT
    1612480  MOKH1 -157.7500  21.437500                      Mokuoloe    HI     NaT
    1615680  KLIH1 -156.5000  20.890625       Kahului, Kahului Harbor    HI     NaT
    ...        ...       ...        ...                           ...   ...     ...
    9759394  MGZP4  -67.1875  18.218750                      Mayaguez    PR     NaT
    9759938  MISP4  -67.9375  18.093750                   Mona Island           NaT
    9761115  BARA9  -61.8125  17.593750                       Barbuda           NaT
    9999530  FRCB6  -64.6875  32.375000  Bermuda, Ferry Reach Channel           NaT
    9999531         -93.3125  29.765625        Calcasieu Test Station    LA     NaT
    [363 rows x 6 columns]
    """

    if station_type is None:
        station_type = COOPS_StationType.CURRENT
    elif not isinstance(station_type, COOPS_StationType):
        station_type = typepigeon.convert_value(station_type, COOPS_StationType)

    if station_type == COOPS_StationType.CURRENT:
        table_id = 'NWSTable'
        table_index = 0
    else:
        table_id = 'HistNWSTable'
        table_index = 1

    tables = __coops_stations_html_tables()

    stations_table = tables[table_index].find('table', {'id': table_id}).find_all('tr')

    stations_columns = [field.text for field in stations_table[0].find_all('th')]
    stations = []
    for station in stations_table[1:]:
        stations.append([value.text.strip() for value in station.find_all('td')])

    stations = DataFrame(stations, columns=stations_columns)
    stations.rename(
        columns={
            'NOS ID': 'nos_id',
            'NWS ID': 'nws_id',
            'Latitude': 'y',
            'Longitude': 'x',
            'State': 'state',
            'Station Name': 'name',
        },
        inplace=True,
    )
    stations = stations.astype(
        {
            'nos_id': numpy.int32,
            'nws_id': 'string',
            'x': numpy.float16,
            'y': numpy.float16,
            'state': 'string',
            'name': 'string',
        },
        copy=False,
    )
    stations.set_index('nos_id', inplace=True)

    if station_type == COOPS_StationType.HISTORICAL:
        stations.rename(columns={'Removed Date/Time': 'removed'}, inplace=True)
        stations['removed'] = pandas.to_datetime(stations['removed'])
    else:
        stations['removed'] = pandas.to_datetime(numpy.nan)

    return stations[['nws_id', 'x', 'y', 'name', 'state', 'removed']]


def coops_stations_within_region(
    region: Polygon, station_type: COOPS_StationType = None,
) -> DataFrame:
    """
    retrieve all stations within the specified region of interest

    :param region: polygon or multipolygon denoting region of interest
    :param station_type: one of ``current`` or ``historical``
    :return: data frame of stations within the specified region

    .. code-block:: python

        from shapely.geometry import Polygon

        polygon = Polygon(...)

        stations = coops_stations_within_region(region=polygon)

    """

    all_stations = coops_stations(station_type)
    points = [Point(*row) for row in all_stations[['x', 'y']].values]

    stations_within_region = all_stations.iloc[
        [index for index, point in enumerate(points) if point.within(region)]
    ]

    return stations_within_region


def coops_stations_within_bounds(
    minx: float, miny: float, maxx: float, maxy: float, station_type: COOPS_StationType = None,
) -> DataFrame:
    return coops_stations_within_region(
        region=box(minx=minx, miny=miny, maxx=maxx, maxy=maxy), station_type=station_type
    )


def coops_data_within_region(
    region: Union[Polygon, MultiPolygon],
    start_date: datetime,
    end_date: datetime = None,
    product: COOPS_Product = None,
    datum: COOPS_TidalDatum = None,
    units: COOPS_Units = None,
    time_zone: COOPS_TimeZone = None,
    interval: COOPS_Interval = None,
    station_type: COOPS_StationType = None,
):
    """
    retrieve CO-OPS data from within the specified region of interest

    :param region: polygon or multipolygon denoting region of interest
    :param start_date: start date of CO-OPS query
    :param end_date: start date of CO-OPS query
    :param product: CO-OPS product
    :param datum: tidal datum
    :param units: one of ``metric`` or ``english``
    :param time_zone: station time zone
    :param interval: data time interval
    :param station_type: either ``current`` or ``historical``
    :return: data frame of data within the specified region

    .. code-block:: python

        from datetime import datetime, timedelta

        from shapely.geometry import MultiPolygon

        polygon = MultiPolygon(...)

        coops_data_within_region(region=polygon, start_date=datetime.now() - timedelta(days=2), end_date=datetime.now())

    """

    stations = coops_stations_within_region(region=region, station_type=station_type)
    return pandas.concat(
        [
            COOPS_Station(station).get(
                start_date=start_date,
                end_date=end_date,
                product=product,
                datum=datum,
                units=units,
                time_zone=time_zone,
                interval=interval,
            )
            for station in stations
        ]
    )
