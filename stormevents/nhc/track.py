from datetime import datetime, timedelta
from functools import partial
import io
import logging
import os
from os import PathLike
import pathlib
from typing import Any, Dict, List, Union

import numpy
import pandas
from pandas import DataFrame
from pyproj import Geod
from shapely import ops
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPolygon,
    Polygon,
)
import typepigeon

from stormevents.nhc import nhc_storms
from stormevents.nhc.atcf import (
    ATCF_FileDeck,
    ATCF_Mode,
    ATCF_RecordType,
    get_atcf_entry,
    get_atcf_file,
    normalize_atcf_value,
    read_atcf,
)
from stormevents.nhc.storms import nhc_archive_storms
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
        mode: ATCF_Mode = None,
        record_type: ATCF_RecordType = None,
        filename: PathLike = None,
    ):
        """
        :param storm: storm ID, or storm name and year
        :param start_date: start date of track
        :param end_date: end date of track
        :param file_deck: ATCF file deck; one of `a`, `b`, `f`
        :param mode: ATCF mode; either `historical` or `realtime`
        :param record_type: ATCF advisory type; one of `BEST`, `OFCL`, `OFCP`, `HMON`, `CARQ`, `HWRF`
        :param filename: file path to `fort.22`

        >>> VortexTrack('AL112017')
        VortexTrack('AL112017', Timestamp('2017-08-30 00:00:00'), Timestamp('2017-09-13 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', None)

        >>> VortexTrack('AL112017', start_date='2017-09-04')
        VortexTrack('AL112017', datetime.datetime(2017, 9, 4, 0, 0), Timestamp('2017-09-13 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', None)

        >>> from datetime import timedelta
        >>> VortexTrack('AL112017', start_date=timedelta(days=2), end_date=timedelta(days=-1))
        VortexTrack('AL112017', Timestamp('2017-09-01 00:00:00'), Timestamp('2017-09-12 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', None)

        >>> VortexTrack('AL112017', file_deck='a')
        VortexTrack('AL112017', Timestamp('2017-08-27 06:00:00'), Timestamp('2017-09-16 15:00:00'), <ATCF_FileDeck.ADVISORY: 'a'>, <ATCF_Mode.historical: 'ARCHIVE'>, None, None)
        """

        self.__unfiltered_data = None
        self.__filename = None

        self.__remote_atcf = None
        self.__nhc_code = None
        self.__name = None
        self.__start_date = None
        self.__end_date = None
        self.__file_deck = None
        self.__mode = None
        self.__record_type = None

        self.__invalid_storm_name = False
        self.__location_hash = None

        self.filename = filename
        self.file_deck = file_deck
        self.mode = mode
        self.record_type = record_type

        if isinstance(storm, DataFrame):
            self.unfiltered_data = storm
        elif isinstance(storm, io.BytesIO):
            self.__remote_atcf = storm
        elif isinstance(storm, (str, PathLike, pathlib.Path)):
            if os.path.exists(storm):
                self.__filename = storm
            else:
                try:
                    self.nhc_code = storm
                except ValueError:
                    if pathlib.Path(storm).exists():
                        self.filename = storm
                    else:
                        raise

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
        mode: ATCF_Mode = None,
        record_type: str = None,
        filename: PathLike = None,
    ) -> 'VortexTrack':
        """
        :param name: storm name
        :param year: storm year
        :param start_date: start date of track
        :param end_date: end date of track
        :param file_deck: ATCF file deck; one of ``a``, ``b``, ``f``
        :param mode: ATCF mode; either ``historical`` or ``realtime``
        :param record_type: ATCF advisory type; one of ``BEST``, ``OFCL``, ``OFCP``, ``HMON``, ``CARQ``, ``HWRF``
        :param filename: file path to ``fort.22``

        >>> VortexTrack.from_storm_name('irma', 2017)
        VortexTrack('AL112017', Timestamp('2017-08-30 00:00:00'), Timestamp('2017-09-13 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', None)
        """

        year = int(year)
        atcf_id = get_atcf_entry(storm_name=name, year=year).name

        return cls(
            storm=atcf_id,
            start_date=start_date,
            end_date=end_date,
            file_deck=file_deck,
            mode=mode,
            record_type=record_type,
            filename=filename,
        )

    @classmethod
    def from_fort22(
        cls, fort22: PathLike, start_date: datetime = None, end_date: datetime = None,
    ) -> 'VortexTrack':
        """
        :param fort22: file path to ``fort.22``
        :param start_date: start date of track
        :param end_date: end date of track

        >>> VortexTrack.from_fort22('tests/data/input/test_from_fort22/irma2017_fort.22')
        VortexTrack('AL112017', Timestamp('2017-09-05 00:00:00'), Timestamp('2017-09-19 00:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', PosixPath('tests/data/input/test_from_fort22/irma2017_fort.22'))
        """

        filename = None
        if pathlib.Path(fort22).exists():
            filename = fort22

        return cls(
            storm=read_atcf(fort22),
            start_date=start_date,
            end_date=end_date,
            file_deck=None,
            mode=None,
            record_type=None,
            filename=filename,
        )

    @classmethod
    def from_atcf_file(
        cls, atcf: PathLike, start_date: datetime = None, end_date: datetime = None,
    ) -> 'VortexTrack':
        """
        :param atcf: file path to ATCF data
        :param start_date: start date of track
        :param end_date: end date of track

        >>> VortexTrack.from_atcf_file('tests/data/input/test_from_atcf/atcf.trk')
        VortexTrack('BT02008', Timestamp('2008-10-16 17:06:00'), Timestamp('2008-10-20 20:06:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', PosixPath('tests/data/input/test_from_atcf/florence2018_atcf.trk'))
        """

        filename = None
        if pathlib.Path(atcf).exists():
            filename = atcf

        return cls(
            storm=atcf,
            start_date=start_date,
            end_date=end_date,
            file_deck=None,
            mode=None,
            record_type=None,
            filename=filename,
        )

    @property
    def name(self) -> str:
        """
        :return: NHC storm name

        >>> track = VortexTrack('AL112017')
        >>> track.name
        'IRMA'
        """

        if self.__name is None:
            name = self.data['name'].value_counts()[:].index.tolist()[0]

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
        if file_deck is None:
            file_deck = ATCF_FileDeck.BEST
        elif not isinstance(file_deck, ATCF_FileDeck):
            file_deck = typepigeon.convert_value(file_deck, ATCF_FileDeck)
        self.__file_deck = file_deck

    @property
    def mode(self) -> ATCF_Mode:
        """
        :return: ATCF mode; either ``historical`` or ``realtime``
        """

        if self.__mode is None:
            if self.filename is None:
                mode = ATCF_Mode.realtime
                if self.nhc_code is not None:
                    archive_storms = nhc_archive_storms()
                    if self.nhc_code.upper() in archive_storms:
                        mode = ATCF_Mode.historical
            else:
                mode = ATCF_Mode.historical
            self.__mode = mode

        return self.__mode

    @mode.setter
    def mode(self, mode: ATCF_Mode):
        if mode is not None and not isinstance(mode, ATCF_Mode):
            mode = typepigeon.convert_value(mode, ATCF_Mode)
        self.__mode = mode

    @property
    def record_type(self) -> str:
        """
        :return: ATCF advisory type; one of ``BEST``, ``OFCL``, ``OFCP``, ``HMON``, ``CARQ``, ``HWRF``
        """

        if self.file_deck == ATCF_FileDeck.BEST:
            self.__record_type = ATCF_RecordType.best.value

        return self.__record_type

    @record_type.setter
    def record_type(self, record_type: ATCF_RecordType):
        # e.g. `BEST`, `OFCL`, `HWRF`, etc.
        if record_type is not None:
            if not isinstance(record_type, str):
                record_type = typepigeon.convert_value(record_type, str)
            record_type = record_type.upper()
            if record_type not in self.valid_record_types:
                raise ValueError(
                    f'invalid advisory "{record_type}"; not one of {self.valid_record_types}'
                )
        self.__record_type = record_type

    @property
    def valid_record_types(self) -> List[ATCF_RecordType]:
        if self.file_deck == ATCF_FileDeck.ADVISORY:
            # see ftp://ftp.nhc.noaa.gov/atcf/docs/nhc_techlist.dat
            # there are more but they may not have enough columns
            valid_record_types = [
                entry.value for entry in ATCF_RecordType if entry != ATCF_RecordType.best
            ]
        elif self.file_deck == ATCF_FileDeck.BEST:
            valid_record_types = [ATCF_RecordType.best.value]
        elif self.file_deck == ATCF_FileDeck.FIXED:
            valid_record_types = [entry.value for entry in ATCF_RecordType]
        else:
            raise NotImplementedError(f'file deck {self.file_deck.value} not implemented')

        return valid_record_types

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
            basin storm_number record_type            datetime  ...   direction     speed    name                    geometry
        0      AL           11        BEST 2017-08-30 00:00:00  ...    0.000000  0.000000  INVEST  POINT (-26.90000 16.10000)
        1      AL           11        BEST 2017-08-30 06:00:00  ...  274.421188  6.951105  INVEST  POINT (-28.30000 16.20000)
        2      AL           11        BEST 2017-08-30 12:00:00  ...  274.424523  6.947623    IRMA  POINT (-29.70000 16.30000)
        3      AL           11        BEST 2017-08-30 18:00:00  ...  270.154371  5.442611    IRMA  POINT (-30.80000 16.30000)
        4      AL           11        BEST 2017-08-30 18:00:00  ...  270.154371  5.442611    IRMA  POINT (-30.80000 16.30000)
        ..    ...          ...         ...                 ...  ...         ...       ...     ...                         ...
        168    AL           11        BEST 2017-09-12 12:00:00  ...  309.875306  7.262151    IRMA  POINT (-86.90000 33.80000)
        169    AL           11        BEST 2017-09-12 18:00:00  ...  315.455084  7.247674    IRMA  POINT (-88.10000 34.80000)
        170    AL           11        BEST 2017-09-13 00:00:00  ...  320.849994  5.315966    IRMA  POINT (-88.90000 35.60000)
        171    AL           11        BEST 2017-09-13 06:00:00  ...  321.042910  3.973414    IRMA  POINT (-89.50000 36.20000)
        172    AL           11        BEST 2017-09-13 12:00:00  ...  321.262133  3.961652    IRMA  POINT (-90.10000 36.80000)
        [173 rows x 22 columns]

        >>> track = VortexTrack('AL112017', file_deck='a')
        >>> track.data
              basin storm_number record_type            datetime  ...   direction      speed    name                    geometry
        0        AL           11        CARQ 2017-08-27 06:00:00  ...    0.000000   0.000000  INVEST  POINT (-17.40000 11.70000)
        1        AL           11        CARQ 2017-08-27 12:00:00  ...  281.524268   2.574642  INVEST  POINT (-17.90000 11.80000)
        2        AL           11        CARQ 2017-08-27 12:00:00  ...  281.524268   2.574642  INVEST  POINT (-13.30000 11.50000)
        3        AL           11        CARQ 2017-08-27 18:00:00  ...  281.528821   2.573747  INVEST  POINT (-18.40000 11.90000)
        4        AL           11        CARQ 2017-08-27 18:00:00  ...  281.528821   2.573747  INVEST  POINT (-16.00000 11.50000)
        ...     ...          ...         ...                 ...  ...         ...        ...     ...                         ...
        10739    AL           11        HMON 2017-09-16 09:00:00  ...   52.414833  11.903071          POINT (-84.30000 43.00000)
        10740    AL           11        HMON 2017-09-16 12:00:00  ...    7.196515   6.218772          POINT (-84.30000 41.00000)
        10741    AL           11        HMON 2017-09-16 12:00:00  ...    7.196515   6.218772          POINT (-82.00000 39.50000)
        10742    AL           11        HMON 2017-09-16 12:00:00  ...    7.196515   6.218772          POINT (-84.30000 44.00000)
        10743    AL           11        HMON 2017-09-16 15:00:00  ...  122.402907  22.540200          POINT (-81.90000 39.80000)
        [10744 rows x 22 columns
        """

        return self.unfiltered_data.loc[
            (self.unfiltered_data['datetime'] >= self.start_date)
            & (self.unfiltered_data['datetime'] <= self.end_date)
        ]

    def write(self, path: PathLike, overwrite: bool = False):
        """
        write track to file path

        :param path: output file path
        :param overwrite: overwrite existing file
        """

        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)
        if overwrite or not path.exists():
            if path.suffix == '.22':
                content = self.fort_22
            else:
                raise NotImplementedError(
                    'writing to files other than `*.22` not yet implemented'
                )
            with open(path, 'w') as f:
                f.write(content)
        else:
            logging.warning(f'skipping existing file "{path}"')

    @property
    def fort_22(self) -> str:
        record_numbers = self.__record_numbers
        lines = []

        dataframe = self.data

        for column in dataframe.select_dtypes(include=['float']):
            if column not in ['latitude', 'longitude']:
                dataframe.loc[:, column] = (
                    dataframe[column].round(0).astype('Int64', copy=False)
                )

        for index, (_, record) in enumerate(dataframe.iterrows()):
            line = []

            line.extend(
                [
                    f'{record["basin"]:<2}',
                    f'{record["storm_number"]:>3}',
                    f'{record["datetime"]:%Y%m%d%H}'.rjust(11),
                    f'{"":3}',
                    f'{record["record_type"]:>5}',
                    f'{normalize_atcf_value((record["datetime"] - self.start_date) / timedelta(hours=1), to_type=int):>4}',
                ]
            )

            latitude = normalize_atcf_value(
                record['latitude'] / 0.1, to_type=int, round_digits=1
            )
            if latitude >= 0:
                line.append(f'{latitude:>4}N')
            else:
                line.append(f'{latitude * -.1:>4}S')

            longitude = normalize_atcf_value(
                record['longitude'] / 0.1, to_type=int, round_digits=1
            )
            if longitude >= 0:
                line.append(f'{longitude:>5}E')
            else:
                line.append(f'{longitude * -1:>5}W')

            line.extend(
                [
                    f'{normalize_atcf_value(record["max_sustained_wind_speed"], to_type=int, round_digits=0):>4}',
                    f'{normalize_atcf_value(record["central_pressure"], to_type=int, round_digits=0):>5}',
                    f'{record["development_level"]:>3}',
                    f'{normalize_atcf_value(record["isotach"], to_type=int, round_digits=0):>4}',
                    f'{record["quadrant"]:>4}',
                    f'{normalize_atcf_value(record["radius_for_NEQ"], to_type=int, round_digits=0):>5}',
                    f'{normalize_atcf_value(record["radius_for_SEQ"], to_type=int, round_digits=0):>5}',
                    f'{normalize_atcf_value(record["radius_for_SWQ"], to_type=int, round_digits=0):>5}',
                    f'{normalize_atcf_value(record["radius_for_NWQ"], to_type=int, round_digits=0):>5}',
                ]
            )

            if record['background_pressure'] is None:
                record['background_pressure'] = self.data['background_pressure'].iloc[
                    index - 1
                ]

            try:
                if (
                    not pandas.isna(record['central_pressure'])
                    and record['background_pressure'] <= record['central_pressure']
                ):
                    if 1013 > record['central_pressure']:
                        background_pressure = 1013
                    else:
                        background_pressure = normalize_atcf_value(
                            record['central_pressure'] + 1, to_type=int, round_digits=0,
                        )
                else:
                    background_pressure = normalize_atcf_value(
                        record['background_pressure'], to_type=int, round_digits=0,
                    )
            except:
                background_pressure = normalize_atcf_value(
                    record['background_pressure'], to_type=int, round_digits=0,
                )
            line.append(f'{background_pressure:>5}')

            line.extend(
                [
                    f'{normalize_atcf_value(record["radius_of_last_closed_isobar"], to_type=int, round_digits=0):>5}',
                    f'{normalize_atcf_value(record["radius_of_maximum_winds"], to_type=int, round_digits=0):>4}',
                    f'{"":>5}',  # gust
                    f'{"":>4}',  # eye
                    f'{"":>4}',  # subregion
                    f'{"":>4}',  # maxseas
                    f'{"":>4}',  # initials
                    f'{record["direction"]:>3}',
                    f'{record["speed"]:>4}',
                    f'{record["name"]:^12}',
                ]
            )

            # from this point forwards it's all aswip
            line.append(f'{record_numbers[index]:>4}')

            lines.append(','.join(line))

        return '\n'.join(lines)

    @property
    def linestring(self) -> MultiLineString:
        """
        :return: spatial linestring of current track
        """

        linestrings = [
            self.data[self.data['record_type'] == record_type]
            .sort_values('datetime')['geometry']
            .drop_duplicates()
            for record_type in pandas.unique(self.data['record_type'])
        ]

        linestrings = [
            LineString(linestring.tolist())
            for linestring in linestrings
            if len(linestring) > 1
        ]

        if len(linestrings) > 0:
            geometry = MultiLineString(linestrings)
        else:
            geometry = GeometryCollection(linestrings)

        return geometry

    @property
    def distance(self) -> float:
        """
        :return: length, in meters, of the track over the default WGS84 that comes with pyPROJ
        """

        geodetic = Geod(ellps='WGS84')
        _, _, distances = geodetic.inv(
            self.data['longitude'].iloc[:-1],
            self.data['latitude'].iloc[:-1],
            self.data['longitude'].iloc[1:],
            self.data['latitude'].iloc[1:],
        )
        return numpy.sum(distances)

    def isotachs(
        self, wind_speed: float, segments: int = 91
    ) -> Dict[str, Dict[datetime, Polygon]]:
        """
        calculate the isotach at the given speed at every time in the dataset

        :param wind_speed: wind speed to extract (in knots)
        :param segments: number of discretization points per quadrant
        :return: list of isotachs as polygons for each record type
        """

        # collect the attributes needed from the forcing to generate swath
        data = self.data[self.data['isotach'] == wind_speed]

        # enumerate quadrants
        quadrant_names = [
            'radius_for_NEQ',
            'radius_for_NWQ',
            'radius_for_SWQ',
            'radius_for_SEQ',
        ]

        # convert quadrant radii from nautical miles to meters
        data[quadrant_names] *= 1852.0

        geodetic = Geod(ellps='WGS84')

        # generate overall swath based on the desired isotach
        isotachs = {}
        for record_type in pandas.unique(data['record_type']):
            record_type_data = data[data['record_type'] == record_type]

            record_type_isotachs = {}
            for index, row in record_type_data.iterrows():
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

                    record_type_isotachs[row['datetime']] = isotach

            if len(record_type_isotachs) > 0:
                isotachs[record_type] = record_type_isotachs

        return isotachs

    def wind_swaths(self, wind_speed: int, segments: int = 91) -> Dict[str, Polygon]:
        """
        extract the wind swath of the BestTrackForcing class object as a Polygon object

        :param wind_speed: wind speed in knots (one of ``34``, ``50``, or ``64``)
        :param segments: number of discretization points per quadrant (default = ``91``)
        """

        valid_isotach_values = [34, 50, 64]
        assert (
            wind_speed in valid_isotach_values
        ), f'isotach must be one of {valid_isotach_values}'

        record_type_isotachs = self.isotachs(wind_speed=wind_speed, segments=segments)

        wind_swaths = {}
        for record_type, isotachs in record_type_isotachs.items():
            isotachs = list(isotachs.values())
            convex_hulls = []
            for index in range(len(isotachs) - 1):
                convex_hulls.append(
                    ops.unary_union([isotachs[index], isotachs[index + 1]]).convex_hull
                )

            # get the union of polygons
            wind_swaths[record_type] = ops.unary_union(convex_hulls)

        return wind_swaths

    @property
    def duration(self) -> pandas.Timedelta:
        """
        :return: duration of current track
        """

        return self.data['datetime'].diff().sum()

    @property
    def remote_atcf(self) -> io.BytesIO:
        """
        :return: ATCF file from server
        """

        configuration = {
            'storm_id': self.nhc_code,
            'file_deck': self.file_deck,
            'mode': self.mode,
            'filename': self.filename,
        }

        if (
            self.nhc_code is not None
            and self.__remote_atcf is None
            or configuration != self.__previous_configuration
        ):
            self.__remote_atcf = get_atcf_file(self.nhc_code, self.file_deck, self.mode)

        return self.__remote_atcf

    @property
    def unfiltered_data(self) -> DataFrame:
        """
        :return: data frame containing all track data for the specified storm and file deck
        """

        configuration = self.__configuration

        # only download new file if the configuration has changed since the last download
        if (
            self.__unfiltered_data is None
            or len(self.__unfiltered_data) == 0
            or configuration != self.__previous_configuration
        ):
            if configuration['filename'] is not None:
                record_types = None if self.record_type is None else [self.record_type]
                atcf_file = configuration['filename']
            else:
                record_types = (
                    self.valid_record_types if self.record_type is None else [self.record_type]
                )
                atcf_file = self.remote_atcf

            dataframe = read_atcf(atcf_file, record_types=record_types)
            dataframe.sort_values(['datetime', 'record_type'], inplace=True)
            dataframe.reset_index(inplace=True, drop=True)

            self.__unfiltered_data = dataframe
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
        self.__unfiltered_data = dataframe

    @property
    def __configuration(self) -> Dict[str, Any]:
        return {
            'id': self.nhc_code,
            'file_deck': self.file_deck,
            'mode': self.mode,
            'record_type': self.record_type,
            'filename': self.filename,
        }

    @property
    def __record_numbers(self) -> numpy.ndarray:
        record_numbers = numpy.empty((len(self.data)), dtype=int)
        for index, record_datetime in enumerate(self.data['datetime'].unique()):
            record_numbers[self.data['datetime'] == record_datetime] = index + 1
        return record_numbers

    @staticmethod
    def __compute_velocity(data: DataFrame) -> DataFrame:
        geodetic = Geod(ellps='WGS84')

        for record_type in pandas.unique(data['record_type']):
            record_data = data.loc[data['record_type'] == record_type]

            indices = numpy.array(
                [
                    numpy.where(record_data['datetime'] == unique_datetime)[0][0]
                    for unique_datetime in pandas.unique(record_data['datetime'])
                ]
            )
            shifted_indices = numpy.roll(indices, 1)
            shifted_indices[0] = 0

            indices = record_data.index[indices]
            shifted_indices = record_data.index[shifted_indices]

            _, inverse_azimuths, distances = geodetic.inv(
                record_data.loc[indices, 'longitude'],
                record_data.loc[indices, 'latitude'],
                record_data.loc[shifted_indices, 'longitude'],
                record_data.loc[shifted_indices, 'latitude'],
            )

            intervals = record_data.loc[indices, 'datetime'].diff()
            speeds = distances / (intervals / pandas.to_timedelta(1, 's'))
            bearings = pandas.Series(inverse_azimuths % 360, index=speeds.index)

            for index in indices:
                cluster_index = record_data['datetime'] == record_data.loc[index, 'datetime']
                record_data.loc[cluster_index, 'speed'] = speeds[index]
                record_data.loc[cluster_index, 'direction'] = bearings[index]

            data.loc[data['record_type'] == record_type] = record_data

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
        return self.__class__(
            storm=self.unfiltered_data.copy(),
            start_date=self.start_date,
            end_date=self.end_date,
            file_deck=self.file_deck,
            record_type=self.record_type,
            filename=self.filename,
        )

    def __eq__(self, other: 'VortexTrack') -> bool:
        return self.data.equals(other.data)

    def __str__(self) -> str:
        return f'{self.nhc_code} ({" + ".join(pandas.unique(self.data["record_type"]).tolist())}) track with {len(self)} entries, spanning {self.distance:.2f} meters over {self.duration}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(repr(value) for value in [self.nhc_code, self.start_date, self.end_date, self.file_deck, self.mode, self.record_type, self.filename])})'
