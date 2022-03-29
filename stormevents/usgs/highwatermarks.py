from enum import Enum
from typing import Any, Dict, List

import geopandas
from geopandas import GeoDataFrame
import pandas
from pandas import DataFrame
import requests
import typepigeon

from stormevents.usgs.base import EventStatus, EventType


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
        quality: HighWaterMarkQuality = None,
        environment: HighWaterMarkEnvironment = None,
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
        :param quality: HWM quality filter
        :param environment: HWM environment filter
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
        >>> query.quality = 'EXCELLENT', 'GOOD'
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
        self.quality = quality
        self.environment = environment
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
    def hwm_type(self) -> List[HighWaterMarkType]:
        return self.__hwm_type

    @hwm_type.setter
    def hwm_type(self, hwm_type: HighWaterMarkType):
        if hwm_type is not None:
            self.__hwm_type = typepigeon.convert_value(hwm_type, [HighWaterMarkType])
        else:
            self.__hwm_type = None

    @property
    def quality(self) -> List[HighWaterMarkQuality]:
        return self.__quality

    @quality.setter
    def quality(self, quality: HighWaterMarkQuality):
        if quality is not None:
            self.__quality = typepigeon.convert_value(quality, [HighWaterMarkQuality])
        else:
            self.__quality = None

    @property
    def environment(self) -> List[HighWaterMarkEnvironment]:
        return self.__environment

    @environment.setter
    def environment(self, environment: HighWaterMarkEnvironment):
        if environment is not None:
            self.__environment = typepigeon.convert_value(
                environment, [HighWaterMarkEnvironment]
            )
        else:
            self.__environment = None

    @property
    def query(self) -> Dict[str, Any]:
        query = {
            'Event': self.event_id,
            'EventType': self.event_type,
            'EventStatus': self.event_status,
            'States': self.us_states,
            'County': self.us_counties,
            'HWMType': self.hwm_type,
            'HWMQuality': self.quality,
            'HWMEnvironment': self.environment,
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
            f'quality={self.quality}, '
            f'environment={self.environment}, '
            f'survey_completed={self.survey_completed}, '
            f'still_water={self.still_water}'
            f')'
        )
