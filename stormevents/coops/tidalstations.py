import calendar
import codecs
from collections.abc import Mapping
from datetime import datetime, timedelta
from enum import Enum
import json
import os

import appdirs
from bs4 import BeautifulSoup
import numpy
import numpy as np
import requests
from typepigeon import convert_value


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


class COOPS_Query:
    URL = 'https://tidesandcurrents.noaa.gov/api/datagetter?'

    def __init__(
        self,
        station_id: int,
        start_date: datetime,
        end_date: datetime,
        product: COOPS_Product,
        datum: COOPS_TidalDatum = None,
        units: COOPS_Units = None,
        time_zone: COOPS_TimeZone = None,
        interval: COOPS_Interval = None,
    ):
        if datum is None:
            datum = COOPS_TidalDatum.NAVD
        if time_zone is None:
            time_zone = COOPS_TimeZone.GMT
        if interval is None:
            interval = COOPS_Interval.H

        self.station_id = station_id
        self.start_date = start_date
        self.end_date = end_date
        self.product = product
        self.datum = datum
        self.units = units
        self.time_zone = time_zone
        self.interval = interval

    @property
    def query(self):
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
            'station': self.station_id,
            'begin_date': f'{self.start_date:%Y%m%d %H:%M}',
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
    def get(self):
        return requests.get(self.URL, params=self.query)


