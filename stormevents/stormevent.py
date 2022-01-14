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
    abstraction of a storm event, providing data getters for NHC tracks, USGS high water marks, and CO-OPS tidal station data
    """

    def __init__(self, name: str, year: int):
        storms = nhc_storms(year=year)
        if name.upper() in storms['name'].values:
            storm = storms.loc[storms['name'] == name.upper()]
            nhc_code = storm.index[0]
            self.__nhc_code = nhc_code
            self.__name = storm['name'][0]
            self.__year = storm['year'][0]
        else:
            raise ValueError('no storm with specified name found in NHC database')

        self.__usgs_id = None
        self.__usgs_flood_event = True

    @classmethod
    def from_nhc_code(cls, nhc_code: str) -> 'StormEvent':
        track = VortexTrack(storm=nhc_code.lower())
        return cls(name=track.name, year=track.year)

    @classmethod
    def from_usgs_id(cls, usgs_id: int, year: int = None) -> 'StormEvent':
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
        return self.__name

    @property
    def year(self) -> int:
        return self.__year

    @property
    def nhc_code(self) -> str:
        return self.__nhc_code

    @property
    def usgs_id(self) -> int:
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
        return self.nhc_code[:2]

    @property
    def number(self) -> int:
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
