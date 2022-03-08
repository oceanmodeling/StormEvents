from datetime import datetime
from enum import Enum
from functools import lru_cache
from os import PathLike
import re
from typing import Any, Dict, List

import geopandas
from geopandas import GeoDataFrame
import pandas
from pandas import DataFrame
import requests
import typepigeon
from typepigeon import convert_value

from stormevents.nhc.storms import nhc_storms


class EventType(Enum):
    """
    https://stn.wim.usgs.gov/STNServices/EventTypes.json
    """

    RIVERINE_FLOOD = 1
    HURRICANE = 2
    DROUGHT = 3
    NOREASTER = 4


class EventStatus(Enum):
    """
    https://stn.wim.usgs.gov/STNServices/EventStatus.json
    """

    ACTIVE = 1
    COMPLETED = 2


class HighWaterMarkType(Enum):
    """
    https://stn.wim.usgs.gov/STNServices/HWMTypes.json
    """

    MUD = 1
    DEBRIS = 2
    VEGETATION_LINE = 3
    SEED_LINE = 4
    STAIN_LINE = 5
    MELTED_SNOW_LINE = 6
    DIRECT_OBSERVATION = 7
    OTHER = 8


class HighWaterMarkQuality(Enum):
    """
    https://stn.wim.usgs.gov/STNServices/HWMQualities.json
    """

    EXCELLENT = 1  # +/- 0.05 ft
    GOOD = 2  # +/- 0.10 ft
    FAIR = 3  # +/- 0.20 ft
    POOR = 4  # +/- 0.40 ft
    VERY_POOR = 5  # +/- > 0.40 ft
    UNKNOWN = 6  # Unknown / Historical


class HighWaterMarkEnvironment(Enum):
    COASTAL = 'Coastal'
    RIVERINE = 'Riverine'


