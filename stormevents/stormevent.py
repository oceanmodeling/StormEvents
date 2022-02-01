from datetime import datetime
from functools import lru_cache
from os import PathLike
from typing import List

from pandas import DataFrame
from shapely.geometry import MultiPoint
import typepigeon
import xarray
from xarray import Dataset

from stormevents.coops import COOPS_Station, coops_stations_within_region
from stormevents.coops.tidalstations import (
    COOPS_Interval,
    COOPS_Product,
    coops_stations_within_bounding_box,
    COOPS_StationType,
    COOPS_TidalDatum,
    COOPS_TimeZone,
    COOPS_Units,
)
from stormevents.nhc import nhc_storms, VortexTrack
from stormevents.nhc.atcf import ATCF_FileDeck, ATCF_Mode
from stormevents.usgs import StormHighWaterMarks, usgs_highwatermark_storms


class StormEvent:
    """
    The ``StormEvent`` class can be used to retrieve data related to any arbitrary named storm event.

    You can instantiate a new ``StormEvent`` object from the NHC storm name and year
    (i.e. ``FLORENCE 2018``),

    .. code-block:: python

        from stormevents import StormEvent

        florence2018 = StormEvent('florence', 2018)

    or from the NHC storm code (i.e. ``AL062018``),

    .. code-block:: python

        from stormevents import StormEvent

        paine2016 = StormEvent.from_nhc_code('EP172016')

    or from the USGS flood event ID (i.e. ``283``).

    .. code-block:: python

        from stormevents import StormEvent

        sally2020 = StormEvent.from_usgs_id(304)

    For this storm, you can then retrieve track data from NHC,

    .. code-block:: python

        from stormevents import StormEvent

        florence2018 = StormEvent('florence', 2018)

        track = florence2018.track()

    high-water mark data from USGS,

    .. code-block:: python

        from stormevents import StormEvent

        florence2018 = StormEvent('florence', 2018)

        high_water_marks = florence2018.high_water_marks()

    and water level products from CO-OPS for this storm.

    .. code-block:: python

        from stormevents import StormEvent

        florence2018 = StormEvent('florence', 2018)

        water_levels = florence2018.tidal_data_within_isotach(isotach=34)

    By default, these functions operate within the time interval defined by the NHC best track.
    """

    def __init__(self, name: str, year: int):
        storms = nhc_storms(year=year)
        storms = storms[storms['name'].str.contains(name.upper())]
        if len(storms) > 0:
            storm = storms.iloc[0]
            nhc_code = storm.name
            self.__nhc_code = nhc_code.upper()
            self.__name = storm['name']
            self.__year = storm['year']
        else:
            raise ValueError(f'storm "{name} {year}" not found in NHC database')

        self.__usgs_id = None
        self.__usgs_flood_event = True

    @classmethod
    def from_nhc_code(cls, nhc_code: str) -> 'StormEvent':
        """
        retrieve storm information from the NHC code
        :param nhc_code: NHC code
        :return: storm object
        """

        try:
            year = int(nhc_code[-4:])
        except:
            raise ValueError(f'unable to parse NHC code "{nhc_code}"')

        storms = nhc_storms(year=year)

        if nhc_code.upper() not in storms.index.values:
            raise ValueError(f'NHC code "{nhc_code}" does not exist in table')

        storm = storms.loc[nhc_code]
        return cls(name=storm['name'], year=storm['year'])

    @classmethod
    def from_usgs_id(cls, usgs_id: int, year: int = None) -> 'StormEvent':
        """
        retrieve storm information from the USGS flood event ID
        :param usgs_id: USGS flood event ID
        :return: storm object
        """

        usgs_storm_events = usgs_highwatermark_storms(year=year)

        if usgs_id in usgs_storm_events.index:
            usgs_storm_event = usgs_storm_events.loc[usgs_id]
            storm = cls(name=usgs_storm_event['nhc_name'], year=usgs_storm_event['year'])
            storm.__usgs_id = usgs_id
            return storm
        else:
            raise ValueError(f'flood event "{usgs_id}" not found in USGS HWM database')

    @property
    def name(self) -> str:
        """ storm name """
        return self.__name

    @property
    def year(self) -> int:
        """ storm year """
        return self.__year

    @property
    def nhc_code(self) -> str:
        """ NHC code """
        return self.__nhc_code

    @property
    def usgs_id(self) -> int:
        """ USGS flood event ID """
        if self.__usgs_id is None and self.__usgs_flood_event:
            usgs_storm_events = usgs_highwatermark_storms(year=self.year)

            if self.nhc_code in usgs_storm_events['nhc_code'].values:
                usgs_storm_event = usgs_storm_events.loc[
                    usgs_storm_events['nhc_code'] == self.nhc_code
                ]
                self.__usgs_id = usgs_storm_event.index[0]
            else:
                self.__usgs_flood_event = False
        return self.__usgs_id

    @property
    def basin(self) -> str:
        """ basin in which storm occurred """
        return self.nhc_code[:2]

    @property
    def number(self) -> int:
        """ ordinal number of storm in the year """
        return int(self.nhc_code[2:4])

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

    @lru_cache(maxsize=None)
    def high_water_marks(
        self, start_date: datetime = None, end_date: datetime = None,
    ) -> DataFrame:
        """
        retrieve USGS high-water marks (HWMs)

        :param start_date: start date
        :param end_date: end date
        :return: data frame of survey data
        """

        high_water_marks = StormHighWaterMarks(name=self.name, year=self.year)
        data = high_water_marks.data
        if start_date is not None:
            start_date = typepigeon.convert_value(start_date, datetime)
            data = data[data['survey_date'] >= start_date]
        if end_date is not None:
            end_date = typepigeon.convert_value(end_date, datetime)
            data = data[data['survey_date'] <= end_date]
        return data

    @lru_cache(maxsize=None)
    def tidal_data_within_isotach(
        self,
        isotach: int,
        station_type: COOPS_StationType = None,
        start_date: datetime = None,
        end_date: datetime = None,
        product: COOPS_Product = None,
        datum: COOPS_TidalDatum = None,
        units: COOPS_Units = None,
        time_zone: COOPS_TimeZone = None,
        interval: COOPS_Interval = None,
        track_filename: PathLike = None,
    ) -> Dataset:
        """
        retrieve CO-OPS tidal station data within the specified isotach of the storm

        :param isotach: the wind swath to extract (34-kt, 50-kt, or 64-kt)
        :param station_type: either ``current`` or ``historical``
        :param start_date: start date
        :param end_date: end date
        :param product: CO-OPS product
        :param datum: tidal datum
        :param units: either ``metric`` or ``english``
        :param time_zone: time zone
        :param interval: time interval
        :param track_filename: file path to ``fort.22``
        :return: data frame of CO-OPS station data

        >>> florence2018 = StormEvent('florence', 2018)
        >>> florence2018.tidal_data_within_isotach(34, start_date='2018-09-13', end_date='2018-09-13 06:00:00')
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

        track = self.track(start_date=start_date, end_date=end_date, filename=track_filename)

        if start_date is None:
            start_date = track.start_date
        if end_date is None:
            end_date = track.end_date

        stations = coops_stations_within_vortextrack_isotach(
            isotach=isotach, track=track, station_type=station_type
        )

        if len(stations) > 0:
            stations_data = []
            for station in stations:
                station_data = station.get(
                    start_date=start_date,
                    end_date=end_date,
                    product=product,
                    datum=datum,
                    units=units,
                    time_zone=time_zone,
                    interval=interval,
                )
                stations_data.append(station_data)

            stations = xarray.combine_nested(stations_data, concat_dim='nos_id',)
        else:
            stations = Dataset(
                coords={'t': None, 'nos_id': None, 'nws_id': None, 'x': None, 'y': None,},
            )

        return stations

    @lru_cache(maxsize=None)
    def tidal_data_within_bounding_box(
        self,
        station_type: COOPS_StationType = None,
        start_date: datetime = None,
        end_date: datetime = None,
        product: COOPS_Product = None,
        datum: COOPS_TidalDatum = None,
        units: COOPS_Units = None,
        time_zone: COOPS_TimeZone = None,
        interval: COOPS_Interval = None,
        track_filename: PathLike = None,
    ) -> Dataset:
        """
        retrieve CO-OPS tidal station data within the bounding box of the track

        :param station_type: either ``current`` or ``historical``
        :param start_date: start date
        :param end_date: end date
        :param product: CO-OPS product
        :param datum: tidal datum
        :param units: either ``metric`` or ``english``
        :param time_zone: time zone of data
        :param interval: time interval of data
        :param track_filename: file path to ``fort.22``
        :return: data array of CO-OPS station data

        >>> florence2018 = StormEvent('florence', 2018)
        >>> florence2018.tidal_data_within_bounding_box(start_date='2018-09-13', end_date='2018-09-13 06:00:00')
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

        track = self.track(start_date=start_date, end_date=end_date, filename=track_filename)

        if start_date is None:
            start_date = track.start_date
        if end_date is None:
            end_date = track.end_date

        stations = coops_stations_within_bounding_box(
            *MultiPoint(track.data[['longitude', 'latitude']].values).bounds,
            station_type=station_type,
        )

        if len(stations) > 0:
            stations_data = []
            for station in stations:
                station_data = station.get(
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
            stations = xarray.combine_nested(stations_data, concat_dim='nos_id')
        else:
            stations = Dataset(
                coords={'t': None, 'nos_id': None, 'nws_id': None, 'x': None, 'y': None}
            )

        return stations

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(repr(value) for value in (self.__name, self.year))})'


def coops_stations_within_vortextrack_isotach(
    isotach: int, track: VortexTrack, station_type: COOPS_StationType = None,
) -> List[COOPS_Station]:
    region = track.wind_swath(isotach=isotach)
    return coops_stations_within_region(region=region, station_type=station_type)