class TidalStations(Mapping):
    """
    interface with the NOAA Center for Operational Oceanographic Products and Services (CO-OPS) API
    https://api.tidesandcurrents.noaa.gov/api/prod/
    """

    url = 'https://tidesandcurrents.noaa.gov/api/datagetter?'

    def __init__(self):
        self.__storage = dict()

    def __getitem__(self, key):
        return self.__storage[key]

    def __iter__(self):
        return iter(self.__storage)

    def __len__(self):
        return len(self.__storage.keys())

    def add_station(self, station_id, start_date, end_date):
        self.__storage[station_id] = self.__fetch_station_data(
            station_id, start_date, end_date
        )

    def __fetch_station_data(self, station_id, start_date, end_date):
        responses = list()
        for _start_date, _end_date in self.__get_datetime_segments(start_date, end_date):
            params = self.__get_params(station_id, _start_date, _end_date)
            try:
                r = requests.get(self.url, params=params, timeout=10.0)
                r.raise_for_status()
            except requests.exceptions.HTTPError as errh:
                print('Http Error:', errh)
            except requests.exceptions.ConnectionError as errc:
                print('Error Connecting:', errc)
            except requests.exceptions.Timeout as errt:
                print('Timeout Error:', errt)
            except requests.exceptions.RequestException as err:
                print('Unknown error.', err)
            responses.append(r)
        data = dict()
        data['datetime'] = list()
        data['values'] = list()
        for i, response in enumerate(responses):
            json_data = json.loads(response.text)
            if 'error' in json_data.keys():
                _start_date, _end_date = list(
                    self.__get_datetime_segments(start_date, end_date)
                )[i]
                data['datetime'].append(_start_date)
                data['values'].append(np.nan)
                data['datetime'].append(_end_date)
                data['values'].append(np.nan)
                continue
            if 'x' not in data.keys():
                data['x'] = float(json_data['metadata']['lon'])
            if 'y' not in data.keys():
                data['y'] = float(json_data['metadata']['lat'])
            if 'name' not in data.keys():
                data['name'] = json_data['metadata']['name']
            for _data in json_data['data']:
                data['datetime'].append(datetime.strptime(_data['t'], '%Y-%m-%d %H:%M'))
                try:
                    data['values'].append(float(_data['v']))
                except ValueError:
                    data['values'].append(np.nan)
        if 'name' not in data.keys():
            data['name'] = ""
        return data

    def __get_params(self, station_id, start_date, end_date):
        params = {
            'station': station_id,
            'begin_date': start_date.strftime('%Y%m%d %H:%M'),
            'end_date': end_date.strftime('%Y%m%d %H:%M'),
            'product': 'water_level',
            'datum': self.datum,
            'units': self.units,
            'time_zone': self.time_zone,
            'format': 'json',
            'application': 'noaa/nos/csdl/stormevent',
        }
        return params

    def __get_datetime_segments(self, start_date, end_date):
        """
        https://www.ianwootten.co.uk/2014/07/01/splitting-a-date-range-in-python/
        """

        segments = [(start_date, end_date)]
        interval = 2
        while np.any(
            [
                (_end_date - _start_date) > timedelta(days=31)
                for _start_date, _end_date in segments
            ]
        ):
            segments = [
                (from_datetime, to_datetime)
                for from_datetime, to_datetime in self.__get_datespan(
                    start_date, end_date, interval
                )
            ]
            interval += 1
        for _start_date, _end_date in segments:
            yield _start_date, _end_date

    def __get_datespan(self, startdate, enddate, interval):
        start_epoch = calendar.timegm(startdate.timetuple())
        end_epoch = calendar.timegm(enddate.timetuple())
        date_diff = end_epoch - start_epoch
        step = date_diff / interval
        delta = timedelta(seconds=step)
        currentdate = startdate
        while currentdate + delta <= enddate:
            todate = currentdate + delta
            yield currentdate, todate
            currentdate += delta

    @property
    def station(self):
        try:
            return self.__station
        except AttributeError:
            raise AttributeError('Must set station attribute.')

    @station.setter
    def station(self, station):
        assert station in self.__storage.keys()
        self.__station = station

    @property
    def datetime(self):
        return self.__storage[self.station]['datetime']

    @property
    def values(self):
        return self.__storage[self.station]['values']

    @property
    def name(self):
        try:
            return self.__storage[self.station]['name']
        except KeyError:
            return ""

    @property
    def start_date(self):
        return self.__start_date

    @start_date.setter
    def start_date(self, start_date):
        assert isinstance(start_date, datetime)
        self.__start_date = start_date

    @property
    def end_date(self):
        return self.__end_date

    @end_date.setter
    def end_date(self, end_date):
        assert isinstance(end_date, datetime)
        self.__end_date = end_date

    @property
    def datum(self):
        try:
            return self.__datum
        except AttributeError:
            return 'MSL'

    @datum.setter
    def datum(self, datum: COOPS_TidalDatum):
        if not isinstance(datum, COOPS_TidalDatum):
            datum = convert_value(datum, COOPS_TidalDatum)
        if datum == 'NAVD88':
            datum = 'NAVD'
        self.__datum = datum

    @property
    def units(self):
        try:
            return self.__units
        except AttributeError:
            return 'metric'

    @property
    def time_zone(self):
        try:
            return self.__time_zone
        except AttributeError:
            return 'gmt'

    # def _call_REST(self):
    #     for station in self.stations:
    #         self._params['station'] = station
    #         response = requests.get(self._url, params=self._params)
    #         response.raise_for_status()
    #         data = json.loads(response.text)
    #         if "data" in data.keys():
    #             time = list()
    #             values=list()
    #             s=list()
    #             metadata=data['metadata']
    #             for datapoint in data['data']:
    #                 time.append(datetime.strptime(datapoint['t'], '%Y-%m-%d %H:%M'))
    #                 try:
    #                         val = float(datapoint['v'])
    #                 except:
    #                         val = np.nan
    #                 values.append(val)
    #                 try:
    #                         _s=float(datapoint['s'])
    #                 except:
    #                         _s=np.nan
    #                 s.append(_s)
    #             self[station] = { "time"     : np.asarray(time),
    #                                                 "zeta"     : np.ma.masked_invalid(values),
    #                                                 "s"        : np.ma.masked_invalid(s),
    #                                                 "metadata" : metadata,
    #                                                 "datum"    : self._params["datum"]}


