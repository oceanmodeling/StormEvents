from datetime import datetime, timedelta
from functools import partial
import gzip
import io
import logging
from os import PathLike
import pathlib
import re
from typing import Any, Dict, List, Union
from urllib.error import URLError
from urllib.request import urlopen

import numpy
import pandas
from pandas import DataFrame
from pyproj import Geod
from shapely import ops
from shapely.geometry import LineString, MultiPolygon, Polygon
import typepigeon

from stormevents.nhc.atcf import (
    ATCF_Advisory,
    ATCF_FileDeck,
    ATCF_Mode,
    atcf_url,
    EXTRA_ATCF_FIELDS,
    get_atcf_entry,
    read_atcf,
)
from stormevents.nhc.storms import nhc_storms
from stormevents.utilities import subset_time_interval


class VortexTrack:
    """
    interface to an ATCF vortex track (i.e. HURDAT, best track, HWRF, etc.)
    """

    def __init__(
        self,
        storm: Union[str, PathLike, DataFrame, io.BytesIO],
        start_date: datetime = None,
        end_date: datetime = None,
        file_deck: ATCF_FileDeck = None,
        advisories: List[ATCF_Advisory] = None,
    ):
        """
        :param storm: storm ID, or storm name and year
        :param start_date: start date of track
        :param end_date: end date of track
        :param file_deck: ATCF file deck; one of `a`, `b`, `f`
        :param advisories: ATCF advisory types; one of `BEST`, `OFCL`, `OFCP`, `HMON`, `CARQ`, `HWRF`

        >>> VortexTrack('AL112017')
        VortexTrack('AL112017', Timestamp('2017-08-30 00:00:00'), Timestamp('2017-09-13 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.HISTORICAL: 'ARCHIVE'>, [<ATCF_Advisory.BEST: 'BEST'>], None)

        >>> VortexTrack('AL112017', start_date='2017-09-04')
        VortexTrack('AL112017', Timestamp('2017-09-04 00:00:00'), Timestamp('2017-09-13 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.HISTORICAL: 'ARCHIVE'>, [<ATCF_Advisory.BEST: 'BEST'>], None)

        >>> from datetime import timedelta
        >>> VortexTrack('AL112017', start_date=timedelta(days=2), end_date=timedelta(days=-1))
        VortexTrack('AL112017', Timestamp('2017-09-01 00:00:00'), Timestamp('2017-09-12 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.HISTORICAL: 'ARCHIVE'>, [<ATCF_Advisory.BEST: 'BEST'>], None)

        >>> VortexTrack('AL112017', file_deck='a')
        VortexTrack('AL112017', Timestamp('2017-08-27 06:00:00'), Timestamp('2017-09-13 12:00:00'), <ATCF_FileDeck.ADVISORY: 'a'>, <ATCF_Mode.HISTORICAL: 'ARCHIVE'>, ['OFCL', 'OFCP', 'HMON', 'CARQ', 'HWRF'], None)
        """

        self.__unfiltered_data = None
        self.__filename = None

        self.__remote_atcf = None
        self.__nhc_code = None
        self.__name = None
        self.__start_date = None
        self.__end_date = None
        self.__file_deck = None
        self.__advisories = None

        self.__advisories_to_remove = []
        self.__invalid_storm_name = False
        self.__location_hash = None
        self.__linestrings = None
        self.__distances = None

        if isinstance(storm, DataFrame):
            self.__unfiltered_data = storm
        elif pathlib.Path(storm).exists():
            self.filename = storm
        elif isinstance(storm, str):
            try:
                self.nhc_code = storm
            except ValueError:
                raise
        else:
            raise FileNotFoundError(f'file not found "{storm}"')

        self.advisories = advisories
        self.file_deck = file_deck

        self.__previous_configuration = self.__configuration

        # use start and end dates to mask dataframe here
        self.start_date = start_date
        self.end_date = end_date

    @classmethod
    def from_storm_name(
        cls,
        name: str,
        year: int,
        start_date: datetime = None,
        end_date: datetime = None,
        file_deck: ATCF_FileDeck = None,
        advisories: [ATCF_Advisory] = None,
    ) -> 'VortexTrack':
        """
        :param name: storm name
        :param year: storm year
        :param start_date: start date of track
        :param end_date: end date of track
        :param file_deck: ATCF file deck; one of ``a``, ``b``, ``f``
        :param advisories: ATCF advisory type; one of ``BEST``, ``OFCL``, ``OFCP``, ``HMON``, ``CARQ``, ``HWRF``

        >>> VortexTrack.from_storm_name('irma', 2017)
        VortexTrack('AL112017', Timestamp('2017-08-30 00:00:00'), Timestamp('2017-09-13 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, [<ATCF_Advisory.BEST: 'BEST'>], None)
        """

        year = int(year)
        atcf_id = get_atcf_entry(storm_name=name, year=year).name

        return cls(
            storm=atcf_id,
            start_date=start_date,
            end_date=end_date,
            file_deck=file_deck,
            advisories=advisories,
        )

    @classmethod
    def from_file(
        cls, path: PathLike, start_date: datetime = None, end_date: datetime = None,
    ) -> 'VortexTrack':
        """
        :param path: file path to ATCF data
        :param start_date: start date of track
        :param end_date: end date of track

        >>> VortexTrack.from_file('tests/data/input/test_vortex_track_from_file/AL062018.dat')
        VortexTrack('AL062018', Timestamp('2018-08-30 06:00:00'), Timestamp('2018-09-18 12:00:00'), None, <ATCF_Mode.HISTORICAL: 'ARCHIVE'>, ['BEST', 'OFCL', 'OFCP', 'HMON', 'CARQ', 'HWRF'], PosixPath('/home/zrb/Projects/StormEvents/tests/data/input/test_vortex_track_from_file/AL062018.dat'))
        >>> VortexTrack.from_file('tests/data/input/test_vortex_track_from_file/irma2017_fort.22')
        VortexTrack('AL112017', Timestamp('2017-09-05 00:00:00'), Timestamp('2017-09-12 00:00:00'), None, <ATCF_Mode.HISTORICAL: 'ARCHIVE'>, ['BEST', 'OFCL', 'OFCP', 'HMON', 'CARQ', 'HWRF'], PosixPath('/home/zrb/Projects/StormEvents/tests/data/input/test_vortex_track_from_file/irma2017_fort.22'))
        """

        try:
            path = pathlib.Path(path)
        except:
            pass

        return cls(storm=path, start_date=start_date, end_date=end_date)

    @property
    def name(self) -> str:
        """
        :return: NHC storm name

        >>> track = VortexTrack('AL112017')
        >>> track.name
        'IRMA'
        """

        if self.__name is None:
            # get the most frequently-used storm name in the data
            names = self.data['name'].value_counts()
            if len(names) > 0:
                name = names.index[0]
            else:
                name = ''

            if name.strip() == '':
                storms = nhc_storms(year=self.year)
                if self.nhc_code.upper() in storms.index:
                    storm = storms.loc[self.nhc_code.upper()]
                    name = storm['name'].lower()

            self.__name = name

        return self.__name

    @property
    def basin(self) -> str:
        """
        :return: basin of track

        >>> track = VortexTrack('AL112017')
        >>> track.basin
        'AL'
        """

        return self.data['basin'].iloc[0]

    @property
    def storm_number(self) -> str:
        """
        :return: ordinal number of storm within the basin and year

        >>> track = VortexTrack('AL112017')
        >>> track.storm_number
        11
        """

        return self.data['storm_number'].iloc[0]

    @property
    def year(self) -> int:
        """
        :return: year of storm

        >>> track = VortexTrack('AL112017')
        >>> track.year
        2017
        """

        return self.data['datetime'].iloc[0].year

    @property
    def nhc_code(self) -> str:
        """
        :return: storm NHC code (i.e. ``AL062018``)

        >>> track = VortexTrack('AL112017')
        >>> track.nhc_code
        'AL112017'
        """

        if self.__nhc_code is None and not self.__invalid_storm_name:
            if self.__unfiltered_data is not None:
                nhc_code = (
                    f'{self.__unfiltered_data["basin"].iloc[-1]}'
                    f'{self.__unfiltered_data["storm_number"].iloc[-1]}'
                    f'{self.__unfiltered_data["datetime"].iloc[-1].year}'
                )
                try:
                    self.nhc_code = nhc_code
                except ValueError:
                    try:
                        nhc_code = get_atcf_entry(
                            storm_name=self.__unfiltered_data['name'].tolist()[-1],
                            year=self.__unfiltered_data['datetime'].tolist()[-1].year,
                        ).name
                        self.nhc_code = nhc_code
                    except ValueError:
                        self.__invalid_storm_name = True
        return self.__nhc_code

    @nhc_code.setter
    def nhc_code(self, nhc_code: str):
        if nhc_code is not None:
            # check if name+year was given instead of basin+number+year
            digits = sum([1 for character in nhc_code if character.isdigit()])

            if digits == 4:
                atcf_nhc_code = get_atcf_entry(
                    storm_name=nhc_code[:-4], year=int(nhc_code[-4:])
                ).name
                if atcf_nhc_code is None:
                    raise ValueError(f'No storm with id: {nhc_code}')
                nhc_code = atcf_nhc_code
        self.__nhc_code = nhc_code

    @property
    def start_date(self) -> pandas.Timestamp:
        """
        :return: start time of current track

        >>> track = VortexTrack('AL112017')
        >>> track.start_date
        Timestamp('2017-08-30 00:00:00')
        >>> track.start_date = '2017-09-04'
        >>> track.start_date
        Timestamp('2017-09-04 00:00:00')
        >>> from datetime import timedelta
        >>> track.start_date = timedelta(days=1)
        >>> track.start_date
        Timestamp('2017-08-31 00:00:00')
        >>> track.start_date = timedelta(days=-2)
        >>> track.start_date
        Timestamp('2017-09-11 12:00:00')
        """

        return self.__start_date

    @start_date.setter
    def start_date(self, start_date: datetime):
        data_start = self.unfiltered_data['datetime'].iloc[0]

        if start_date is None:
            start_date = data_start
        else:
            # interpret timedelta as a temporal movement around start / end
            data_end = self.unfiltered_data['datetime'].iloc[-1]
            start_date, _ = subset_time_interval(
                start=data_start, end=data_end, subset_start=start_date,
            )
            if not isinstance(start_date, pandas.Timestamp):
                start_date = pandas.to_datetime(start_date)

        self.__start_date = start_date

    @property
    def end_date(self) -> pandas.Timestamp:
        """
        :return: end time of current track

        >>> track = VortexTrack('AL112017')
        >>> track.end_date
        Timestamp('2017-09-13 12:00:00')
        >>> track.end_date = '2017-09-10'
        >>> track.end_date
        Timestamp('2017-09-10 00:00:00')
        >>> from datetime import timedelta
        >>> track.end_date = timedelta(days=-1)
        >>> track.end_date
        Timestamp('2017-09-12 12:00:00')
        >>> track.end_date = timedelta(days=2)
        >>> track.end_date
        Timestamp('2017-09-01 00:00:00')
        """

        return self.__end_date

    @end_date.setter
    def end_date(self, end_date: datetime):
        data_end = self.unfiltered_data['datetime'].iloc[-1]

        if end_date is None:
            end_date = data_end
        else:
            # interpret timedelta as a temporal movement around start / end
            data_start = self.unfiltered_data['datetime'].iloc[0]
            _, end_date = subset_time_interval(
                start=data_start, end=data_end, subset_end=end_date,
            )
            if not isinstance(end_date, pandas.Timestamp):
                end_date = pandas.to_datetime(end_date)

        self.__end_date = end_date

    @property
    def file_deck(self) -> ATCF_FileDeck:
        """
        :return: ATCF file deck; one of ``a``, ``b``, ``f``
        """

        return self.__file_deck

    @file_deck.setter
    def file_deck(self, file_deck: ATCF_FileDeck):
        if file_deck is None and self.filename is None:
            if self.advisories is not None or len(self.advisories) > 0:
                if ATCF_Advisory.BEST in typepigeon.convert_value(
                    self.advisories, [ATCF_Advisory]
                ):
                    file_deck = ATCF_FileDeck.BEST
                else:
                    file_deck = ATCF_FileDeck.ADVISORY
            else:
                file_deck = ATCF_FileDeck.BEST
        elif not isinstance(file_deck, ATCF_FileDeck):
            file_deck = typepigeon.convert_value(file_deck, ATCF_FileDeck)
        self.__file_deck = file_deck

    @property
    def advisories(self) -> List[ATCF_Advisory]:
        """
        :return: ATCF advisory types; one of ``BEST``, ``OFCL``, ``OFCP``, ``HMON``, ``CARQ``, ``HWRF``
        """

        if self.file_deck == ATCF_FileDeck.BEST:
            self.__advisories = [ATCF_Advisory.BEST]

        return self.__advisories

    @advisories.setter
    def advisories(self, advisories: List[ATCF_Advisory]):
        # e.g. `BEST`, `OFCL`, `HWRF`, etc.
        if advisories is None:
            advisories = self.__valid_advisories
        else:
            advisories = typepigeon.convert_value(advisories, [str])
            advisories = [advisory.upper() for advisory in advisories]
        self.__advisories = advisories

    @property
    def __valid_advisories(self) -> List[ATCF_Advisory]:
        if self.file_deck is None:
            valid_advisories = [advisory.value for advisory in ATCF_Advisory]
        elif self.file_deck == ATCF_FileDeck.ADVISORY:
            # see ftp://ftp.nhc.noaa.gov/atcf/docs/nhc_techlist.dat
            # there are more but they may not have enough columns
            valid_advisories = [
                entry.value for entry in ATCF_Advisory if entry != ATCF_Advisory.BEST
            ]
        elif self.file_deck == ATCF_FileDeck.BEST:
            valid_advisories = [ATCF_Advisory.BEST.value]
        elif self.file_deck == ATCF_FileDeck.FIXED:
            valid_advisories = [entry.value for entry in ATCF_Advisory]
        else:
            raise NotImplementedError(f'file deck {self.file_deck.value} not implemented')

        return valid_advisories

    @property
    def filename(self) -> pathlib.Path:
        """
        :return: file path to read file (optional)
        """

        return self.__filename

    @filename.setter
    def filename(self, filename: PathLike):
        if filename is not None and not isinstance(filename, pathlib.Path):
            filename = pathlib.Path(filename)
        self.__filename = filename

    @property
    def data(self) -> DataFrame:
        """
        :return: track data for the given parameters as a data frame

        >>> track = VortexTrack('AL112017')
        >>> track.data
            basin storm_number            datetime advisory_number  ... isowave_radius_for_SWQ extra_values                    geometry  track_start_time
        0      AL           11 2017-08-30 00:00:00                  ...                    NaN         <NA>  POINT (-26.90000 16.10000)        2017-08-30
        1      AL           11 2017-08-30 06:00:00                  ...                    NaN         <NA>  POINT (-28.30000 16.20000)        2017-08-30
        2      AL           11 2017-08-30 12:00:00                  ...                    NaN         <NA>  POINT (-29.70000 16.30000)        2017-08-30
        3      AL           11 2017-08-30 18:00:00                  ...                    NaN         <NA>  POINT (-30.80000 16.30000)        2017-08-30
        4      AL           11 2017-08-30 18:00:00                  ...                    NaN         <NA>  POINT (-30.80000 16.30000)        2017-08-30
        ..    ...          ...                 ...             ...  ...                    ...          ...                         ...               ...
        168    AL           11 2017-09-12 12:00:00                  ...                    NaN         <NA>  POINT (-86.90000 33.80000)        2017-08-30
        169    AL           11 2017-09-12 18:00:00                  ...                    NaN         <NA>  POINT (-88.10000 34.80000)        2017-08-30
        170    AL           11 2017-09-13 00:00:00                  ...                    NaN         <NA>  POINT (-88.90000 35.60000)        2017-08-30
        171    AL           11 2017-09-13 06:00:00                  ...                    NaN         <NA>  POINT (-89.50000 36.20000)        2017-08-30
        172    AL           11 2017-09-13 12:00:00                  ...                    NaN         <NA>  POINT (-90.10000 36.80000)        2017-08-30
        [173 rows x 38 columns]

        >>> track = VortexTrack('AL112017', file_deck='a')
        >>> track.data
              basin storm_number            datetime advisory_number  ... isowave_radius_for_SWQ extra_values                    geometry    track_start_time
        0        AL           11 2017-08-27 06:00:00              01  ...                    NaN         <NA>  POINT (-17.40000 11.70000) 2017-08-28 06:00:00
        1        AL           11 2017-08-27 12:00:00              01  ...                    NaN         <NA>  POINT (-17.90000 11.80000) 2017-08-28 06:00:00
        2        AL           11 2017-08-27 18:00:00              01  ...                    NaN         <NA>  POINT (-18.40000 11.90000) 2017-08-28 06:00:00
        3        AL           11 2017-08-28 00:00:00              01  ...                    NaN         <NA>  POINT (-19.00000 12.00000) 2017-08-28 06:00:00
        4        AL           11 2017-08-28 06:00:00              01  ...                    NaN         <NA>  POINT (-19.50000 12.00000) 2017-08-28 06:00:00
        ...     ...          ...                 ...             ...  ...                    ...          ...                         ...                 ...
        10739    AL           11 2017-09-12 00:00:00              03  ...                    NaN         <NA>  POINT (-84.40000 31.90000) 2017-09-12 00:00:00
        10740    AL           11 2017-09-12 03:00:00              03  ...                    NaN         <NA>  POINT (-84.90000 32.40000) 2017-09-12 00:00:00
        10741    AL           11 2017-09-12 12:00:00              03  ...                    NaN         <NA>  POINT (-86.40000 33.80000) 2017-09-12 00:00:00
        10742    AL           11 2017-09-13 00:00:00              03  ...                    NaN         <NA>  POINT (-88.20000 35.20000) 2017-09-12 00:00:00
        10743    AL           11 2017-09-13 12:00:00              03  ...                    NaN         <NA>  POINT (-88.60000 36.40000) 2017-09-12 00:00:00
        [10434 rows x 38 columns]
        """

        return self.unfiltered_data.loc[
            (self.unfiltered_data['datetime'] >= self.start_date)
            & (self.unfiltered_data['datetime'] <= self.end_date)
        ]

    def to_file(self, path: PathLike, advisory: ATCF_Advisory = None, overwrite: bool = False):
        """
        write track to file path

        :param path: output file path
        :param advisory: advisory type to write
        :param overwrite: overwrite existing file
        """

        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)

        if overwrite or not path.exists():
            if path.suffix == '.dat':
                data = self.atcf(advisory=advisory)
                data.to_csv(path, index=False, header=False)
            elif path.suffix == '.22':
                data = self.fort_22(advisory=advisory)
                data.to_csv(path, index=False, header=False)
            else:
                raise NotImplementedError(f'writing to `*{path.suffix}` not supported')
        else:
            logging.warning(f'skipping existing file "{path}"')

    def atcf(self, advisory: ATCF_Advisory = None) -> DataFrame:
        """
        https://www.nrlmry.navy.mil/atcf_web/docs/database/new/abrdeck.html

        BASIN,CY,YYYYMMDDHH,TECHNUM/MIN,TECH,TAU,LatN/S,LonE/W,VMAX,MSLP,TY,RAD,WINDCODE,RAD1,RAD2,RAD3,RAD4,RADP,RRP,MRD,GUSTS,EYE,SUBREGION,MAXSEAS,INITIALS,DIR,SPEED,STORMNAME,DEPTH,SEAS,SEASCODE,SEAS1,SEAS2,SEAS3,SEAS4,USERDEFINED,userdata

        :param advisory: advisory type
        :return: dataframe of CSV lines in ATCF format
        """

        atcf = self.data.copy(deep=True)
        atcf.loc[atcf['advisory'] != 'BEST', 'datetime'] = atcf.loc[
            atcf['advisory'] != 'BEST', 'track_start_time'
        ]
        atcf.drop(columns=['geometry', 'track_start_time'], inplace=True)

        if advisory is not None:
            if isinstance(advisory, ATCF_Advisory):
                advisory = advisory.value
            atcf = atcf[atcf['advisory'] == advisory]

        atcf.loc[:, ['longitude', 'latitude']] = atcf.loc[:, ['longitude', 'latitude']] * 10

        float_columns = atcf.select_dtypes(include=['float']).columns
        integer_na_value = -99999
        for column in float_columns:
            atcf.loc[pandas.isna(atcf[column]), column] = integer_na_value
            atcf.loc[:, column] = atcf.loc[:, column].round(0).astype(int)

        atcf['basin'] = atcf['basin'].str.pad(2)
        atcf['storm_number'] = atcf['storm_number'].astype('string').str.pad(3)
        atcf['datetime'] = atcf['datetime'].dt.strftime('%Y%m%d%H').str.pad(11)
        atcf['advisory_number'] = atcf['advisory_number'].str.pad(3)
        atcf['advisory'] = atcf['advisory'].str.pad(5)
        atcf['forecast_hours'] = atcf['forecast_hours'].astype('string').str.pad(4)

        atcf['latitude'] = atcf['latitude'].astype('string')
        atcf.loc[~atcf['latitude'].str.contains('-'), 'latitude'] = (
            atcf.loc[~atcf['latitude'].str.contains('-'), 'latitude'] + 'N'
        )
        atcf.loc[atcf['latitude'].str.contains('-'), 'latitude'] = (
            atcf.loc[atcf['latitude'].str.contains('-'), 'latitude'] + 'S'
        )
        atcf['latitude'] = atcf['latitude'].str.strip('-').str.pad(5)

        atcf['longitude'] = atcf['longitude'].astype('string')
        atcf.loc[~atcf['longitude'].str.contains('-'), 'longitude'] = (
            atcf.loc[~atcf['longitude'].str.contains('-'), 'longitude'] + 'E'
        )
        atcf.loc[atcf['longitude'].str.contains('-'), 'longitude'] = (
            atcf.loc[atcf['longitude'].str.contains('-'), 'longitude'] + 'W'
        )
        atcf['longitude'] = atcf['longitude'].str.strip('-').str.pad(6)

        atcf['max_sustained_wind_speed'] = (
            atcf['max_sustained_wind_speed'].astype('string').str.pad(5)
        )
        atcf['central_pressure'] = atcf['central_pressure'].astype('string').str.pad(5)
        atcf['development_level'] = atcf['development_level'].str.pad(3)
        atcf['isotach_radius'] = atcf['isotach_radius'].astype('string').str.pad(4)
        atcf['isotach_quadrant_code'] = atcf['isotach_quadrant_code'].str.pad(4)
        atcf['isotach_radius_for_NEQ'] = (
            atcf['isotach_radius_for_NEQ'].astype('string').str.pad(5)
        )
        atcf['isotach_radius_for_SEQ'] = (
            atcf['isotach_radius_for_SEQ'].astype('string').str.pad(5)
        )
        atcf['isotach_radius_for_NWQ'] = (
            atcf['isotach_radius_for_NWQ'].astype('string').str.pad(5)
        )
        atcf['isotach_radius_for_SWQ'] = (
            atcf['isotach_radius_for_SWQ'].astype('string').str.pad(5)
        )

        atcf['background_pressure'].fillna(method='ffill', inplace=True)
        atcf.loc[
            ~pandas.isna(self.data['central_pressure'])
            & (self.data['background_pressure'] <= self.data['central_pressure'])
            & (self.data['central_pressure'] < 1013),
            'background_pressure',
        ] = '1013'
        atcf.loc[
            ~pandas.isna(self.data['central_pressure'])
            & (self.data['background_pressure'] <= self.data['central_pressure'])
            & (self.data['central_pressure'] < 1013),
            'background_pressure',
        ] = (self.data['central_pressure'] + 1)
        atcf['background_pressure'] = (
            atcf['background_pressure'].astype(int).astype('string').str.pad(5)
        )

        atcf['radius_of_last_closed_isobar'] = (
            atcf['radius_of_last_closed_isobar'].astype('string').str.pad(5)
        )
        atcf['radius_of_maximum_winds'] = (
            atcf['radius_of_maximum_winds'].astype('string').str.pad(4)
        )
        atcf['gust_speed'] = atcf['gust_speed'].astype('string').str.pad(4)
        atcf['eye_diameter'] = atcf['eye_diameter'].astype('string').str.pad(4)
        atcf['subregion_code'] = atcf['subregion_code'].str.pad(4)
        atcf['maximum_wave_height'] = atcf['maximum_wave_height'].astype('string').str.pad(4)
        atcf['forecaster_initials'] = atcf['forecaster_initials'].str.pad(4)

        atcf['direction'] = atcf['direction'].astype('string').str.pad(4)
        atcf['speed'] = atcf['speed'].astype('string').str.pad(4)
        atcf['name'] = atcf['name'].astype('string').str.pad(11)

        if 'depth_code' in atcf.columns:
            atcf['depth_code'] = atcf['depth_code'].astype('string').str.pad(2)
            atcf['isowave'] = atcf['isowave'].astype('string').str.pad(3)
            atcf['isowave_quadrant_code'] = (
                atcf['isowave_quadrant_code'].astype('string').str.pad(4)
            )
            atcf['isowave_radius_for_NEQ'] = (
                atcf['isowave_radius_for_NEQ'].astype('string').str.pad(5)
            )
            atcf['isowave_radius_for_SEQ'] = (
                atcf['isowave_radius_for_SEQ'].astype('string').str.pad(5)
            )
            atcf['isowave_radius_for_NWQ'] = (
                atcf['isowave_radius_for_NWQ'].astype('string').str.pad(5)
            )
            atcf['isowave_radius_for_SWQ'] = (
                atcf['isowave_radius_for_SWQ'].astype('string').str.pad(5)
            )

        for column in atcf.select_dtypes(include=['string']).columns:
            atcf[column] = atcf[column].str.replace(re.compile(str(integer_na_value)), '')

        return atcf

    def fort_22(self, advisory: ATCF_Advisory = None) -> DataFrame:
        """
        https://wiki.adcirc.org/wiki/Fort.22_file

        :param advisory: advisory type
        :return: `fort.22` representation of the current track
        """

        fort22 = self.atcf(advisory=advisory)

        fort22.drop(
            columns=[field for field in EXTRA_ATCF_FIELDS.values() if field in fort22.columns],
            inplace=True,
        )

        fort22['longitude'] = fort22['longitude'].str.strip().str.pad(4)
        fort22['latitude'] = fort22['latitude'].str.strip().str.pad(5)
        fort22['gust_speed'] = fort22['gust_speed'].str.strip().str.pad(5)
        fort22['direction'] = fort22['direction'].str.strip().str.pad(3)
        fort22['name'] = fort22['name'].str.strip().str.pad(12)
        fort22.loc[fort22['name'] == '', 'name'] = self.name

        fort22['record_number'] = (
            (self.data.groupby(['datetime']).ngroup() + 1).astype('string').str.pad(4)
        )

        return fort22

    @property
    def linestrings(self) -> Dict[str, Dict[str, LineString]]:
        """
        :return: spatial linestrings for every advisory and track
        """

        configuration = self.__configuration

        # only proceed if the configuration has changed
        if (
            self.__linestrings is None
            or len(self.__linestrings) == 0
            or configuration != self.__previous_configuration
        ):
            tracks = self.tracks

            linestrings = {}
            for advisory, advisory_tracks in tracks.items():
                linestrings[advisory] = {}
                for track_start_time, track in advisory_tracks.items():
                    geometries = track['geometry']
                    if len(geometries) > 1:
                        geometries = geometries.drop_duplicates()
                        if len(geometries) > 1:
                            linestrings[advisory][track_start_time] = LineString(
                                geometries.to_list()
                            )

            self.__linestrings = linestrings

        return self.__linestrings

    @property
    def distances(self) -> Dict[str, Dict[str, float]]:
        """
        :return: length, in meters, of the track over WGS84 (``EPSG:4326``)
        """

        configuration = self.__configuration

        # only proceed if the configuration has changed
        if (
            self.__distances is None
            or len(self.__distances) == 0
            or configuration != self.__previous_configuration
        ):
            geodetic = Geod(ellps='WGS84')

            linestrings = self.linestrings

            distances = {}
            for advisory, advisory_tracks in linestrings.items():
                distances[advisory] = {}
                for track_start_time, linestring in advisory_tracks.items():
                    x, y = linestring.xy
                    _, _, track_distances = geodetic.inv(x[:-1], y[:-1], x[1:], y[1:],)
                    distances[advisory][track_start_time] = numpy.sum(track_distances)

            self.__distances = distances

        return self.__distances

    def isotachs(
        self, wind_speed: float, segments: int = 91
    ) -> Dict[str, Dict[str, Dict[str, Polygon]]]:
        """
        isotach at the given wind speed at every time in the dataset

        :param wind_speed: wind speed to extract (in knots)
        :param segments: number of discretization points per quadrant
        :return: list of isotachs as polygons for each advisory type and individual track
        """

        valid_isotach_values = [34, 50, 64]
        assert (
            wind_speed in valid_isotach_values
        ), f'isotach must be one of {valid_isotach_values}'

        # collect the attributes needed from the forcing to generate swath
        data = self.data[self.data['isotach_radius'] == wind_speed]

        # enumerate quadrants
        quadrant_names = [
            'isotach_radius_for_NEQ',
            'isotach_radius_for_NWQ',
            'isotach_radius_for_SWQ',
            'isotach_radius_for_SEQ',
        ]

        # convert quadrant radii from nautical miles to meters
        data[quadrant_names] *= 1852.0

        geodetic = Geod(ellps='WGS84')

        tracks = separate_tracks(data)

        # generate overall swath based on the desired isotach
        isotachs = {}
        for advisory, advisory_tracks in tracks.items():
            advisory_isotachs = {}
            for track_start_time, track_data in advisory_tracks.items():
                track_isotachs = {}
                for index, row in track_data.iterrows():
                    # get the starting angle range for NEQ based on storm direction
                    rotation_angle = 360 - row['direction']
                    start_angle = 0 + rotation_angle
                    end_angle = 90 + rotation_angle

                    # append quadrants in counter-clockwise direction from NEQ
                    quadrants = []
                    for quadrant_name in quadrant_names:
                        # skip if quadrant radius is zero
                        if row[quadrant_name] > 1:
                            # enter the angle range for this quadrant
                            theta = numpy.linspace(start_angle, end_angle, segments)

                            # move angle to next quadrant
                            start_angle = start_angle + 90
                            end_angle = end_angle + 90

                            # make the coordinate list for this quadrant using forward geodetic (origin,angle,dist)
                            vectorized_forward_geodetic = numpy.vectorize(
                                partial(
                                    geodetic.fwd,
                                    lons=row['longitude'],
                                    lats=row['latitude'],
                                    dist=row[quadrant_name],
                                )
                            )
                            x, y, reverse_azimuth = vectorized_forward_geodetic(az=theta)
                            vertices = numpy.stack([x, y], axis=1)

                            # insert center point at beginning and end of list
                            vertices = numpy.concatenate(
                                [
                                    row[['longitude', 'latitude']].values[None, :],
                                    vertices,
                                    row[['longitude', 'latitude']].values[None, :],
                                ],
                                axis=0,
                            )

                            quadrants.append(Polygon(vertices))

                    if len(quadrants) > 0:
                        isotach = ops.unary_union(quadrants)

                        if isinstance(isotach, MultiPolygon):
                            isotach = isotach.buffer(1e-10)

                        track_isotachs[f'{row["datetime"]}:%Y%m%dT%H%M%S'] = isotach
                if len(track_isotachs) > 0:
                    advisory_isotachs[track_start_time] = track_isotachs
            if len(advisory_isotachs) > 0:
                isotachs[advisory] = advisory_isotachs
        return isotachs

    def wind_swaths(
        self, wind_speed: int, segments: int = 91
    ) -> Dict[str, Dict[str, Polygon]]:
        """
        wind swaths (per advisory type) for each advisory and track, as polygons

        :param wind_speed: wind speed in knots (one of ``34``, ``50``, or ``64``)
        :param segments: number of discretization points per quadrant (default = ``91``)
        """

        isotachs = self.isotachs(wind_speed=wind_speed, segments=segments)

        wind_swaths = {}
        for advisory, advisory_isotachs in isotachs.items():
            advisory_wind_swaths = {}
            for track_start_time, track_isotachs in advisory_isotachs.items():
                convex_hulls = []
                isotach_times = list(track_isotachs)
                for index in range(len(isotach_times) - 1):
                    convex_hulls.append(
                        ops.unary_union(
                            [
                                track_isotachs[isotach_times[index]],
                                track_isotachs[isotach_times[index + 1]],
                            ]
                        ).convex_hull
                    )

                if len(convex_hulls) > 0:
                    # get the union of polygons
                    advisory_wind_swaths[track_start_time] = ops.unary_union(convex_hulls)
            if len(advisory_isotachs) > 0:
                wind_swaths[advisory] = advisory_wind_swaths

        return wind_swaths

    @property
    def tracks(self) -> Dict[str, Dict[str, DataFrame]]:
        """
        :return: individual tracks sorted into advisories and initial times
        """
        return separate_tracks(self.data)

    @property
    def duration(self) -> pandas.Timedelta:
        """
        :return: duration of current track
        """

        return self.data['datetime'].diff().sum()

    @property
    def unfiltered_data(self) -> DataFrame:
        """
        :return: data frame containing all track data for the specified storm and file deck; NOTE: datetimes for forecasts represent the initial datetime of the forecast, not the datetime of the record
        """

        configuration = self.__configuration

        # only proceed if the configuration has changed
        if (
            self.__unfiltered_data is None
            or len(self.__unfiltered_data) == 0
            or configuration != self.__previous_configuration
        ):
            advisories = self.advisories
            if configuration['filename'] is not None:
                atcf_file = configuration['filename']
            else:
                url = atcf_url(self.nhc_code, self.file_deck)
                try:
                    response = urlopen(url)
                except URLError:
                    url = atcf_url(self.nhc_code, self.file_deck, mode=ATCF_Mode.HISTORICAL)
                    try:
                        response = urlopen(url)
                    except URLError:
                        raise ConnectionError(f'could not connect to {url}')
                atcf_file = io.BytesIO()
                atcf_file.write(response.read())
                atcf_file.seek(0)
                if url.endswith('.gz'):
                    atcf_file = gzip.GzipFile(fileobj=atcf_file, mode='rb')

            if 'OFCL' in advisories and 'CARQ' not in advisories:
                self.__advisories_to_remove.append(ATCF_Advisory.CARQ)

            dataframe = read_atcf(
                atcf_file, advisories=advisories + self.__advisories_to_remove
            )
            dataframe.sort_values(['datetime', 'advisory'], inplace=True)
            dataframe.reset_index(inplace=True, drop=True)

            dataframe['track_start_time'] = dataframe['datetime'].copy()
            if ATCF_Advisory.BEST in self.advisories:
                dataframe.loc[dataframe['advisory'] == 'BEST', 'track_start_time'] = (
                    dataframe.loc[dataframe['advisory'] == 'BEST', 'datetime']
                    .sort_values()
                    .iloc[0]
                )

            dataframe.loc[dataframe['advisory'] != 'BEST', 'datetime'] += pandas.to_timedelta(
                dataframe.loc[dataframe['advisory'] != 'BEST', 'forecast_hours'].astype(int),
                unit='hours',
            )

            self.unfiltered_data = dataframe
            self.__previous_configuration = configuration

        # if location values have changed, recompute velocity
        location_hash = pandas.util.hash_pandas_object(self.__unfiltered_data['geometry'])

        if self.__location_hash is None or len(location_hash) != len(self.__location_hash):
            updated_locations = ~self.__unfiltered_data.index.isnull()
        else:
            updated_locations = location_hash != self.__location_hash
        updated_locations |= pandas.isna(self.__unfiltered_data['speed'])

        if updated_locations.any():
            self.__unfiltered_data.loc[updated_locations] = self.__compute_velocity(
                self.__unfiltered_data[updated_locations]
            )
            self.__location_hash = location_hash

        return self.__unfiltered_data

    @unfiltered_data.setter
    def unfiltered_data(self, dataframe: DataFrame):
        # fill missing values of MRD and MSLP in the OFCL advisory
        if 'OFCL' in self.advisories:
            tracks = separate_tracks(dataframe)

            if 'OFCL' in tracks:
                ofcl_tracks = tracks['OFCL']
                carq_tracks = tracks['CARQ']

                for initial_time, forecast in ofcl_tracks.items():
                    if initial_time in carq_tracks:
                        carq_forecast = carq_tracks[initial_time]
                    else:
                        carq_forecast = carq_tracks[list(carq_tracks)[0]]

                    relation = HollandBRelation()
                    holland_b = relation.holland_b(
                        max_sustained_wind_speed=carq_forecast['max_sustained_wind_speed'],
                        background_pressure=carq_forecast['background_pressure'],
                        central_pressure=carq_forecast['central_pressure'],
                    )

                    holland_b[holland_b == numpy.inf] = numpy.nan
                    holland_b = numpy.nanmean(holland_b)

                    mrd_missing = pandas.isna(forecast['radius_of_maximum_winds'])
                    mslp_missing = pandas.isna(forecast['central_pressure'])
                    radp_missing = pandas.isna(forecast['background_pressure'])

                    # fill OFCL maximum wind radius with the first entry from the CARQ advisory
                    forecast.loc[mrd_missing, 'radius_of_maximum_winds'] = carq_forecast[
                        'radius_of_maximum_winds'
                    ].iloc[0]

                    # fill OFCL background pressure with the first entry from the CARQ advisory central pressure (at sea level)
                    forecast.loc[radp_missing, 'background_pressure'] = carq_forecast[
                        'central_pressure'
                    ].iloc[0]

                    # fill OFCL central pressure (at sea level) with the 3rd hour entry, preserving Holland B
                    forecast.loc[mslp_missing, 'central_pressure'] = relation.central_pressure(
                        max_sustained_wind_speed=forecast.loc[
                            mslp_missing, 'max_sustained_wind_speed'
                        ],
                        background_pressure=forecast.loc[mslp_missing, 'background_pressure'],
                        holland_b=holland_b,
                    )

        if len(self.__advisories_to_remove) > 0:
            dataframe = dataframe[
                ~dataframe['advisory'].isin(
                    [value.value for value in self.__advisories_to_remove]
                )
            ]
            self.__advisories_to_remove = []

        self.__unfiltered_data = dataframe

    @property
    def __configuration(self) -> Dict[str, Any]:
        return {
            'id': self.nhc_code,
            'file_deck': self.file_deck,
            'advisories': self.advisories,
            'filename': self.filename,
        }

    @staticmethod
    def __compute_velocity(data: DataFrame) -> DataFrame:
        geodetic = Geod(ellps='WGS84')

        for advisory in pandas.unique(data['advisory']):
            advisory_data = data.loc[data['advisory'] == advisory]

            indices = numpy.array(
                [
                    numpy.where(advisory_data['datetime'] == unique_datetime)[0][0]
                    for unique_datetime in pandas.unique(advisory_data['datetime'])
                ]
            )
            shifted_indices = numpy.roll(indices, 1)
            shifted_indices[0] = 0

            indices = advisory_data.index[indices]
            shifted_indices = advisory_data.index[shifted_indices]

            _, inverse_azimuths, distances = geodetic.inv(
                advisory_data.loc[indices, 'longitude'],
                advisory_data.loc[indices, 'latitude'],
                advisory_data.loc[shifted_indices, 'longitude'],
                advisory_data.loc[shifted_indices, 'latitude'],
            )

            intervals = advisory_data.loc[indices, 'datetime'].diff()
            speeds = distances / (intervals / pandas.to_timedelta(1, 's'))
            bearings = pandas.Series(inverse_azimuths % 360, index=speeds.index)

            for index in indices:
                cluster_index = (
                    advisory_data['datetime'] == advisory_data.loc[index, 'datetime']
                )
                advisory_data.loc[cluster_index, 'speed'] = speeds[index]
                advisory_data.loc[cluster_index, 'direction'] = bearings[index]

            data.loc[data['advisory'] == advisory] = advisory_data

        data.loc[pandas.isna(data['speed']), 'speed'] = 0

        return data

    @property
    def __file_end_date(self):
        unique_dates = numpy.unique(self.unfiltered_data['datetime'])
        for date in unique_dates:
            if date >= numpy.datetime64(self.end_date):
                return date

    def __len__(self) -> int:
        return len(self.data)

    def __copy__(self) -> 'VortexTrack':
        instance = self.__class__(
            storm=self.unfiltered_data.copy(),
            start_date=self.start_date,
            end_date=self.end_date,
            file_deck=self.file_deck,
            advisories=self.advisories,
        )
        if self.filename is not None:
            instance.filename = self.filename
        return instance

    def __eq__(self, other: 'VortexTrack') -> bool:
        return self.data.equals(other.data)

    def __str__(self) -> str:
        return f'{self.nhc_code} ({" + ".join(pandas.unique(self.data["advisory"]).tolist())}) track with {len(self)} entries, spanning {self.distances:.2f} meters over {self.duration}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(repr(value) for value in [self.nhc_code, self.start_date, self.end_date, self.file_deck, self.advisories, self.filename])})'


