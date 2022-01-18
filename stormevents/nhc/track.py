from datetime import datetime, timedelta
import ftplib
from functools import wraps
import gzip
import io
import os
from os import PathLike
import pathlib
import socket
from time import sleep
from typing import Collection, List, TextIO, Union

from dateutil.parser import parse as parse_date
import numpy
import pandas
from pandas import DataFrame
from pyproj import Geod
from shapely import ops
from shapely.geometry import Polygon
import typepigeon

from stormevents.nhc import nhc_storms
from stormevents.nhc.atcf import (
    ATCF_FileDeck,
    atcf_id_from_storm_name,
    ATCF_Mode,
    ATCF_RecordType,
    atcf_url,
    normalize_atcf_value,
)
from stormevents.utilities import get_logger

LOGGER = get_logger(__name__)


class VortexTrack:
    """
    interface to an ATCF vortex track (i.e. HURDAT, best track, etc.)

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
        self.__dataframe = None
        self.__filename = None

        self.__atcf = None
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
            self.__atcf = storm
        elif isinstance(storm, (str, PathLike, pathlib.Path)):
            if os.path.exists(storm):
                self.__atcf = io.open(storm, 'rb')
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

    @property
    def filename(self) -> pathlib.Path:
        return self.__filename

    @filename.setter
    def filename(self, filename: PathLike):
        if filename is not None and not isinstance(filename, pathlib.Path):
            filename = pathlib.Path(filename)
        self.__filename = filename

    def __str__(self):
        record_numbers = self.record_numbers
        lines = []

        dataframe = self.data

        for column in dataframe.select_dtypes(include=['float']):
            if column not in ['latitude', 'longitude']:
                dataframe.loc[:, column] = (
                    dataframe[column].round(0).astype('Int64', copy=False)
                )

        for i, (_, row) in enumerate(dataframe.iterrows()):
            line = []

            line.extend(
                [
                    f'{row["basin"]:<2}',
                    f'{row["storm_number"]:>3}',
                    f'{row["datetime"]:%Y%m%d%H}'.rjust(11),
                    f'{"":3}',
                    f'{row["record_type"]:>5}',
                    f'{normalize_atcf_value((row["datetime"] - self.start_date) / timedelta(hours=1), to_type=int):>4}',
                ]
            )

            latitude = normalize_atcf_value(row['latitude'] / 0.1, to_type=int, round_digits=1)
            if latitude >= 0:
                line.append(f'{latitude:>4}N')
            else:
                line.append(f'{latitude * -.1:>4}S')

            longitude = normalize_atcf_value(
                row['longitude'] / 0.1, to_type=int, round_digits=1
            )
            if longitude >= 0:
                line.append(f'{longitude:>5}E')
            else:
                line.append(f'{longitude * -1:>5}W')

            line.extend(
                [
                    f'{normalize_atcf_value(row["max_sustained_wind_speed"], to_type=int, round_digits=0):>4}',
                    f'{normalize_atcf_value(row["central_pressure"], to_type=int, round_digits=0):>5}',
                    f'{row["development_level"]:>3}',
                    f'{normalize_atcf_value(row["isotach"], to_type=int, round_digits=0):>4}',
                    f'{row["quadrant"]:>4}',
                    f'{normalize_atcf_value(row["radius_for_NEQ"], to_type=int, round_digits=0):>5}',
                    f'{normalize_atcf_value(row["radius_for_SEQ"], to_type=int, round_digits=0):>5}',
                    f'{normalize_atcf_value(row["radius_for_SWQ"], to_type=int, round_digits=0):>5}',
                    f'{normalize_atcf_value(row["radius_for_NWQ"], to_type=int, round_digits=0):>5}',
                ]
            )

            if row['background_pressure'] is None:
                row['background_pressure'] = self.data['background_pressure'].iloc[i - 1]
            if (
                not pandas.isna(row['central_pressure'])
                and row['background_pressure'] <= row['central_pressure']
                and 1013 > row['central_pressure']
            ):
                background_pressure = 1013
            elif (
                not pandas.isna(row['central_pressure'])
                and row['background_pressure'] <= row['central_pressure']
                and 1013 <= row['central_pressure']
            ):
                background_pressure = normalize_atcf_value(
                    row['central_pressure'] + 1, to_type=int, round_digits=0,
                )
            else:
                background_pressure = normalize_atcf_value(
                    row['background_pressure'], to_type=int, round_digits=0,
                )
            line.append(f'{background_pressure:>5}')

            line.extend(
                [
                    f'{normalize_atcf_value(row["radius_of_last_closed_isobar"], to_type=int, round_digits=0):>5}',
                    f'{normalize_atcf_value(row["radius_of_maximum_winds"], to_type=int, round_digits=0):>4}',
                    f'{"":>5}',  # gust
                    f'{"":>4}',  # eye
                    f'{"":>4}',  # subregion
                    f'{"":>4}',  # maxseas
                    f'{"":>4}',  # initials
                    f'{row["direction"]:>3}',
                    f'{row["speed"]:>4}',
                    f'{row["name"]:^12}',
                ]
            )

            # from this point forwards it's all aswip
            line.append(f'{record_numbers[i]:>4}')

            lines.append(','.join(line))

        return '\n'.join(lines)

    def write(self, path: PathLike, overwrite: bool = False):
        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)
        if overwrite or not path.exists():
            with open(path, 'w') as f:
                f.write(str(self))
        else:
            LOGGER.warning(f'skipping existing file "{path}"')

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
    def track_length(self) -> float:
        geodetic = Geod(ellps='WGS84')

        forward_azimuths, inverse_azimuths, distances = geodetic.inv(
            self.data['longitude'].iloc[:-1],
            self.data['latitude'].iloc[:-1],
            self.data['longitude'].iloc[1:],
            self.data['latitude'].iloc[1:],
        )

        return numpy.sum(distances)

    @property
    def start_date(self) -> datetime:
        return self.__start_date

    @start_date.setter
    def start_date(self, start_date: datetime):
        if start_date is None:
            start_date = self.dataframe['datetime'].iloc[0]
        else:
            if not isinstance(start_date, datetime):
                start_date = parse_date(start_date)
            if (
                start_date < self.dataframe['datetime'].iloc[0]
                or start_date > self.dataframe['datetime'].iloc[-1]
            ):
                raise ValueError(
                    f'given start date is outside of data bounds ({self.dataframe["datetime"].iloc[0]} - {self.dataframe["datetime"].iloc[-1]})'
                )
        self.__start_date = start_date

    @property
    def end_date(self) -> datetime:
        return self.__end_date

    @end_date.setter
    def end_date(self, end_date: datetime):
        if end_date is None:
            end_date = self.dataframe['datetime'].iloc[-1]
        else:
            if not isinstance(end_date, datetime):
                end_date = parse_date(end_date)
            if (
                end_date < self.dataframe['datetime'].iloc[0]
                or end_date > self.dataframe['datetime'].iloc[-1]
            ):
                raise ValueError(
                    f'given end date is outside of data bounds ({self.dataframe["datetime"].iloc[0]} - {self.dataframe["datetime"].iloc[-1]})'
                )
            if end_date <= self.start_date:
                raise ValueError(f'end date must be after start date ({self.start_date})')
        self.__end_date = end_date

    @property
    def duration(self) -> float:
        d = (self.end_date - self.start_date) / timedelta(days=1)
        return d

    @property
    def file_deck(self) -> ATCF_FileDeck:
        return self.__file_deck

    @property
    def name(self) -> str:
        if self.__name is None:
            name = self.data['name'].value_counts()[:].index.tolist()[0]

            if name.strip() == '':
                storms = nhc_storms(year=self.year)
                if self.storm_id.lower() in storms.index:
                    storm = storms.loc[self.storm_id.lower()]
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
    def datetime(self):
        return self.data['datetime']

    @property
    def central_pressure(self):
        return self.data['central_pressure']

    @property
    def speed(self):
        return self.data['speed']

    @property
    def direction(self):
        return self.data['direction']

    @property
    def longitude(self):
        return self.data['longitude']

    @property
    def latitude(self):
        return self.data['latitude']

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
        return self.__record_type

    @record_type.setter
    def record_type(self, record_type: ATCF_RecordType):
        # e.g. BEST, OFCL, HWRF, etc.
        if record_type is not None:
            if not isinstance(record_type, str):
                record_type = typepigeon.convert_value(record_type, str)
            record_type = record_type.upper()
            if self.file_deck == ATCF_FileDeck.a:
                # see ftp://ftp.nhc.noaa.gov/atcf/docs/nhc_techlist.dat
                # there are more but they may not have enough columns
                allowed_record_types = ['OFCL', 'OFCP', 'HWRF', 'HMON', 'CARQ']
            elif self.file_deck == ATCF_FileDeck.b:
                allowed_record_types = ['BEST']
            else:
                raise NotImplementedError(f'file deck {self.file_deck.value} not implemented')
            if record_type not in allowed_record_types:
                raise ValueError(
                    f'request_record_type = {record_type} not allowed, select from {allowed_record_types}'
                )
        self.__record_type = record_type

    @property
    def data(self) -> DataFrame:
        """
        retrieve track data for the given parameters as a data frame
        """

        start_date_mask = self.dataframe['datetime'] >= self.start_date
        if self.end_date is None:
            return self.dataframe[start_date_mask]
        else:
            return self.dataframe[
                start_date_mask & (self.dataframe['datetime'] <= self.__file_end_date)
            ]

    @property
    def atcf(self) -> open:
        configuration = {
            'storm_id': self.storm_id,
            'file_deck': self.file_deck,
            'mode': self.mode,
            'filename': self.filename,
        }

        if (
            self.storm_id is not None
            and self.__atcf is None
            or configuration != self.__previous_configuration
        ):
            self.__atcf = get_atcf_file(self.storm_id, self.file_deck, self.mode)

        return self.__atcf

    @property
    def dataframe(self):
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
                dataframe = read_atcf(configuration['filename'])
            else:
                # https://www.nrlmry.navy.mil/atcf_web/docs/database/new/abdeck.txt

                columns = [
                    'basin',
                    'storm_number',
                    'datetime',
                    'record_type',
                    'latitude',
                    'longitude',
                    'max_sustained_wind_speed',
                    'central_pressure',
                    'development_level',
                    'isotach',
                    'quadrant',
                    'radius_for_NEQ',
                    'radius_for_SEQ',
                    'radius_for_SWQ',
                    'radius_for_NWQ',
                    'background_pressure',
                    'radius_of_last_closed_isobar',
                    'radius_of_maximum_winds',
                    'name',
                    'direction',
                    'speed',
                ]

                atcf = self.atcf
                if isinstance(atcf, io.BytesIO):
                    # test if Gzip file
                    atcf.seek(0)  # rewind
                    first_two_bytes = atcf.read(2)
                    atcf.seek(0)  # rewind
                    if first_two_bytes == b'\x1f\x8b':
                        atcf = gzip.GzipFile(fileobj=atcf)
                    elif len(first_two_bytes) == 0:
                        raise ValueError('empty file')

                start_date = self.start_date
                # Only accept request record type or
                # BEST track or OFCL (official) advisory by default
                allowed_record_types = self.record_type
                if allowed_record_types is None:
                    allowed_record_types = ['BEST', 'OFCL']
                records = []

                for line_index, line in enumerate(atcf):
                    line = line.decode('UTF-8').split(',')

                    record = {
                        'basin': line[0],
                        'storm_number': line[1].strip(' '),
                    }

                    record['record_type'] = line[4].strip(' ')

                    if record['record_type'] not in allowed_record_types:
                        continue

                    # computing the actual datetime based on record_type
                    if record['record_type'] == 'BEST':
                        # Add minutes line to base datetime
                        minutes = line[3].strip(' ')
                        if minutes == "":
                            minutes = '00'
                        record['datetime'] = parse_date(line[2].strip(' ') + minutes)
                    else:
                        # Add validation time to base datetime
                        minutes = '00'
                        record['datetime'] = parse_date(line[2].strip(' ') + minutes)
                        if start_date is not None:
                            # Only keep records where base date == start time for advisories
                            if start_date != record['datetime']:
                                continue
                        validation_time = int(line[5].strip(' '))
                        record['datetime'] = record['datetime'] + timedelta(
                            hours=validation_time
                        )

                    latitude = line[6]
                    if 'N' in latitude:
                        latitude = float(latitude.strip('N '))
                    elif 'S' in latitude:
                        latitude = float(latitude.strip('S ')) * -1
                    latitude *= 0.1
                    record['latitude'] = latitude

                    longitude = line[7]
                    if 'E' in longitude:
                        longitude = float(longitude.strip('E ')) * 0.1
                    elif 'W' in longitude:
                        longitude = float(longitude.strip('W ')) * -0.1
                    record['longitude'] = longitude

                    record.update(
                        {
                            'max_sustained_wind_speed': float(line[8].strip(' ')),
                            'central_pressure': float(line[9].strip(' ')),
                            'development_level': line[10].strip(' '),
                        }
                    )

                    try:
                        record['isotach'] = int(line[11].strip(' '))
                    except ValueError:
                        raise Exception(
                            'Error: No radial wind information for this storm; '
                            'parametric wind model cannot be built.'
                        )

                    record.update(
                        {
                            'quadrant': line[12].strip(' '),
                            'radius_for_NEQ': int(line[13].strip(' ')),
                            'radius_for_SEQ': int(line[14].strip(' ')),
                            'radius_for_SWQ': int(line[15].strip(' ')),
                            'radius_for_NWQ': int(line[16].strip(' ')),
                        }
                    )

                    if len(line) > 18:
                        record.update(
                            {
                                'background_pressure': int(line[17].strip(' ')),
                                'radius_of_last_closed_isobar': int(line[18].strip(' ')),
                                'radius_of_maximum_winds': int(line[19].strip(' ')),
                            }
                        )

                        if len(line) > 23:
                            storm_name = line[27].strip()
                        else:
                            storm_name = ''

                        record['name'] = storm_name
                    else:
                        previous_record = records[-1]

                        record.update(
                            {
                                'background_pressure': previous_record['background_pressure'],
                                'radius_of_last_closed_isobar': previous_record[
                                    'radius_of_last_closed_isobar'
                                ],
                                'radius_of_maximum_winds': previous_record[
                                    'radius_of_maximum_winds'
                                ],
                                'name': previous_record['name'],
                            }
                        )

                    for key, value in record.items():
                        if isinstance(value, str) and r'\n' in value:
                            record[key] = value.replace(r'\n', '')

                    records.append(record)

                if len(records) == 0:
                    raise ValueError(f'no records found with type(s) "{allowed_record_types}"')

                dataframe = DataFrame.from_records(data=records, columns=columns)

            self.__dataframe = dataframe
            self.__previous_configuration = configuration

        # if location values have changed, recompute velocity
        location_hash = pandas.util.hash_pandas_object(
            self.__dataframe[['longitude', 'latitude']]
        ).sum()
        if self.__location_hash is None or location_hash != self.__location_hash:
            self.__dataframe = self.__compute_velocity(self.__dataframe)
            self.__location_hash = location_hash

        return self.__dataframe

    @dataframe.setter
    def dataframe(self, dataframe: DataFrame):
        self.__dataframe = dataframe

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
    def record_numbers(self) -> numpy.ndarray:
        record_numbers = numpy.empty((len(self.data)), dtype=int)
        for index, record_datetime in enumerate(self.data['datetime'].unique()):
            record_numbers[self.data['datetime'] == record_datetime] = index + 1
        return record_numbers

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
        return numpy.all(self.dataframe == other.dataframe)

    @staticmethod
    def __compute_velocity(data: DataFrame) -> DataFrame:
        geodetic = Geod(ellps='WGS84')

        unique_datetimes = numpy.unique(data['datetime'])
        for datetime_index, unique_datetime in enumerate(unique_datetimes):
            unique_datetime_indices = numpy.where(
                numpy.asarray(data['datetime']) == unique_datetime
            )[0]
            for unique_datetime_index in unique_datetime_indices:
                if unique_datetime_indices[-1] + 1 < len(data['datetime']):
                    dt = (
                        data['datetime'].iloc[unique_datetime_indices[-1] + 1]
                        - data['datetime'].iloc[unique_datetime_index]
                    )
                    forward_azimuth, inverse_azimuth, distance = geodetic.inv(
                        data['longitude'].iloc[unique_datetime_indices[-1] + 1],
                        data['latitude'].iloc[unique_datetime_indices[-1] + 1],
                        data['longitude'].iloc[unique_datetime_index],
                        data['latitude'].iloc[unique_datetime_index],
                    )
                else:
                    dt = (
                        data['datetime'].iloc[unique_datetime_index]
                        - data['datetime'].iloc[unique_datetime_indices[0] - 1]
                    )
                    forward_azimuth, inverse_azimuth, distance = geodetic.inv(
                        data['longitude'].iloc[unique_datetime_indices[0] - 1],
                        data['latitude'].iloc[unique_datetime_indices[0] - 1],
                        data['longitude'].iloc[unique_datetime_index],
                        data['latitude'].iloc[unique_datetime_index],
                    )

                speed = distance / (dt / timedelta(seconds=1))
                bearing = inverse_azimuth % 360

                data['speed'].iloc[unique_datetime_index] = speed
                data['direction'].iloc[unique_datetime_index] = bearing

                data['speed'] = data['speed'].astype('float', copy=False)
                data['direction'] = data['direction'].astype('float', copy=False)

        # Output has units of meters per second.
        return data

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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.storm_id}')"


def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """

    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    msg = '%s, Retrying in %d seconds...' % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    # else:
                    #     print(msg)
                    sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