class HarmonicConstituents(dict):
    _rebuild = False

    def __init__(self, stations):
        super(HarmonicConstituents, self).__init__()
        self._stations = stations
        self._url = 'https://tidesandcurrents.noaa.gov/harcon.html?id='
        self._init_cache()
        self._init_stations()

    def _init_cache(self):
        self._cachedir = appdirs.user_cache_dir('harmonic_constituents')
        self._harmConstCache = self._cachedir + '/harm_const.json'
        if os.path.isfile(self._harmConstCache):
            self._cache = json.loads(open(self._harmConstCache, 'r').readlines()[0])
        else:
            self._cache = dict()

    def _init_stations(self):
        for station in self._stations:
            if station not in list(self._cache.keys()):
                self._add_station_to_cache(station)
            self[station] = self._cache[station]

    def _add_station_to_cache(self, station):
        # Parse from html, not available through rest.
        url = self._url + station
        soup = BeautifulSoup(requests.get(url).text, 'html.parser')
        table = soup.find('table')
        if table is not None:
            headings = [th.get_text().strip() for th in table.find('tr').find_all('th')]
            datasets = list()
            for row in table.find_all('tr')[1:]:
                datasets.append(
                    dict(zip(headings, (td.get_text() for td in row.find_all('td'))))
                )
            for dataset in datasets:
                if station not in self._cache.keys():
                    self._cache[station] = dict()
                if float(dataset['Amplitude']) != 0.0:
                    self._cache[station][dataset['Name']] = {
                        'amplitude': float(dataset['Amplitude']) / 3.28084,
                        'phase': float(dataset['Phase']),
                        'speed': float(dataset['Speed']),
                        'description': dataset['Description'],
                        'units': 'meters',
                    }
        else:
            self._cache[station] = None
        self._rebuild = True

    def __del__(self):
        if self._rebuild is True:
            with open(self._harmConstCache, 'wb') as f:
                json.dump(self._cache, codecs.getwriter('utf-8')(f), ensure_ascii=False)


class RESTWrapper:
    def __init__(
        self,
        product,
        start_date,
        end_date,
        format='json',
        units='metric',
        time_zone='gmt',
        datum='msl',
    ):
        self._product = product

        self._init_params()
        self._call_REST()

    def __getitem__(self, key):
        return self._storage[key]

    def __iter__(self):
        return iter(self._storage)

    def __len__(self):
        return len(self._storage.keys())

    def _init_params(self):
        self._params = {
            'format': 'json',
            'units': 'metric',
            'time_zone': 'gmt',
            'application': 'StormEvent',
            'datum': 'msl',
            'product': 'water_level',
        }
        self._url = 'https://tidesandcurrents.noaa.gov/api/datagetter?'
        self._params['begin_date'] = self.start_date.strftime('%Y%m%d %H:%M')
        self._params['end_date'] = self.end_date.strftime('%Y%m%d %H:%M')

    def _call_REST(self):
        for station in self.stations:
            self._params['station'] = station
            response = requests.get(self._url, params=self._params)
            response.raise_for_status()
            data = json.loads(response.text)
            if 'data' in data.keys():
                time = list()
                values = list()
                s = list()
                metadata = data['metadata']
                for datapoint in data['data']:
                    time.append(datetime.strptime(datapoint['t'], '%Y-%m-%d %H:%M'))
                    try:
                        val = float(datapoint['v'])
                    except:
                        val = numpy.nan
                    values.append(val)
                    try:
                        _s = float(datapoint['s'])
                    except:
                        _s = numpy.nan
                    s.append(_s)
                self[station] = {
                    'time': numpy.asarray(time),
                    'zeta': numpy.ma.masked_invalid(values),
                    's': numpy.ma.masked_invalid(s),
                    'metadata': metadata,
                    'datum': self._params['datum'],
                }


if __name__ == '__main__':
    test = TidalStations()

    print('done')
