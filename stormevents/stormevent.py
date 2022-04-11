from datetime import datetime
from functools import lru_cache
from os import PathLike
from typing import List

import pandas
from shapely import ops
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import shape as shapely_shape
import xarray
from xarray import Dataset

from stormevents.coops.tidalstations import (
    COOPS_Interval,
    COOPS_Product,
    COOPS_Station,
    coops_stations_within_region,
    COOPS_StationStatus,
    COOPS_TidalDatum,
    COOPS_TimeZone,
    COOPS_Units,
)
from stormevents.nhc import nhc_storms, VortexTrack
from stormevents.nhc.atcf import ATCF_Advisory, ATCF_FileDeck, ATCF_Mode
from stormevents.usgs import usgs_flood_storms, USGS_StormEvent
from stormevents.utilities import relative_to_time_interval, subset_time_interval


class StormEvent:
    """
    The ``StormEvent`` class can be used to retrieve data
    related to any arbitrary named storm event.
    """

    def __init__(
        self, name: str, year: int, start_date: datetime = None, end_date: datetime = None
    ):
        """
        :param name: storm name
        :param year: storm year
        :param start_date: starting time
        :param end_date: ending time

        >>> StormEvent('florence', 2018)
        StormEvent(name='FLORENCE', year=2018, start_date=Timestamp('2018-08-30 06:00:00'), end_date=Timestamp('2018-09-18 12:00:00'))

        >>> StormEvent('paine', 2016, start_date='2016-09-18', end_date=datetime(2016, 9, 19, 12))
        StormEvent(name='PAINE', year=2016, start_date=Timestamp('2016-09-18 00:00:00'), end_date=datetime.datetime(2016, 9, 19, 12, 0))

        >>> StormEvent('florence', 2018, start_date=timedelta(days=2))
        StormEvent(name='FLORENCE', year=2018, start_date=Timestamp('2018-09-01 06:00:00'), end_date=Timestamp('2018-09-18 12:00:00'))

        >>> StormEvent('henri', 2021, start_date=timedelta(days=-3), end_date=timedelta(days=-2))
        StormEvent(name='HENRI', year=2021, start_date=Timestamp('2021-08-21 12:00:00'), end_date=Timestamp('2021-08-22 12:00:00'))

        >>> StormEvent('ida', 2021, end_date=timedelta(days=2))
        StormEvent(name='IDA', year=2021, start_date=Timestamp('2021-08-27 18:00:00'), end_date=Timestamp('2021-08-29 18:00:00'))
        """

        storms = nhc_storms(year=year)
        storms = storms[storms['name'].str.contains(name.upper())]
        if len(storms) > 0:
            self.__entry = storms.iloc[0]
        else:
            raise ValueError(f'storm "{name} {year}" not found in NHC database')

        self.__usgs_id = None
        self.__is_usgs_flood_event = True
        self.__high_water_marks = None
        self.__previous_configuration = {'name': self.name, 'year': self.year}

        self.start_date = start_date
        self.end_date = end_date

    @classmethod
    def from_nhc_code(
        cls, nhc_code: str, start_date: datetime = None, end_date: datetime = None
    ) -> 'StormEvent':
        """
        retrieve storm information from the NHC code
        :param nhc_code: NHC code
        :param start_date: starting time
        :param end_date: ending time
        :return: storm object

        >>> StormEvent.from_nhc_code('EP172016')
        StormEvent(name='PAINE', year=2016, start_date=Timestamp('2016-09-18 00:00:00'), end_date=Timestamp('2016-09-21 12:00:00'))
        """

        try:
            year = int(nhc_code[-4:])
        except:
            raise ValueError(f'unable to parse NHC code "{nhc_code}"')

        storms = nhc_storms(year=year)

        if nhc_code.upper() not in storms.index.values:
            raise ValueError(f'NHC code "{nhc_code}" does not exist in table')

        storm = storms.loc[nhc_code]
        return cls(
            name=storm['name'], year=storm['year'], start_date=start_date, end_date=end_date
        )

    @classmethod
    def from_usgs_id(
        cls,
        usgs_id: int,
        year: int = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> 'StormEvent':
        """
        retrieve storm information from the USGS flood event ID
        :param usgs_id: USGS flood event ID
        :param start_date: starting time
        :param end_date: ending time
        :return: storm object

        >>> StormEvent.from_usgs_id(310)
        StormEvent(name='HENRI', year=2021, start_date=Timestamp('2021-08-20 18:00:00'), end_date=Timestamp('2021-08-24 12:00:00'))
        """

        flood_events = usgs_flood_storms(year=year)

        if usgs_id in flood_events.index:
            flood_event = flood_events.loc[usgs_id]
            if start_date is None:
                start_date = flood_event['start_date']
            if end_date is None:
                end_date = flood_event['end_date']
            storm = cls(
                name=flood_event['nhc_name'],
                year=flood_event['year'],
                start_date=start_date,
                end_date=end_date,
            )
            storm.__usgs_id = usgs_id
            return storm
        else:
            raise ValueError(f'flood event "{usgs_id}" not found in USGS HWM database')

    @property
    def nhc_code(self) -> str:
        """
        :return: NHC code, for example `AL112013` for the 11th Atlantic storm in 2013, or `EP032011` for the 3rd Pacific storm in 2011
        """

        return self.__entry.name

    @property
    def usgs_id(self) -> int:
        """
        :return: USGS flood event ID
        """

        if self.__usgs_id is None and self.__is_usgs_flood_event:
            usgs_storm_events = usgs_flood_storms(year=self.year)

            if self.nhc_code in usgs_storm_events['nhc_code'].values:
                usgs_storm_event = usgs_storm_events.loc[
                    usgs_storm_events['nhc_code'] == self.nhc_code
                ]
                self.__usgs_id = usgs_storm_event.index[0]
            else:
                self.__is_usgs_flood_event = False
        return self.__usgs_id

    @property
    def name(self) -> str:
        return self.__entry['name'].strip()

    @property
    def year(self) -> int:
        return self.__entry['year']

    @property
    def basin(self) -> str:
        """
        :return: basin in which storm occurred
        """

        return self.__entry['basin'].strip()

    @property
    def number(self) -> int:
        """
        :return: ordinal number of storm in the year
        """

        return self.__entry['number']

    @property
    def start_date(self) -> datetime:
        return self.__start_date

    @start_date.setter
    def start_date(self, start_date: datetime):
        if start_date is None:
            start_date = self.__data_start
        else:
            # interpret timedelta as a temporal movement around start / end
            start_date, _ = subset_time_interval(
                start=self.__data_start, end=self.__data_end, subset_start=start_date,
            )
        self.__start_date = start_date

    @property
    @lru_cache(maxsize=None)
    def __data_start(self) -> datetime:
        data_start = self.__entry['start_date']
        if pandas.isna(data_start):
            data_start = VortexTrack.from_storm_name(self.name, self.year).start_date
        return data_start

    @property
    def end_date(self) -> datetime:
        return self.__end_date

    @end_date.setter
    def end_date(self, end_date: datetime):
        if end_date is None:
            end_date = self.__data_end
        else:
            # interpret timedelta as a temporal movement around start / end
            _, end_date = subset_time_interval(
                start=self.__data_start, end=self.__data_end, subset_end=end_date,
            )
        self.__end_date = end_date

    @property
    @lru_cache(maxsize=None)
    def __data_end(self) -> datetime:
        data_end = self.__entry['end_date']
        if pandas.isna(data_end):
            data_end = VortexTrack.from_storm_name(self.name, self.year).end_date
        return data_end

    def track(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        file_deck: ATCF_FileDeck = None,
        advisories: List[ATCF_Advisory] = None,
        filename: PathLike = None,
    ) -> VortexTrack:
        """
        retrieve NHC ATCF track data

        :param start_date: start date
        :param end_date: end date
        :param file_deck: ATCF file deck
        :param advisories: ATCF advisory types
        :param filename: file path to ``fort.22``
        :return: vortex track

        >>> storm = StormEvent('florence', 2018)
        >>> storm.track()
        VortexTrack('AL062018', Timestamp('2018-08-30 06:00:00'), Timestamp('2018-09-18 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.HISTORICAL: 'ARCHIVE'>, [<ATCF_Advisory.BEST: 'BEST'>], None)
        """

        if start_date is None:
            start_date = self.start_date
        if end_date is None:
            end_date = self.end_date

        if filename is not None:
            track = VortexTrack.from_file(filename)
        else:
            track = VortexTrack.from_storm_name(
                name=self.name,
                year=self.year,
                start_date=start_date,
                end_date=end_date,
                file_deck=file_deck,
                advisories=advisories,
            )
        return track

    @property
    def flood_event(self) -> USGS_StormEvent:
        """
        :return: USGS high-water marks (HWMs) for this storm event

        >>> storm = StormEvent('florence', 2018)
        >>> flood = storm.flood_event
        >>> flood.high_water_marks()
                 latitude  longitude          eventName  ... siteZone peak_summary_id                    geometry
        hwm_id                                           ...                                                     
        33496   37.298440 -80.007750  Florence Sep 2018  ...      NaN             NaN  POINT (-80.00775 37.29844)
        33497   33.699720 -78.936940  Florence Sep 2018  ...      NaN             NaN  POINT (-78.93694 33.69972)
        33498   33.758610 -78.792780  Florence Sep 2018  ...      NaN             NaN  POINT (-78.79278 33.75861)
        33499   33.641389 -78.947778  Florence Sep 2018  ...                      NaN  POINT (-78.94778 33.64139)
        33500   33.602500 -78.973889  Florence Sep 2018  ...                      NaN  POINT (-78.97389 33.60250)
        ...           ...        ...                ...  ...      ...             ...                         ...
        34872   35.534641 -77.038183  Florence Sep 2018  ...      NaN             NaN  POINT (-77.03818 35.53464)
        34873   35.125000 -77.050044  Florence Sep 2018  ...      NaN             NaN  POINT (-77.05004 35.12500)
        34874   35.917467 -76.254367  Florence Sep 2018  ...      NaN             NaN  POINT (-76.25437 35.91747)
        34875   35.111000 -77.037851  Florence Sep 2018  ...      NaN             NaN  POINT (-77.03785 35.11100)
        34876   35.301135 -77.264727  Florence Sep 2018  ...      NaN             NaN  POINT (-77.26473 35.30114)
        [644 rows x 53 columns]
        """

        configuration = {'name': self.name, 'year': self.year}
        if self.__high_water_marks is None or configuration != self.__previous_configuration:
            self.__high_water_marks = USGS_StormEvent(name=self.name, year=self.year)
        return self.__high_water_marks

    def coops_product_within_isotach(
        self,
        product: COOPS_Product,
        wind_speed: int,
        advisories: List[ATCF_Advisory] = None,
        station_type: COOPS_StationStatus = None,
        start_date: datetime = None,
        end_date: datetime = None,
        datum: COOPS_TidalDatum = None,
        units: COOPS_Units = None,
        time_zone: COOPS_TimeZone = None,
        interval: COOPS_Interval = None,
        track: VortexTrack = None,
    ) -> Dataset:
        """
        retrieve CO-OPS tidal station data from within the specified polygon

        :param product: CO-OPS product
        :param wind_speed: wind speed in knots (one of ``34``, ``50``, or ``64``)
        :param advisories: ATCF advisory types
        :param start_date: start date
        :param end_date: end date
        :param station_type: either ``current`` or ``historical``
        :param datum: tidal datum
        :param units: either ``metric`` or ``english``
        :param time_zone: time zone
        :param interval: time interval
        :param track: vortex track object or file path to ``fort.22``
        :return: CO-OPS station data

        >>> storm = StormEvent('florence', 2018)
        >>> storm.coops_product_within_isotach('water_level', wind_speed=34, start_date='2018-09-12 14:03:00', end_date='2018-09-14')
        <xarray.Dataset>
        Dimensions:  (nos_id: 7, t: 340)
        Coordinates:
          * nos_id   (nos_id) int64 8651370 8652587 8654467 ... 8658120 8658163 8661070
          * t        (t) datetime64[ns] 2018-09-12T14:06:00 ... 2018-09-14
            nws_id   (nos_id) <U5 'DUKN7' 'ORIN7' 'HCGN7' ... 'WLON7' 'JMPN7' 'MROS1'
            x        (nos_id) float64 -75.75 -75.56 -75.69 -76.69 -77.94 -77.81 -78.94
            y        (nos_id) float64 36.19 35.78 35.22 34.72 34.22 34.22 33.66
        Data variables:
            v        (nos_id, t) float32 7.181 7.199 7.144 7.156 ... 9.6 9.634 9.686
            s        (nos_id, t) float32 0.317 0.36 0.31 0.318 ... 0.049 0.047 0.054
            f        (nos_id, t) object '0,0,0,0' '0,0,0,0' ... '0,0,0,0' '0,0,0,0'
            q        (nos_id, t) object 'v' 'v' 'v' 'v' 'v' 'v' ... 'v' 'v' 'v' 'v' 'v'
        """

        if isinstance(track, VortexTrack):
            track.start_date = start_date
            track.end_date = end_date
            track.advisories = advisories
        else:
            track = self.track(
                start_date=start_date, end_date=end_date, filename=track, advisories=advisories
            )

        polygons = []
        wind_swaths = track.wind_swaths(wind_speed)
        for advisory, advisory_wind_swaths in wind_swaths.items():
            polygons.append(ops.unary_union(list(advisory_wind_swaths.values())))
        region = ops.unary_union(polygons)

        return self.coops_product_within_region(
            region=region,
            station_type=station_type,
            start_date=start_date,
            end_date=end_date,
            product=product,
            datum=datum,
            units=units,
            time_zone=time_zone,
            interval=interval,
        )

    def coops_product_within_region(
        self,
        product: COOPS_Product,
        region: Polygon,
        start_date: datetime = None,
        end_date: datetime = None,
        station_type: COOPS_StationStatus = None,
        datum: COOPS_TidalDatum = None,
        units: COOPS_Units = None,
        time_zone: COOPS_TimeZone = None,
        interval: COOPS_Interval = None,
    ) -> Dataset:
        """
        retrieve CO-OPS tidal station data from within the specified region

        :param product: CO-OPS product; one of ``water_level``, ``air_temperature``, ``water_temperature``, ``wind``, ``air_pressure``, ``air_gap``, ``conductivity``, ``visibility``, ``humidity``, ``salinity``, ``hourly_height``, ``high_low``, ``daily_mean``, ``monthly_mean``, ``one_minute_water_level``, ``predictions``, ``datums``, ``currents``, ``currents_predictions``
        :param region: a Shapely polygon denoting the region of interest
        :param start_date: start date
        :param end_date: end date
        :param station_type: either ``current`` or ``historical``
        :param datum: tidal datum
        :param units: either ``metric`` or ``english``
        :param time_zone: time zone
        :param interval: time interval
        :return: CO-OPS station data

        >>> import shapely
        >>> storm = StormEvent('florence', 2018)
        >>> region = shapely.geometry.box(*storm.track().linestrings.bounds)
        >>> storm.coops_product_within_region('water_level', region=region, start_date='2018-09-12 14:03:00', end_date='2018-09-14')
        <xarray.Dataset>
        Dimensions:  (nos_id: 89, t: 340)
        Coordinates:
          * nos_id   (nos_id) int64 2695535 2695540 8447386 ... 9759394 9759938 9761115
          * t        (t) datetime64[ns] 2018-09-12T14:06:00 ... 2018-09-14
            nws_id   (nos_id) <U5 'FRCB6' 'BEPB6' 'FRVM3' ... 'MGZP4' 'MISP4' 'BARA9'
            x        (nos_id) float64 -64.69 -64.69 -71.19 ... -67.19 -67.94 -61.81
            y        (nos_id) float64 32.38 32.38 41.72 41.69 ... 18.22 18.09 17.59
        Data variables:
            v        (nos_id, t) float32 1.956 1.952 1.948 1.939 ... 8.916 8.901 8.898
            s        (nos_id, t) object 0.007000000216066837 ... '0.041'
            f        (nos_id, t) object '0,0,0,0' '0,0,0,0' ... '0,0,0,0' '0,0,0,0'
            q        (nos_id, t) object 'v' 'v' 'v' 'v' 'v' 'v' ... 'p' 'p' 'p' 'p' 'p'
        """

        if not isinstance(region, BaseGeometry):
            region = shapely_shape(region)

        if start_date is None:
            start_date = self.start_date
        else:
            start_date = relative_to_time_interval(
                start=self.start_date, end=self.end_date, relative=start_date
            )
        if end_date is None:
            end_date = self.end_date
        else:
            end_date = relative_to_time_interval(
                start=self.start_date, end=self.end_date, relative=end_date
            )

        stations = coops_stations_within_region(region=region, station_status=station_type)

        if len(stations) > 0:
            stations_data = []
            for station in stations.index:
                station_data = COOPS_Station(station).product(
                    product=product,
                    start_date=start_date,
                    end_date=end_date,
                    datum=datum,
                    units=units,
                    time_zone=time_zone,
                    interval=interval,
                )
                if len(station_data['t']) > 0:
                    stations_data.append(station_data)
            stations_data = xarray.combine_nested(stations_data, concat_dim='nos_id')
        else:
            stations_data = Dataset(
                coords={'t': None, 'nos_id': None, 'nws_id': None, 'x': None, 'y': None}
            )

        return stations_data

    def __repr__(self) -> str:
        return (
            f'{self.__class__.__name__}('
            f'name={repr(self.name)}, '
            f'year={repr(self.year)}, '
            f'start_date={repr(self.start_date)}, '
            f'end_date={repr(self.end_date)}'
            f')'
        )