class FloodEventHighWaterMarks:
    """
    representation of high-water mark (HWM) surveys for an arbitrary flood event
    """

    URL = 'https://stn.wim.usgs.gov/STNServices/HWMs/FilteredHWMs.json'

    def __init__(self, id: int):
        """
        :param id: USGS event ID

        >>> survey = FloodEventHighWaterMarks(182)
        >>> survey.data()
                 latitude  longitude            eventName hwmTypeName  ...   hwm_label files siteZone                    geometry
        hwm_id                                                         ...
        22636   32.007730 -81.238270  Irma September 2017   Seed line  ...        HWM1    []      NaN  POINT (-81.23827 32.00773)
        22757   30.510528 -81.460833  Irma September 2017      Debris  ...       HWM 1    []        0  POINT (-81.46083 30.51053)
        22885   30.770560 -81.581390  Irma September 2017   Seed line  ...  GACAM17842    []      NaN  POINT (-81.58139 30.77056)
        22965   31.063150 -81.404540  Irma September 2017      Debris  ...         HWM    []      NaN  POINT (-81.40454 31.06315)
        23052   30.845000 -81.560000  Irma September 2017      Debris  ...  GACAM17840    []      NaN  POINT (-81.56000 30.84500)
        ...           ...        ...                  ...         ...  ...         ...   ...      ...                         ...
        25147   30.018190 -81.859657  Irma September 2017         Mud  ...       HWM01    []      NaN  POINT (-81.85966 30.01819)
        25148   30.097214 -81.891451  Irma September 2017   Seed line  ...      hwm 01    []      NaN  POINT (-81.89145 30.09721)
        25150   30.038222 -81.880928  Irma September 2017   Seed line  ...       HWM01    []      NaN  POINT (-81.88093 30.03822)
        25158   29.720560 -81.506110  Irma September 2017   Seed line  ...         HWM    []      NaN  POINT (-81.50611 29.72056)
        25159   30.097514 -81.794375  Irma September 2017   Seed line  ...       HWM 1    []      NaN  POINT (-81.79438 30.09751)
        [221 rows x 52 columns]
        >>> survey.data(hwm_quality=['EXCELLENT', 'GOOD'])
                 latitude  longitude            eventName hwmTypeName  ...   hwm_label files siteZone                    geometry
        hwm_id                                                         ...
        22636   32.007730 -81.238270  Irma September 2017   Seed line  ...        HWM1    []      NaN  POINT (-81.23827 32.00773)
        22885   30.770560 -81.581390  Irma September 2017   Seed line  ...  GACAM17842    []      NaN  POINT (-81.58139 30.77056)
        23130   31.034720 -81.640000  Irma September 2017   Seed line  ...        HWM1    []      NaN  POINT (-81.64000 31.03472)
        23216   32.035150 -81.045040  Irma September 2017   Seed line  ...        HWM1    []      NaN  POINT (-81.04504 32.03515)
        23236   32.083650 -81.157520  Irma September 2017   Seed line  ...        HWM1    []      NaN  POINT (-81.15752 32.08365)
        ...           ...        ...                  ...         ...  ...         ...   ...      ...                         ...
        25146   29.992580 -81.851518  Irma September 2017   Seed line  ...      HWM 01    []      NaN  POINT (-81.85152 29.99258)
        25148   30.097214 -81.891451  Irma September 2017   Seed line  ...      hwm 01    []      NaN  POINT (-81.89145 30.09721)
        25150   30.038222 -81.880928  Irma September 2017   Seed line  ...       HWM01    []      NaN  POINT (-81.88093 30.03822)
        25158   29.720560 -81.506110  Irma September 2017   Seed line  ...         HWM    []      NaN  POINT (-81.50611 29.72056)
        25159   30.097514 -81.794375  Irma September 2017   Seed line  ...       HWM 1    []      NaN  POINT (-81.79438 30.09751)
        [138 rows x 52 columns]
        """

        self.id = id

        self.__query = None
        self.__data = None
        self.__error = None

    @classmethod
    def from_name(cls, name: str, year: int = None,) -> 'FloodEventHighWaterMarks':
        """
        retrieve high-water mark info from the USGS flood event name

        :param name: USGS flood event name
        :param year: year of flood event
        :return: high-water marks object
        """

        events = usgs_highwatermark_events(year=year)
        events = events[events['name'] == name]

        if len(events) == 0:
            raise ValueError(f'no event with name "{name}" found')

        if year is not None:
            events = events[events['year'] == year]

        event = events.iloc[0]

        return cls(id=event.name)

    @classmethod
    def from_csv(cls, filename: PathLike, id: int) -> 'FloodEventHighWaterMarks':
        """
        read a CSV file with high-water mark data

        :param filename: file path to CSV
        :param id: USGS flood event ID
        :return: high-water marks object
        """

        data = pandas.read_csv(filename, index_col='hwm_id')
        try:
            instance = cls(id=int(id))
        except:
            instance = cls.from_name(id)
        instance.__data = data
        return instance

    @property
    def id(self) -> int:
        return self.__id

    @id.setter
    def id(self, id: int):
        self.__metadata = usgs_highwatermark_events().loc[id]
        self.__id = self.__metadata.name

    @property
    def name(self) -> str:
        return self.__metadata['name']

    @property
    def year(self) -> int:
        return self.__metadata['year']

    @property
    def description(self) -> str:
        return self.__metadata['description']

    @property
    def event_type(self) -> EventType:
        return typepigeon.convert_value(self.__metadata['event_type'], EventType)

    @property
    def event_status(self) -> EventStatus:
        return typepigeon.convert_value(self.__metadata['event_status'], EventStatus)

    @property
    def coordinator(self) -> str:
        return self.__metadata['coordinator']

    @property
    def instruments(self) -> str:
        return self.__metadata['instruments']

    @property
    def last_updated(self) -> datetime:
        return self.__metadata['last_updated']

    @property
    def last_updated_by(self) -> str:
        return self.__metadata['last_updated_by']

    @property
    def start_date(self) -> datetime:
        return typepigeon.convert_value(self.__metadata['start_date'], datetime)

    @property
    def end_date(self) -> datetime:
        return typepigeon.convert_value(self.__metadata['end_date'], datetime)

    def data(
        self,
        us_states: List[str] = None,
        us_counties: List[str] = None,
        hwm_type: HighWaterMarkType = None,
        hwm_quality: HighWaterMarkQuality = None,
        hwm_environment: HighWaterMarkEnvironment = None,
        survey_completed: bool = None,
        still_water: bool = None,
    ) -> GeoDataFrame:
        """
        :returns: data frame of data for the current parameters

        >>> survey = FloodEventHighWaterMarks(23)
        >>> survey.data()
                 latitude  longitude eventName                      hwmTypeName  ... approval_id hwm_uncertainty uncertainty                    geometry
        hwm_id                                                                   ...
        14699   38.917360 -75.947890     Irene                           Debris  ...         NaN             NaN         NaN  POINT (-75.94789 38.91736)
        14700   38.917360 -75.947890     Irene                              Mud  ...         NaN             NaN         NaN  POINT (-75.94789 38.91736)
        14701   38.917580 -75.948470     Irene                              Mud  ...         NaN             NaN         NaN  POINT (-75.94847 38.91758)
        14702   38.917360 -75.946060     Irene                       Stain line  ...         NaN             NaN         NaN  POINT (-75.94606 38.91736)
        14703   38.917580 -75.945970     Irene                              Mud  ...         NaN             NaN         NaN  POINT (-75.94597 38.91758)
        ...           ...        ...       ...                              ...  ...         ...             ...         ...                         ...
        41666   44.184900 -72.823970     Irene  Other (Note in Description box)  ...     24707.0             NaN         NaN  POINT (-72.82397 44.18490)
        41667   43.616332 -72.658893     Irene                      Clear water  ...     24706.0             NaN         NaN  POINT (-72.65889 43.61633)
        41668   43.617370 -72.667530     Irene                        Seed line  ...     24705.0             NaN         NaN  POINT (-72.66753 43.61737)
        41670   43.524600 -72.677540     Irene                        Seed line  ...         NaN             NaN         NaN  POINT (-72.67754 43.52460)
        41671   43.534470 -72.672750     Irene                        Seed line  ...         NaN             NaN         NaN  POINT (-72.67275 43.53447)
        [1300 rows x 51 columns]
        """

        if self.__query is None:
            self.__query = HighWaterMarksQuery(
                event_id=self.id,
                event_type=self.event_type,
                event_status=self.event_status,
                us_states=us_states,
                us_counties=us_counties,
                hwm_type=hwm_type,
                hwm_quality=hwm_quality,
                hwm_environment=hwm_environment,
                survey_completed=survey_completed,
                still_water=still_water,
            )
        else:
            if us_states is not None:
                self.__query.us_states = us_states
            if us_counties is not None:
                self.__query.us_counties = us_counties
            if hwm_type is not None:
                self.__query.hwm_type = hwm_type
            if hwm_quality is not None:
                self.__query.hwm_quality = hwm_quality
            if hwm_environment is not None:
                self.__query.hwm_environment = hwm_environment
            if survey_completed is not None:
                self.__query.survey_completed = survey_completed
            if still_water is not None:
                self.__query.still_water = still_water

        return self.__query.data

    def __eq__(self, other: 'FloodEventHighWaterMarks') -> bool:
        return (
            self.__query is not None
            and other.__query is not None
            and self.__query == other.__query
        )

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(event_id={repr(self.id)})'


