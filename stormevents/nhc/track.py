from datetime import datetime, timedelta
import io
import logging
from numbers import Number
import os
from os import PathLike
import pathlib
from typing import List, Union

from dateutil.parser import parse as parse_date
import numpy
import pandas
from pandas import DataFrame
from pyproj import Geod
from shapely import ops
from shapely.geometry import LineString, Polygon
import typepigeon

from stormevents.nhc import nhc_storms
from stormevents.nhc.atcf import (
    ATCF_FileDeck,
    atcf_id_from_storm_name,
    ATCF_Mode,
    ATCF_RecordType,
    get_atcf_file,
    normalize_atcf_value,
    read_atcf,
)


class VortexTrack:
    """
    interface to an ATCF vortex track (i.e. HURDAT, best track, HWRF, etc.)

    .. code-block:: python

        # retrieve vortex data from the Internet from its ID
        vortex = VortexTrack('AL112017')

    .. code-block:: python

        # you can also use the storm name and year in the lookup
        vortex = VortexTrack('irma2017')

    .. code-block:: python

        # read vortex data from an existing ATCF track file (`*.trk`)
        vortex = VortexTrack.from_atcf_file('atcf.trk')

    .. code-block:: python

        # read vortex data from an existing file in the ADCIRC `fort.22` format
        vortex = VortexTrack.from_fort22('fort.22')

    .. code-block:: python

        # write to a file in the ADCIRC `fort.22` format
        vortex.write('fort.22')

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
        """

        self.__dataframe = None
        self.__filename = None

        self.__remote_atcf = None
        self.__storm_id = None
        self.__name = None
        self.__start_date = start_date  # initially used to filter A-deck here
        self.__end_date = None
        self.__file_deck = None
        self.__mode = None
        self.__record_type = None

        self.__invalid_storm_name = False
        self.__location_hash = None

        self.file_deck = file_deck
        self.mode = mode
        self.record_type = record_type
        self.filename = filename

        if isinstance(storm, DataFrame):
            self.dataframe = storm
        elif isinstance(storm, io.BytesIO):
            self.__remote_atcf = storm
        elif isinstance(storm, (str, PathLike, pathlib.Path)):
            if os.path.exists(storm):
                self.__remote_atcf = io.open(storm, 'rb')
            else:
                try:
                    self.storm_id = storm
                except ValueError:
                    if pathlib.Path(storm).exists():
                        self.filename = storm
                    else:
                        raise

        self.__previous_configuration = {
            'storm_id': self.storm_id,
            'file_deck': self.file_deck,
            'mode': self.mode,
            'filename': self.filename,
        }

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
    ):
        year = int(year)
        atcf_id = atcf_id_from_storm_name(storm_name=name, year=year)
        if atcf_id is None:
            raise ValueError(f'No storm found with name "{name}" in {year}')
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
        read a ``fort.22`` file
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
        read an ATCF file
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
        if self.__name is None:
            name = self.data['name'].value_counts()[:].index.tolist()[0]

            if name.strip() == '':
                storms = nhc_storms(year=self.year)
                if self.storm_id.upper() in storms.index:
                    storm = storms.loc[self.storm_id.upper()]
                    name = storm['name'].lower()

            self.__name = name

        return self.__name

    @property
    def basin(self) -> str:
        return self.data['basin'].iloc[0]

    @property
    def storm_number(self) -> str:
        return self.data['storm_number'].iloc[0]

    @property
    def year(self) -> int:
        return self.data['datetime'].iloc[0].year

    @property
    def storm_id(self) -> str:
        if self.__storm_id is None and not self.__invalid_storm_name:
            if self.__dataframe is not None:
                storm_id = (
                    f'{self.__dataframe["basin"].iloc[-1]}'
                    f'{self.__dataframe["storm_number"].iloc[-1]}'
                    f'{self.__dataframe["datetime"].iloc[-1].year}'
                )
                try:
                    self.storm_id = storm_id
                except ValueError:
                    try:
                        storm_id = atcf_id_from_storm_name(
                            storm_name=self.__dataframe['name'].tolist()[-1],
                            year=self.__dataframe['datetime'].tolist()[-1].year,
                        )
                        self.storm_id = storm_id
                    except ValueError:
                        self.__invalid_storm_name = True
        return self.__storm_id

    @storm_id.setter
    def storm_id(self, storm_id: str):
        if storm_id is not None:
            # check if name+year was given instead of basin+number+year
            digits = sum([1 for character in storm_id if character.isdigit()])

            if digits == 4:
                atcf_id = atcf_id_from_storm_name(
                    storm_name=storm_id[:-4], year=int(storm_id[-4:])
                )
                if atcf_id is None:
                    raise ValueError(f'No storm with id: {storm_id}')
                storm_id = atcf_id
        self.__storm_id = storm_id

    @property
    def start_date(self) -> datetime:
        return self.__start_date

    @start_date.setter
    def start_date(self, start_date: datetime):
        data_start = self.dataframe['datetime'].iloc[0]
        data_end = self.dataframe['datetime'].iloc[-1]

        if start_date is None:
            start_date = data_start
        else:
            # interpret timedelta as a temporal movement around start / end
            if isinstance(start_date, timedelta) or isinstance(start_date, Number):
                start_date = typepigeon.convert_value(start_date, timedelta)
                if start_date >= timedelta(0):
                    start_date = data_start + start_date
                else:
                    start_date = data_end + start_date
            elif not isinstance(start_date, datetime):
                start_date = parse_date(start_date)

            if start_date < data_start or start_date > data_end:
                raise ValueError(f'"{self.start_date}" outside "{data_start} - {data_end}"')

        self.__start_date = start_date

    @property
    def end_date(self) -> datetime:
        return self.__end_date

    @end_date.setter
    def end_date(self, end_date: datetime):
        data_start = self.dataframe['datetime'].iloc[0]
        data_end = self.dataframe['datetime'].iloc[-1]

        if end_date is None:
            end_date = data_end
        else:
            # interpret timedelta as a temporal movement around start / end
            if isinstance(end_date, timedelta) or isinstance(end_date, Number):
                end_date = typepigeon.convert_value(end_date, timedelta)
                if end_date >= timedelta(0):
                    end_date = data_start + end_date
                else:
                    end_date = data_end + end_date
            elif not isinstance(end_date, datetime):
                end_date = parse_date(end_date)

            if end_date < data_start or end_date > data_end:
                raise ValueError(f'"{self.end_date}" outside "{data_start} - {data_end}"')

            if end_date <= self.start_date:
                raise ValueError(f'"{self.end_date}" is not after "{self.start_date}"')

        self.__end_date = end_date

    @property
    def file_deck(self) -> ATCF_FileDeck:
        return self.__file_deck

    @file_deck.setter
    def file_deck(self, file_deck: ATCF_FileDeck):
        if file_deck is None:
            file_deck = ATCF_FileDeck.a
        elif not isinstance(file_deck, ATCF_FileDeck):
            file_deck = normalize_atcf_value(file_deck, ATCF_FileDeck)
        self.__file_deck = file_deck

    @property
    def mode(self) -> ATCF_Mode:
        return self.__mode

    @mode.setter
    def mode(self, mode: ATCF_Mode):
        if mode is None:
            mode = ATCF_Mode.historical
        elif not isinstance(mode, ATCF_Mode):
            mode = normalize_atcf_value(mode, ATCF_Mode)
        self.__mode = mode

    @property
    def record_type(self) -> str:
        """
        :return: ATCF advisory type; one of `BEST`, `OFCL`, `OFCP`, `HMON`, `CARQ`, `HWRF`
        """

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
        if self.file_deck == ATCF_FileDeck.a:
            # see ftp://ftp.nhc.noaa.gov/atcf/docs/nhc_techlist.dat
            # there are more but they may not have enough columns
            valid_record_types = ['OFCL', 'OFCP', 'HWRF', 'HMON', 'CARQ']
        elif self.file_deck == ATCF_FileDeck.b:
            valid_record_types = ['BEST']
        else:
            raise NotImplementedError(f'file deck {self.file_deck.value} not implemented')

        return valid_record_types

    @property
    def filename(self) -> pathlib.Path:
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
        """

        start_date_mask = self.dataframe['datetime'] >= self.start_date
        if self.end_date is None:
            return self.dataframe.loc[start_date_mask]
        else:
            return self.dataframe.loc[
                start_date_mask & (self.dataframe['datetime'] <= self.__file_end_date)
            ]

    def write(self, path: PathLike, overwrite: bool = False):
        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)
        if overwrite or not path.exists():
            with open(path, 'w') as f:
                f.write(str(self))
        else:
            logging.warning(f'skipping existing file "{path}"')

    def __str__(self):
        record_numbers = self.record_numbers
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
    def linestring(self) -> LineString:
        """
        :return: spatial linestring of current track
        """

        return LineString(self.data[['longitude', 'latitude']])

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

    def isotachs(self, wind_speed: float, segments: int = 91) -> List[Polygon]:
        """
        calculate the isotach at the given speed at every time in the dataset

        :param wind_speed: wind speed to extract (in knots)
        :param segments: number of discretization points per quadrant
        :return: list of isotachs as polygons
        """

        ## Collect the attributes needed from the forcing to generate swath
        data = self.data[self.data['isotach'] == wind_speed]

        # convert quadrant radii from nautical miles to meters
        quadrants = ['radius_for_NEQ', 'radius_for_NWQ', 'radius_for_SWQ', 'radius_for_SEQ']
        data[quadrants] *= 1852.0  # nautical miles to meters

        geodetic = Geod(ellps='WGS84')

        ## Generate overall swath based on the desired isotach
        polygons = []
        for index, row in data.iterrows():
            # get the starting angle range for NEQ based on storm direction
            rot_angle = 360 - row['direction']
            start_angle = 0 + rot_angle
            end_angle = 90 + rot_angle

            # append quadrants in counter-clockwise direction from NEQ
            arcs = []
            for quadrant in quadrants:
                # enter the angle range for this quadrant
                theta = numpy.linspace(start_angle, end_angle, segments)
                # move angle to next quadrant
                start_angle = start_angle + 90
                end_angle = end_angle + 90
                # skip if quadrant radius is zero
                if row[quadrant] <= 1.0:
                    continue
                # make the coordinate list for this quadrant
                ## entering origin
                coords = [row[['longitude', 'latitude']].tolist()]
                # using forward geodetic (origin,angle,dist)
                for az12 in theta:
                    lont, latt, backaz = geodetic.fwd(
                        lons=row['longitude'],
                        lats=row['latitude'],
                        az=az12,
                        dist=row[quadrant],
                    )
                    coords.append((lont, latt))
                ## start point equals last point
                coords.append(coords[0])
                # enter quadrant as new polygon
                arcs.append(Polygon(coords))
            polygons.append(ops.unary_union(arcs))
        return polygons

    def wind_swath(self, isotach: int, segments: int = 91) -> Polygon:
        """
        extract the wind swath of the BestTrackForcing class object as a Polygon object

        :param isotach: the wind swath to extract (34-kt, 50-kt, or 64-kt)
        :param segments: number of discretization points per quadrant (default = 91)
        """

        # parameter
        # isotach should be one of 34, 50, 64
        valid_isotach_values = [34, 50, 64]
        assert (
            isotach in valid_isotach_values
        ), f'`isotach` value in `get_wind_swath` must be one of {valid_isotach_values}'

        isotachs = self.isotachs(wind_speed=isotach, segments=segments)

        convex_hulls = []
        for index in range(len(isotachs) - 1):
            convex_hulls.append(
                ops.unary_union([isotachs[index], isotachs[index + 1]]).convex_hull
            )

        # get the union of polygons
        return ops.unary_union(convex_hulls)

    @property
    def duration(self) -> float:
        return self.data['datetime'].diff().sum()

    @property
    def remote_atcf(self) -> io.BytesIO:
        """
        :return: ATCF file from server
        """

        configuration = {
            'storm_id': self.storm_id,
            'file_deck': self.file_deck,
            'mode': self.mode,
            'filename': self.filename,
        }

        if (
            self.storm_id is not None
            and self.__remote_atcf is None
            or configuration != self.__previous_configuration
        ):
            self.__remote_atcf = get_atcf_file(self.storm_id, self.file_deck, self.mode)

        return self.__remote_atcf

    @property
    def dataframe(self) -> DataFrame:
        configuration = {
            'storm_id': self.storm_id,
            'file_deck': self.file_deck,
            'mode': self.mode,
            'filename': self.filename,
        }

        # only download new file if the configuration has changed since the last download
        if (
            self.__dataframe is None
            or len(self.__dataframe) == 0
            or configuration != self.__previous_configuration
        ):
            if configuration['filename'] is not None:
                record_types = None if self.record_type is None else [self.record_type]
                atcf_file = configuration['filename']
            else:
                # Only accept request `BEST` or `OFCL` (official) records by default
                record_types = (
                    self.valid_record_types if self.record_type is None else [self.record_type]
                )
                atcf_file = self.remote_atcf

            dataframe = read_atcf(atcf_file, record_types=record_types)
            dataframe.sort_values(['datetime', 'record_type'], inplace=True)
            dataframe.reset_index(inplace=True, drop=True)

            self.__dataframe = dataframe
            self.__previous_configuration = configuration

        # if location values have changed, recompute velocity
        location_hash = pandas.util.hash_pandas_object(
            self.__dataframe[['longitude', 'latitude']]
        ).sum()
        if self.__location_hash is None or location_hash != self.__location_hash:
            if self.__location_hash is None:
                velocity_update_indices = pandas.isna(self.__dataframe['speed'])
            else:
                velocity_update_indices = self.__dataframe.index.isnull()

            self.__dataframe[velocity_update_indices] = self.__compute_velocity(
                self.__dataframe[velocity_update_indices]
            )
            self.__location_hash = location_hash

        return self.__dataframe

    @dataframe.setter
    def dataframe(self, dataframe: DataFrame):
        self.__dataframe = dataframe

    @property
    def record_numbers(self) -> numpy.ndarray:
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
        unique_dates = numpy.unique(self.dataframe['datetime'])
        for date in unique_dates:
            if date >= numpy.datetime64(self.end_date):
                return date

    def __copy__(self) -> 'VortexTrack':
        return self.__class__(
            storm=self.dataframe.copy(),
            start_date=self.start_date,
            end_date=self.end_date,
            file_deck=self.file_deck,
            record_type=self.record_type,
        )

    def __eq__(self, other: 'VortexTrack') -> bool:
        return self.data.equals(other.data)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(repr(value) for value in [self.storm_id, self.start_date, self.end_date, self.file_deck, self.mode, self.record_type, self.filename])})'
