from datetime import datetime
from functools import lru_cache
from os import PathLike
from typing import List

import pandas
from pandas import DataFrame
from shapely.geometry import MultiPoint

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
            data = data['date'] >= start_date
        if end_date is not None:
            data = data['date'] <= end_date
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
    ) -> DataFrame:
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
        """

        track = self.track(start_date=start_date, end_date=end_date, filename=track_filename)

        if start_date is None:
            start_date = track.start_date
        if end_date is None:
            end_date = track.end_date

        stations = coops_stations_within_vortextrack_isotach(
            isotach=isotach, track=track, station_type=station_type
        )

        return pandas.concat(
            [
                station.get(
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
    ) -> DataFrame:
        """
        retrieve CO-OPS tidal station data within the bounding box of the track

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
        """

        track = self.track(start_date=start_date, end_date=end_date, filename=track_filename)

        if start_date is None:
            start_date = track.start_date
        if end_date is None:
            end_date = track.end_date

        stations = coops_stations_within_bounding_box(
            *MultiPoint(track.data[['Longitude', 'Latitude']]).bounds,
            station_type=station_type,
        )

        return pandas.concat(
            [
                station.get(
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

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.__name}, {self.year})'


def coops_stations_within_vortextrack_isotach(
    isotach: int, track: VortexTrack, station_type: COOPS_StationType = None,
) -> List[COOPS_Station]:
    region = track.wind_swath(isotach=isotach)
    return coops_stations_within_region(region=region, station_type=station_type)