class StormHighWaterMarks(FloodEventHighWaterMarks):
    """
    representation of high-water mark (HWM) surveys for a named storm event
    """

    def __init__(self, name: str, year: int):
        """
        :param name: storm name
        :param year: storm year
        """

        storms = usgs_highwatermark_storms(year=year)
        storm = storms[(storms['nhc_name'] == name.upper().strip()) & (storms['year'] == year)]

        if len(storm) == 0:
            raise ValueError(f'storm "{name} {year}" not found in USGS HWM database')

        super().__init__(id=storm.index[0])


class HighWaterMarksQuery:
    """
    abstraction of an individual query to the USGS Short-Term Network API for high-water marks (HWMs)
    https://stn.wim.usgs.gov/STNServices/Documentation/home
    """

    URL = 'https://stn.wim.usgs.gov/STNServices/HWMs/FilteredHWMs.json'

    def __init__(
        self,
        event_id: int = None,
        event_type: EventType = None,
        event_status: EventStatus = None,
        us_states: List[str] = None,
        us_counties: List[str] = None,
        hwm_type: HighWaterMarkType = None,
        hwm_quality: HighWaterMarkQuality = None,
        hwm_environment: HighWaterMarkEnvironment = None,
        survey_completed: bool = None,
        still_water: bool = None,
    ):
        """
        :param event_id: USGS event ID
        :param event_type: type of flood event
        :param event_status: whether flood event had completed
        :param us_states: U.S. states in which to query
        :param us_counties: U.S. counties in which to query
        :param hwm_type: HWM type filter
        :param hwm_quality: HWM quality filter
        :param hwm_environment: HWM environment filter
        :param survey_completed: whether HWM survey should be complete
        :param still_water: HWM still water filter

        >>> query = HighWaterMarksQuery(182)
        >>> query.data
                 latitude  longitude            eventName hwmTypeName  ...   hwm_label files siteZone                    geometry
        hwm_id                                                         ...
        22636   32.007730 -81.238270  Irma September 2017   Seed line  ...        HWM1    []      NaN  POINT (-81.23827 32.00773)
        22757   30.510528 -81.460833  Irma September 2017      Debris  ...       HWM 1    []        0  POINT (-81.46083 30.51053)
        22885   30.770560 -81.581390  Irma September 2017   Seed line  ...  GACAM17842    []      NaN  POINT (-81.58139 30.77056)
        22965   31.063150 -81.404540  Irma September 2017      Debris  ...         HWM    []      NaN  POINT (-81.40454 31.06315)
        23052   30.845000 -81.560000  Irma September 2017      Debris  ...  GACAM17840    []      NaN  POINT (-81.56000 30.84500)
        ...           ...        ...                  ...         ...  ...         ...   ...      ...                         ...
        25147   30.018190 -81.859657  Irma September 2017         Mud  ...       HWM01    []      NaN  POINT (-81.85966 30.01819)
        25148   30.097214 -81.891451  Irma September 2017   Seed line  ...      hwm 01    []      NaN  POINT (-81.89145 30.09721)
        25150   30.038222 -81.880928  Irma September 2017   Seed line  ...       HWM01    []      NaN  POINT (-81.88093 30.03822)
        25158   29.720560 -81.506110  Irma September 2017   Seed line  ...         HWM    []      NaN  POINT (-81.50611 29.72056)
        25159   30.097514 -81.794375  Irma September 2017   Seed line  ...       HWM 1    []      NaN  POINT (-81.79438 30.09751)
        [221 rows x 52 columns]
        >>> query.hwm_quality = 'EXCELLENT', 'GOOD'
        >>> query.data
                 latitude  longitude            eventName hwmTypeName  ...   hwm_label files siteZone                    geometry
        hwm_id                                                         ...
        22636   32.007730 -81.238270  Irma September 2017   Seed line  ...        HWM1    []      NaN  POINT (-81.23827 32.00773)
        22885   30.770560 -81.581390  Irma September 2017   Seed line  ...  GACAM17842    []      NaN  POINT (-81.58139 30.77056)
        23130   31.034720 -81.640000  Irma September 2017   Seed line  ...        HWM1    []      NaN  POINT (-81.64000 31.03472)
        23216   32.035150 -81.045040  Irma September 2017   Seed line  ...        HWM1    []      NaN  POINT (-81.04504 32.03515)
        23236   32.083650 -81.157520  Irma September 2017   Seed line  ...        HWM1    []      NaN  POINT (-81.15752 32.08365)
        ...           ...        ...                  ...         ...  ...         ...   ...      ...                         ...
        25146   29.992580 -81.851518  Irma September 2017   Seed line  ...      HWM 01    []      NaN  POINT (-81.85152 29.99258)
        25148   30.097214 -81.891451  Irma September 2017   Seed line  ...      hwm 01    []      NaN  POINT (-81.89145 30.09721)
        25150   30.038222 -81.880928  Irma September 2017   Seed line  ...       HWM01    []      NaN  POINT (-81.88093 30.03822)
        25158   29.720560 -81.506110  Irma September 2017   Seed line  ...         HWM    []      NaN  POINT (-81.50611 29.72056)
        25159   30.097514 -81.794375  Irma September 2017   Seed line  ...       HWM 1    []      NaN  POINT (-81.79438 30.09751)
        [138 rows x 52 columns]
        """

        self.event_id = event_id
        self.event_type = event_type
        self.event_status = event_status
        self.us_states = us_states
        self.us_counties = us_counties
        self.hwm_type = hwm_type
        self.hwm_quality = hwm_quality
        self.hwm_environment = hwm_environment
        self.survey_completed = survey_completed
        self.still_water = still_water

        self.__previous_query = self.query
        self.__data = None
        self.__error = None

    @property
    def us_states(self) -> List[str]:
        return self.__us_states

    @us_states.setter
    def us_states(self, us_states: List[str]):
        self.__us_states = typepigeon.convert_value(us_states, [str])

    @property
    def us_counties(self) -> List[str]:
        return self.__us_counties

    @us_counties.setter
    def us_counties(self, us_counties: List[str]):
        self.__us_counties = typepigeon.convert_value(us_counties, [str])

    @property
    def hwm_quality(self) -> List[HighWaterMarkQuality]:
        return self.__hwm_quality

    @hwm_quality.setter
    def hwm_quality(self, hwm_quality: HighWaterMarkQuality):
        if hwm_quality is not None:
            self.__hwm_quality = convert_value(hwm_quality, [HighWaterMarkQuality])
        else:
            self.__hwm_quality = None

    @property
    def hwm_type(self) -> List[HighWaterMarkType]:
        return self.__hwm_type

    @hwm_type.setter
    def hwm_type(self, hwm_type: HighWaterMarkType):
        if hwm_type is not None:
            self.__hwm_type = convert_value(hwm_type, [HighWaterMarkType])
        else:
            self.__hwm_type = None

    @property
    def hwm_environment(self) -> List[HighWaterMarkEnvironment]:
        return self.__hwm_environment

    @hwm_environment.setter
    def hwm_environment(self, hwm_environment: HighWaterMarkEnvironment):
        if hwm_environment is not None:
            self.__hwm_environment = convert_value(hwm_environment, [HighWaterMarkEnvironment])
        else:
            self.__hwm_environment = None

    @property
    def query(self) -> Dict[str, Any]:
        query = {
            'Event': self.event_id,
            'EventType': self.event_type,
            'EventStatus': self.event_status,
            'States': self.us_states,
            'County': self.us_counties,
            'HWMType': self.hwm_type,
            'HWMQuality': self.hwm_quality,
            'HWMEnvironment': self.hwm_environment,
            'SurveyComplete': self.survey_completed,
            'StillWater': self.still_water,
        }

        for key, value in query.items():
            if key not in ['SurveyComplete', 'StillWater']:
                if isinstance(value, Enum):
                    value = value.value
                elif isinstance(value, List):
                    value = [
                        entry.value if isinstance(entry, Enum) else entry for entry in value
                    ]
                    value = typepigeon.convert_value(value, [str])

                    if len(value) > 0:
                        value = ','.join(value)
                    else:
                        value = None

            query[key] = value

        return query

    @property
    def data(self) -> GeoDataFrame:
        """
        :returns: data frame of data for the current parameters

        >>> query = HighWaterMarksQuery(23)
        >>> query.data
                 latitude  longitude eventName                      hwmTypeName  ... approval_id hwm_uncertainty uncertainty                    geometry
        hwm_id                                                                   ...
        14699   38.917360 -75.947890     Irene                           Debris  ...         NaN             NaN         NaN  POINT (-75.94789 38.91736)
        14700   38.917360 -75.947890     Irene                              Mud  ...         NaN             NaN         NaN  POINT (-75.94789 38.91736)
        14701   38.917580 -75.948470     Irene                              Mud  ...         NaN             NaN         NaN  POINT (-75.94847 38.91758)
        14702   38.917360 -75.946060     Irene                       Stain line  ...         NaN             NaN         NaN  POINT (-75.94606 38.91736)
        14703   38.917580 -75.945970     Irene                              Mud  ...         NaN             NaN         NaN  POINT (-75.94597 38.91758)
        ...           ...        ...       ...                              ...  ...         ...             ...         ...                         ...
        41666   44.184900 -72.823970     Irene  Other (Note in Description box)  ...     24707.0             NaN         NaN  POINT (-72.82397 44.18490)
        41667   43.616332 -72.658893     Irene                      Clear water  ...     24706.0             NaN         NaN  POINT (-72.65889 43.61633)
        41668   43.617370 -72.667530     Irene                        Seed line  ...     24705.0             NaN         NaN  POINT (-72.66753 43.61737)
        41670   43.524600 -72.677540     Irene                        Seed line  ...         NaN             NaN         NaN  POINT (-72.67754 43.52460)
        41671   43.534470 -72.672750     Irene                        Seed line  ...         NaN             NaN         NaN  POINT (-72.67275 43.53447)
        [1300 rows x 51 columns]
        """

        if self.__data is None or self.__previous_query != self.query:
            query = self.query

            if any(
                value is not None
                for key, value in query.items()
                if key not in ['SurveyComplete', 'StillWater']
            ):
                url = self.URL
            else:
                url = 'https://stn.wim.usgs.gov/STNServices/HWMs.json'

            response = requests.get(url, params=query)

            if response.status_code == 200:
                data = DataFrame(response.json())
                self.__error = None
            else:
                self.__error = f'{response.reason} - {response.request.url}'
                raise ValueError(self.__error)

            if len(data) > 0:
                data['survey_date'] = pandas.to_datetime(data['survey_date'], errors='coerce')
                data['flag_date'] = pandas.to_datetime(data['flag_date'], errors='coerce')
                data.loc[data['markerName'].str.len() == 0, 'markerName'] = None
            else:
                data = DataFrame(
                    columns=[
                        'latitude',
                        'longitude',
                        'eventName',
                        'hwmTypeName',
                        'hwmQualityName',
                        'verticalDatumName',
                        'verticalMethodName',
                        'approvalMember',
                        'markerName',
                        'horizontalMethodName',
                        'horizontalDatumName',
                        'flagMemberName',
                        'surveyMemberName',
                        'site_no',
                        'siteDescription',
                        'sitePriorityName',
                        'networkNames',
                        'stateName',
                        'countyName',
                        'siteZone',
                        'sitePermHousing',
                        'site_latitude',
                        'site_longitude',
                        'hwm_id',
                        'waterbody',
                        'site_id',
                        'event_id',
                        'hwm_type_id',
                        'hwm_quality_id',
                        'latitude_dd',
                        'longitude_dd',
                        'survey_date',
                        'elev_ft',
                        'vdatum_id',
                        'vcollect_method_id',
                        'bank',
                        'marker_id',
                        'hcollect_method_id',
                        'hwm_notes',
                        'hwm_environment',
                        'flag_date',
                        'stillwater',
                        'hdatum_id',
                        'hwm_label',
                        'files',
                        'height_above_gnd',
                        'hwm_locationdescription',
                        'flag_member_id',
                        'survey_member_id',
                    ],
                )
            data.set_index('hwm_id', inplace=True)
            self.__data = GeoDataFrame(
                data, geometry=geopandas.points_from_xy(data['longitude'], data['latitude']),
            )
            self.__previous_query = query
        elif self.__error is not None:
            raise ValueError(self.__error)

        return self.__data

    def __eq__(self, other: 'HighWaterMarksQuery') -> bool:
        return self.query == other.query

    def __repr__(self) -> str:
        return (
            f'{self.__class__.__name__}('
            f'event_id={self.event_id}, '
            f'event_type={self.event_type}, '
            f'event_status={self.event_status}, '
            f'us_states={self.us_states}, '
            f'us_counties={self.us_counties}, '
            f'hwm_type={self.hwm_type}, '
            f'hwm_quality={self.hwm_quality}, '
            f'hwm_environment={self.hwm_environment}, '
            f'survey_completed={self.survey_completed}, '
            f'still_water={self.still_water}'
            f')'
        )