def get_atcf_file(
    storm_id: str, file_deck: ATCF_FileDeck = None, mode: ATCF_Mode = None
) -> io.BytesIO:
    url = atcf_url(file_deck=file_deck, storm_id=storm_id, mode=mode).replace('ftp://', "")
    LOGGER.info(f'Downloading storm data from {url}')

    hostname, filename = url.split('/', 1)

    handle = io.BytesIO()

    try:
        ftp = ftplib.FTP(hostname, 'anonymous', "")
        ftp.encoding = 'utf-8'
        ftp.retrbinary(f'RETR {filename}', handle.write)
    except socket.gaierror:
        raise ConnectionError(f'cannot connect to {hostname}')

    return handle


def read_atcf(track: PathLike) -> DataFrame:
    try:
        if not isinstance(track, TextIO):
            track = open(track)
        track = track.readlines()
    except FileNotFoundError:
        # check if the entire track file was passed as a string
        track = str(track).splitlines()
        if len(track) == 1:
            raise

    data = {
        'basin': [],
        'storm_number': [],
        'datetime': [],
        'record_type': [],
        'latitude': [],
        'longitude': [],
        'max_sustained_wind_speed': [],
        'central_pressure': [],
        'development_level': [],
        'isotach': [],
        'quadrant': [],
        'radius_for_NEQ': [],
        'radius_for_SEQ': [],
        'radius_for_SWQ': [],
        'radius_for_NWQ': [],
        'background_pressure': [],
        'radius_of_last_closed_isobar': [],
        'radius_of_maximum_winds': [],
        'name': [],
        'direction': [],
        'speed': [],
    }

    for index, row in enumerate(track):
        row = [value.strip() for value in row.split(',')]

        if len(row) >= 27:
            row_data = {key: None for key in data}

            row_data['basin'] = row[0]
            row_data['storm_number'] = row[1]
            row_data['datetime'] = datetime.strptime(row[2], '%Y%m%d%H')
            row_data['record_type'] = row[4]

            latitude = row[6]
            if 'N' in latitude:
                latitude = float(latitude[:-1]) * 0.1
            elif 'S' in latitude:
                latitude = float(latitude[:-1]) * -0.1
            row_data['latitude'] = latitude

            longitude = row[7]
            if 'E' in longitude:
                longitude = float(longitude[:-1]) * 0.1
            elif 'W' in longitude:
                longitude = float(longitude[:-1]) * -0.1
            row_data['longitude'] = longitude

            row_data['max_sustained_wind_speed'] = normalize_atcf_value(
                row[8], to_type=int, round_digits=0,
            )
            row_data['central_pressure'] = normalize_atcf_value(
                row[9], to_type=int, round_digits=0
            )
            row_data['development_level'] = row[10]
            row_data['isotach'] = normalize_atcf_value(row[11], to_type=int, round_digits=0)
            row_data['quadrant'] = row[12]
            row_data['radius_for_NEQ'] = normalize_atcf_value(
                row[13], to_type=int, round_digits=0
            )
            row_data['radius_for_SEQ'] = normalize_atcf_value(
                row[14], to_type=int, round_digits=0
            )
            row_data['radius_for_SWQ'] = normalize_atcf_value(
                row[15], to_type=int, round_digits=0
            )
            row_data['radius_for_NWQ'] = normalize_atcf_value(
                row[16], to_type=int, round_digits=0
            )
            row_data['background_pressure'] = normalize_atcf_value(
                row[17], to_type=int, round_digits=0
            )
            row_data['radius_of_last_closed_isobar'] = normalize_atcf_value(
                row[18], to_type=int, round_digits=0,
            )
            row_data['radius_of_maximum_winds'] = normalize_atcf_value(
                row[19], to_type=int, round_digits=0,
            )
            row_data['direction'] = normalize_atcf_value(row[25], to_type=int)
            row_data['speed'] = normalize_atcf_value(row[26], to_type=int)
            row_data['name'] = row[27]

            for key, value in row_data.items():
                if isinstance(data[key], Collection):
                    data[key].append(value)
                elif data[key] is None:
                    data[key] = value

    return DataFrame(data=data)