class HollandBRelation:
    def __init__(self, rho: float = None):
        if rho is None:
            rho = 1.15
        self.rho = rho

    def holland_b(
        self,
        max_sustained_wind_speed: float,
        background_pressure: float,
        central_pressure: float,
    ) -> float:
        return ((max_sustained_wind_speed ** 2) * self.rho * numpy.exp(1)) / (
            background_pressure - central_pressure
        )

    def central_pressure(
        self, max_sustained_wind_speed: float, background_pressure: float, holland_b: float,
    ) -> float:
        return (
            -(max_sustained_wind_speed ** 2) * self.rho * numpy.exp(1)
        ) / holland_b + background_pressure

    def max_sustained_wind_speed(
        self, holland_b: float, background_pressure: float, central_pressure: float,
    ) -> float:
        return numpy.sqrt(
            holland_b * (background_pressure - central_pressure) / (self.rho * numpy.exp(1))
        )


def separate_tracks(data: DataFrame) -> Dict[str, Dict[str, DataFrame]]:
    """
    separate the given track data frame into advisories and tracks (forecasts / hindcasts)

    :param data: data frame of track
    :return: dictionary of forecasts for each advisory (aside from best track ``BEST``, which only has one hindcast)
    """

    tracks = {}
    for advisory in pandas.unique(data['advisory']):
        advisory_data = data[data['advisory'] == advisory]

        if advisory == 'BEST':
            advisory_data = advisory_data.sort_values('datetime')

        track_start_times = pandas.unique(advisory_data['track_start_time'])

        tracks[advisory] = {}
        for track_start_time in track_start_times:
            if advisory == 'BEST':
                track_data = advisory_data
            else:
                track_data = advisory_data[
                    advisory_data['track_start_time'] == pandas.to_datetime(track_start_time)
                ].sort_values('forecast_hours')

            tracks[advisory][
                f'{pandas.to_datetime(track_start_time):%Y%m%dT%H%M%S}'
            ] = track_data

    return tracks