@lru_cache(maxsize=None)
def usgs_highwatermark_events(
    year: int = None, event_type: EventType = None, event_status: EventStatus = None,
) -> DataFrame:
    """
    this function collects all USGS flood events of the given type and status that have high-water mark data

    https://stn.wim.usgs.gov/STNServices/Events.json

    USGS does not standardize event naming, and they should.
    Year, month, and storm type are not always included.
    The order in which the names are in the response is also not standardized.
    This function applies a workaround to fill in gaps in data.
    USGS should standardize their REST server data.

    :param event_type: type of USGS flood event
    :param year: year of event
    :param event_status: status of USGS flood event
    :return: table of flood events


    >>> usgs_highwatermark_events()
                                                name  year  ...          start_date            end_date
    usgs_id                                                 ...
    7                             FEMA 2013 exercise  2013  ... 2013-05-15 04:00:00 2013-05-23 04:00:00
    8                                          Wilma  2005  ... 2005-10-20 00:00:00 2005-10-31 00:00:00
    9                            Midwest Floods 2011  2011  ... 2011-02-01 06:00:00 2011-08-30 05:00:00
    10                          2013 - June PA Flood  2013  ... 2013-06-23 00:00:00 2013-07-01 00:00:00
    11               Colorado 2013 Front Range Flood  2013  ... 2013-09-12 05:00:00 2013-09-24 05:00:00
    ...                                          ...   ...  ...                 ...                 ...
    311                   2021 August Flash Flood TN  2021  ... 2021-08-21 05:00:00 2021-08-22 05:00:00
    312                    2021 Tropical Cyclone Ida  2021  ... 2021-08-27 05:00:00 2021-09-03 05:00:00
    313                Chesapeake Bay - October 2021  2021  ... 2021-10-28 04:00:00                 NaT
    314      2021 November Flooding Washington State  2021  ... 2021-11-08 06:00:00 2021-11-19 06:00:00
    315          Washington Coastal Winter 2021-2022  2021  ... 2021-11-01 05:00:00 2022-06-30 05:00:00
    [292 rows x 11 columns]
    """

    events = pandas.read_json('https://stn.wim.usgs.gov/STNServices/Events.json')
    events.rename(
        columns={
            'event_id': 'usgs_id',
            'event_name': 'name',
            'event_start_date': 'start_date',
            'event_end_date': 'end_date',
            'event_description': 'description',
            'event_coordinator': 'coordinator',
        },
        inplace=True,
    )
    events.set_index('usgs_id', inplace=True)
    events['start_date'] = pandas.to_datetime(events['start_date'])
    events['end_date'] = pandas.to_datetime(events['end_date'])
    events['last_updated'] = pandas.to_datetime(events['last_updated'])
    events['event_type'] = events['event_type_id'].apply(lambda value: EventType(value).name)
    events['event_status'] = events['event_status_id'].apply(
        lambda value: EventStatus(value).name
    )
    events['year'] = events['start_date'].dt.year
    events = events[
        [
            'name',
            'year',
            'description',
            'event_type',
            'event_status',
            'coordinator',
            'instruments',
            'last_updated',
            'last_updated_by',
            'start_date',
            'end_date',
        ]
    ]

    if event_type is not None:
        event_type = typepigeon.convert_value(event_type, [str])
        events = events[events['event_type'].isin(event_type)]

    if event_status is not None:
        event_status = typepigeon.convert_value(event_status, [str])
        events = events[events['event_status'].isin(event_status)]

    if year is not None:
        year = typepigeon.convert_value(year, [int])
        events = events[events['year'].isin(year)]

    return events


