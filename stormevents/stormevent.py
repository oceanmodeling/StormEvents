from datetime import datetime
from functools import lru_cache
from os import PathLike

import pandas
from pandas import DataFrame
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
import typepigeon
import xarray
from xarray import Dataset

from stormevents.coops import COOPS_Station, coops_stations_within_region
from stormevents.coops.tidalstations import (
    COOPS_Interval,
    COOPS_Product,
    COOPS_StationType,
    COOPS_TidalDatum,
    COOPS_TimeZone,
    COOPS_Units,
)
from stormevents.nhc import nhc_storms, VortexTrack
from stormevents.nhc.atcf import ATCF_FileDeck, ATCF_Mode
from stormevents.usgs import StormHighWaterMarks, usgs_highwatermark_storms
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
        StormEvent('FLORENCE', 2018)
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
        StormEvent('PAINE', 2016)
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
        StormEvent('HENRI', 2021)
        """

        usgs_storm_events = usgs_highwatermark_storms(year=year)

        if usgs_id in usgs_storm_events.index:
            usgs_storm_event = usgs_storm_events.loc[usgs_id]
            storm = cls(
                name=usgs_storm_event['nhc_name'],
                year=usgs_storm_event['year'],
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
        :return: NHC code
        """

        return self.__entry.name

    @property
    def usgs_id(self) -> int:
        """
        :return: USGS flood event ID
        """

        if self.__usgs_id is None and self.__is_usgs_flood_event:
            usgs_storm_events = usgs_highwatermark_storms(year=self.year)

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
        """
        :return: storm name
        """

        return self.__entry['name'].strip()

    @property
    def year(self) -> int:
        """
        :return: storm year
        """

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
        """
        :return: filter start time
        """

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
        """
        :return: filter end time
        """

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

    @lru_cache(maxsize=None)
    def track(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        file_deck: ATCF_FileDeck = None,
        mode: ATCF_Mode = None,
        record_type: str = None,
        filename: PathLike = None,
    ) -> VortexTrack:
        """
        retrieve NHC ATCF track data

        :param start_date: start date
        :param end_date: end date
        :param file_deck: ATCF file deck
        :param mode: ATCF mode
        :param record_type: ATCF record type
        :param filename: file path to ``fort.22``
        :return: vortex track
        """

        if start_date is None:
            start_date = self.start_date
        if end_date is None:
            end_date = self.end_date

        track = VortexTrack.from_storm_name(
            name=self.name,
            year=self.year,
            start_date=start_date,
            end_date=end_date,
            file_deck=file_deck,
            mode=mode,
            record_type=record_type,
            filename=filename,
        )
        return track

    @property
    def high_water_marks(self) -> DataFrame:
        """
        :return: USGS high-water marks (HWMs) for this storm event
        """

        configuration = {'name': self.name, 'year': self.year}
        if self.__high_water_marks is None or configuration != self.__previous_configuration:
            self.__high_water_marks = StormHighWaterMarks(name=self.name, year=self.year).data
        return self.__high_water_marks

    @lru_cache(maxsize=None)
    def tidal_data_within_isotach(
        self,
        wind_speed: int,
        station_type: COOPS_StationType = None,
        start_date: datetime = None,
        end_date: datetime = None,
        product: COOPS_Product = None,
        datum: COOPS_TidalDatum = None,
        units: COOPS_Units = None,
        time_zone: COOPS_TimeZone = None,
        interval: COOPS_Interval = None,
        track: VortexTrack = None,
    ) -> Dataset:
        """
        retrieve CO-OPS tidal station data from within the specified polygon

        :param wind_speed: wind speed in knots (one of ``34``, ``50``, or ``64``)
        :param station_type: either ``current`` or ``historical``
        :param start_date: start date
        :param end_date: end date
        :param product: CO-OPS product
        :param datum: tidal datum
        :param units: either ``metric`` or ``english``
        :param time_zone: time zone
        :param interval: time interval
        :param track: vortex track object or file path to ``fort.22``
        :return: CO-OPS station data

        >>> storm = StormEvent('florence', 2018)
        >>> storm.tidal_data_within_isotach(wind_speed=34, start_date='2018-09-13', end_date='2018-09-13 06:00:00')
        <xarray.Dataset>
        Dimensions:  (t: 121, nos_id: 7)
        Coordinates:
          * t        (t) datetime64[ns] 2018-09-13T12:00:00 ... 2018-09-14
          * nos_id   (nos_id) int64 8651370 8652587 8654467 ... 8658120 8658163 8661070
            nws_id   (nos_id) <U5 'DUKN7' 'ORIN7' 'HCGN7' ... 'WLON7' 'JMPN7' 'MROS1'
            x        (nos_id) float64 -75.75 -75.56 -75.69 -76.69 -77.94 -77.81 -78.94
            y        (nos_id) float64 36.19 35.78 35.22 34.72 34.22 34.22 33.66
        Data variables:
            v        (nos_id, t) float32 6.562 6.631 6.682 6.766 ... 9.6 9.634 9.686
            s        (nos_id, t) float32 0.66 0.537 0.496 0.516 ... 0.049 0.047 0.054
            f        (nos_id, t) object '0,0,0,0' '0,0,0,0' ... '0,0,0,0' '0,0,0,0'
            q        (nos_id, t) object 'v' 'v' 'v' 'v' 'v' 'v' ... 'v' 'v' 'v' 'v' 'v'
        """

        if isinstance(track, VortexTrack):
            track.start_date = start_date
            track.end_date = end_date
        else:
            track = self.track(start_date=start_date, end_date=end_date, filename=track)

        region = track.wind_swath(wind_speed)

        return self.tidal_data_within_region(
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

    def tidal_data_within_region(
        self,
        region: Polygon,
        station_type: COOPS_StationType = None,
        start_date: datetime = None,
        end_date: datetime = None,
        product: COOPS_Product = None,
        datum: COOPS_TidalDatum = None,
        units: COOPS_Units = None,
        time_zone: COOPS_TimeZone = None,
        interval: COOPS_Interval = None,
    ) -> Dataset:
        """
        retrieve CO-OPS tidal station data from within the specified region

        :param region: a Shapely polygon denoting the region of interest
        :param station_type: either ``current`` or ``historical``
        :param start_date: start date
        :param end_date: end date
        :param product: CO-OPS product
        :param datum: tidal datum
        :param units: either ``metric`` or ``english``
        :param time_zone: time zone
        :param interval: time interval
        :return: CO-OPS station data

        >>> import shapely
        >>> storm = StormEvent('florence', 2018)
        >>> region = shapely.geometry.box(self.track().linestring.bounds)
        >>> storm.tidal_data_within_region(region, start_date='2018-09-13', end_date='2018-09-13 06:00:00')
        <xarray.Dataset>
        Dimensions:  (t: 61, nos_id: 65)
        Coordinates:
          * t        (t) datetime64[ns] 2018-09-13 ... 2018-09-13T06:00:00
          * nos_id   (nos_id) int64 8652587 8654467 8654467 ... 8652587 8652587 8652587
            nws_id   (nos_id) <U5 'ORIN7' 'HCGN7' 'HCGN7' ... 'ORIN7' 'ORIN7' 'ORIN7'
            x        (nos_id) float64 -75.55 -75.7 -75.7 -75.7 ... -75.55 -75.55 -75.55
            y        (nos_id) float64 35.8 35.21 35.21 35.21 ... 35.8 35.8 35.8 35.8
        Data variables:
            v        (nos_id, t) float32 1.141 1.149 1.149 1.156 ... 1.175 1.167 1.164
            s        (nos_id, t) float32 0.003 0.003 0.003 0.004 ... 0.004 0.003 0.007
            f        (nos_id, t) object '0,0,0,0' '0,0,0,0' ... '0,0,0,0' '0,0,0,0'
            q        (nos_id, t) object 'v' 'v' 'v' 'v' 'v' 'v' ... 'v' 'v' 'v' 'v' 'v'
        """

        if not isinstance(region, BaseGeometry):
            try:
                region = typepigeon.convert_value(region, MultiPolygon)
            except ValueError:
                region = typepigeon.convert_value(region, Polygon)

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

        stations = coops_stations_within_region(region=region, station_type=station_type)

        if len(stations) > 0:
            stations_data = []
            for station in stations.index:
                station_data = COOPS_Station(station).get(
                    start_date=start_date,
                    end_date=end_date,
                    product=product,
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
        attributes = ', '.join(repr(value) for value in (self.name, self.year))

        if self.start_date != self.__entry['start_date']:
            attributes += f', start_date={repr(str(self.start_date))}'
        if self.end_date != self.__entry['end_date']:
            attributes += f', end_date={repr(str(self.end_date))}'

        return f'{self.__class__.__name__}({attributes})'