@lru_cache(maxsize=None)
def usgs_highwatermark_storms(year: int = None) -> DataFrame:
    """
    this function collects USGS high-water mark data for storm events and cross-correlates it with NHC storm data

    this is useful if you want to retrieve USGS data for a specific NHC storm code

    :param year: storm year
    :return: table of USGS flood events with NHC storm names

    >>> usgs_highwatermark_storms()
                                                   usgs_name  year  nhc_name  nhc_code
    usgs_id
    8                                                  Wilma  2005     WILMA  AL252005
    18                                        Isaac Aug 2012  2012     ISAAC  AL092012
    19                                                  Rita  2005      RITA  AL182005
    23                                                 Irene  2011     IRENE  AL092011
    24                                                 Sandy  2012     SANDY  AL182012
    25                                                Gustav  2008    GUSTAV  AL072008
    26                                                   Ike  2008       IKE  AL092008
    119                                              Joaquin  2015   JOAQUIN  AL112015
    131                                              Hermine  2016   HERMINE  AL092016
    133                                Isabel September 2003  2003    ISABEL  AL132003
    135                                 Matthew October 2016  2016   MATTHEW  AL142016
    180                                      Harvey Aug 2017  2017    HARVEY  AL092017
    182                                  Irma September 2017  2017      IRMA  AL112017
    189                                 Maria September 2017  2017     MARIA  AL152017
    190                                  Jose September 2017  2017      JOSE  AL122017
    196                                    Nate October 2017  2017      NATE  AL162017
    281                                     Lane August 2018  2018      LANE  EP142018
    282                                      Gordon Sep 2018  2018    GORDON  AL072018
    283                                    Florence Sep 2018  2018  FLORENCE  AL062018
    284                                       Isaac Sep 2018  2018     ISAAC  AL092018
    287                                     Michael Oct 2018  2018   MICHAEL  AL142018
    291                                2019 Hurricane Dorian  2019    DORIAN  AL052019
    299      1995 South Carolina August Tropical Storm Jerry  1995     JERRY  AL111995
    300        1999 South Carolina September Hurricane Floyd  1999     FLOYD  AL081999
    301                                2020 Hurricane Isaias  2020    ISAIAS  AL092020
    303                     2020 TS Marco - Hurricane  Laura  2020     MARCO  AL142020
    304                                 2020 Hurricane Sally  2020     SALLY  AL192020
    305                                 2020 Hurricane Delta  2020     DELTA  AL262020
    310                          2021 Tropical Cyclone Henri  2021     HENRI  AL082021
    312                            2021 Tropical Cyclone Ida  2021       IDA  AL092021
    """

    events = usgs_highwatermark_events(year=year, event_type=EventType.HURRICANE)

    events.rename(columns={'name': 'usgs_name'}, inplace=True)
    events['nhc_name'] = None
    events['nhc_code'] = None

    storms = nhc_storms(tuple(pandas.unique(events['year'])))

    storm_names = pandas.unique(storms['name'].str.strip())
    storm_names.sort()
    for storm_name in storm_names:
        event_storms = events[
            events['usgs_name'].str.contains(storm_name, flags=re.IGNORECASE)
        ]
        for event_id, event in event_storms.iterrows():
            storms_matching = storms[
                storms['name'].str.contains(storm_name, flags=re.IGNORECASE)
                & (storms['year'] == event['year'])
            ]

            for nhc_code, storm in storms_matching.iterrows():
                events.at[event_id, 'nhc_name'] = storm['name']
                events.at[event_id, 'nhc_code'] = storm.name

    return events.loc[
        ~pandas.isna(events['nhc_code']), ['usgs_name', 'year', 'nhc_name', 'nhc_code']
    ]
