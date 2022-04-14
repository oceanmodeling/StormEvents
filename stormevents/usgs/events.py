from datetime import datetime
from functools import lru_cache
from os import PathLike
import re
from typing import List

from geopandas import GeoDataFrame
import pandas
from pandas import DataFrame
import typepigeon

from stormevents.nhc import nhc_storms
from stormevents.usgs.base import EventStatus, EventType
from stormevents.usgs.highwatermarks import (
    HighWaterMarkEnvironment,
    HighWaterMarkQuality,
    HighWaterMarksQuery,
    HighWaterMarkType,
)
from stormevents.usgs.sensors import usgs_files, usgs_sensors


@lru_cache(maxsize=None)
def usgs_flood_events(
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


    >>> usgs_flood_events()
                                                name  year                                        description  ... last_updated_by          start_date            end_date
    usgs_id                                                                                                    ...
    7                             FEMA 2013 exercise  2013                   Ardent/Sentry 2013 FEMA Exercise  ...             NaN 2013-05-15 04:00:00 2013-05-23 04:00:00
    8                                          Wilma  2005  Category 3 in west FL.   Hurricane Wilma was t...  ...             NaN 2005-10-20 00:00:00 2005-10-31 00:00:00
    9                            Midwest Floods 2011  2011  Spring and summer 2011 flooding of the Mississ...  ...            35.0 2011-02-01 06:00:00 2011-08-30 05:00:00
    10                          2013 - June PA Flood  2013           Localized summer rain, small scale event  ...             NaN 2013-06-23 00:00:00 2013-07-01 00:00:00
    11               Colorado 2013 Front Range Flood  2013  A large prolonged precipitation event resulted...  ...            35.0 2013-09-12 05:00:00 2013-09-24 05:00:00
    ...                                          ...   ...                                                ...  ...             ...                 ...                 ...
    312                    2021 Tropical Cyclone Ida  2021                                                NaN  ...           864.0 2021-08-27 05:00:00 2021-09-03 05:00:00
    313                Chesapeake Bay - October 2021  2021     Coastal-flooding event in the  Chesapeake Bay.  ...           406.0 2021-10-28 04:00:00                 NaT
    314      2021 November Flooding Washington State  2021                         Atmospheric River Flooding  ...           864.0 2021-11-08 06:00:00 2021-11-19 06:00:00
    315          Washington Coastal Winter 2021-2022  2021                                                NaN  ...           864.0 2021-11-01 05:00:00 2022-06-30 05:00:00
    317        2022 Hunga Tonga-Hunga Haapai tsunami  2022                                                     ...             1.0 2022-01-14 05:00:00 2022-01-18 05:00:00
    [293 rows x 11 columns]
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
def usgs_flood_storms(year: int = None) -> DataFrame:
    """
    this function collects USGS high-water mark data for storm events and cross-correlates it with NHC storm data

    this is useful if you want to retrieve USGS data for a specific NHC storm code

    :param year: storm year
    :return: table of USGS flood events with NHC storm names

    >>> usgs_flood_storms()
                                                   usgs_name  year  nhc_name  ... last_updated_by          start_date            end_date
    usgs_id                                                                   ...
    8                                                  Wilma  2005     WILMA  ...             NaN 2005-10-20 00:00:00 2005-10-31 00:00:00
    18                                        Isaac Aug 2012  2012     ISAAC  ...            35.0 2012-08-27 05:00:00 2012-09-02 05:00:00
    19                                                  Rita  2005      RITA  ...             NaN 2005-09-23 04:00:00 2005-09-25 04:00:00
    23                                                 Irene  2011     IRENE  ...             NaN 2011-08-26 04:00:00 2011-08-29 04:00:00
    24                                                 Sandy  2012     SANDY  ...             NaN 2012-10-21 04:00:00 2012-10-30 04:00:00
    ...                                                  ...   ...       ...  ...             ...                 ...                 ...
    303                     2020 TS Marco - Hurricane  Laura  2020     MARCO  ...           864.0 2020-08-22 05:00:00 2020-08-30 05:00:00
    304                                 2020 Hurricane Sally  2020     SALLY  ...           864.0 2020-09-13 05:00:00 2020-09-20 05:00:00
    305                                 2020 Hurricane Delta  2020     DELTA  ...           864.0 2020-10-06 05:00:00 2020-10-13 05:00:00
    310                          2021 Tropical Cyclone Henri  2021     HENRI  ...           864.0 2021-08-20 05:00:00 2021-09-03 05:00:00
    312                            2021 Tropical Cyclone Ida  2021       IDA  ...           864.0 2021-08-27 05:00:00 2021-09-03 05:00:00
    [30 rows x 13 columns]
    """

    events = usgs_flood_events(year=year, event_type=EventType.HURRICANE)

    events.rename(columns={'name': 'usgs_name'}, inplace=True)
    events['nhc_name'] = None
    events['nhc_code'] = None

    storms = nhc_storms(tuple(pandas.unique(events['year'])))

    storm_names = sorted(pandas.unique(storms['name'].str.strip()))
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
        ~pandas.isna(events['nhc_code']),
        ['usgs_name', 'year', 'nhc_name', 'nhc_code', *events.columns[2:-2],],
    ]


class USGS_Event:
    """
    representation of an arbitrary flood event as defined by the USGS
    """

    URL = 'https://stn.wim.usgs.gov/STNServices/HWMs/FilteredHWMs.json'

    def __init__(self, id: int):
        """
        :param id: USGS event ID

        >>> flood = USGS_Event(182)
        >>> flood.high_water_marks()
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
        >>> flood.high_water_marks(quality=['EXCELLENT', 'GOOD'])
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
    def from_name(cls, name: str, year: int = None,) -> 'USGS_Event':
        """
        retrieve high-water mark info from the USGS flood event name

        :param name: USGS flood event name
        :param year: year of flood event
        :return: flood event object
        """

        events = usgs_flood_events(year=year)
        events = events[events['name'] == name]

        if len(events) == 0:
            raise ValueError(f'no event with name "{name}" found')

        if year is not None:
            events = events[events['year'] == year]

        event = events.iloc[0]

        return cls(id=event.name)

    @classmethod
    def from_csv(cls, filename: PathLike) -> 'USGS_Event':
        """
        read a CSV file with high-water mark data

        :param filename: file path to CSV
        :return: flood event object
        """

        data = pandas.read_csv(filename, index_col='hwm_id')
        try:
            instance = cls(id=int(data['event_id'].iloc[0]))
        except KeyError:
            instance = cls.from_name(data['eventName'].iloc[0])
        instance.__data = data
        return instance

    @property
    def id(self) -> int:
        return self.__id

    @id.setter
    def id(self, id: int):
        self.__metadata = usgs_flood_events().loc[id]
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

    @property
    def files(self) -> DataFrame:
        """
        list of USGS-provided files surrounding this event

        :return: data frame of file information for this event

        >>> event = USGS_Event(135)
        >>> event.files
                                        name  ... is_nwis
        file_id                               ...
        64549            HWM_Field notes.pdf  ...     NaN
        55811    FLVOL03146_recoveryform.JPG  ...     NaN
        65298                   IMG_1489.JPG  ...     NaN
        65299                   IMG_1490.JPG  ...     NaN
        60279               HWM_MEASURED.jpg  ...     NaN
          ...                            ...  ...     ...
        61637     NCSAM18802 GNSS Survey.jpg  ...     NaN
        57900       SC-BEA-0508.hwm pic1.jpg  ...     NaN
        60277       SC-GEO-0918.hwm pic1.jpg  ...     NaN
        62481     SCBEA18200_SurveySheet.jpg  ...     NaN
        83448      SCBEA18345_FieldSheet.jpg  ...     NaN
        [5589 rows x 19 columns]
        """

        return usgs_files(event_id=self.id)

    @property
    def sensors(self) -> DataFrame:
        """
        list of USGS sensors surrounding this event

        :return: data frame of sensor information for this event

        >>> event = USGS_Event(135)
        >>> event.sensors
                       sensor_type_id  ...  last_updated_by
        instrument_id                  ...
        8080                        1  ...              NaN
        7755                        5  ...              NaN
        8097                        5  ...              NaN
        8030                        1  ...              NaN
        7846                        1  ...              NaN
         ...                      ...  ...              ...
        7889                        1  ...              NaN
        8967                        1  ...           1692.0
        9037                        1  ...              3.0
        8046                        1  ...            761.0
        9511                        5  ...             35.0
        [394 rows x 17 columns]
        """

        return usgs_sensors(event_id=self.id)

    def retrieve_file(self, id: int, path: PathLike):
        'https://stn.wim.usgs.gov/STNServices/Files/{id}/item'

    def high_water_marks(
        self,
        us_states: List[str] = None,
        us_counties: List[str] = None,
        hwm_type: HighWaterMarkType = None,
        quality: HighWaterMarkQuality = None,
        environment: HighWaterMarkEnvironment = None,
        survey_completed: bool = None,
        still_water: bool = None,
    ) -> GeoDataFrame:
        """
        :returns: data frame of data for the current parameters

        >>> flood = USGS_Event(182)
        >>> flood.high_water_marks()
                 latitude  longitude            eventName hwmTypeName  ... hwm_uncertainty                                          hwm_notes siteZone                    geometry
        hwm_id                                                         ...
        22602   31.170642 -81.428402  Irma September 2017      Debris  ...             NaN                                                NaN      NaN  POINT (-81.42840 31.17064)
        22605   31.453850 -81.362853  Irma September 2017   Seed line  ...             0.1                                                NaN      NaN  POINT (-81.36285 31.45385)
        22612   30.720000 -81.549440  Irma September 2017   Seed line  ...             NaN  There is a secondary peak around 5.5 ft, so th...      NaN  POINT (-81.54944 30.72000)
        22636   32.007730 -81.238270  Irma September 2017   Seed line  ...             0.1  Trimble R8 used to establish TBM. Levels ran f...      NaN  POINT (-81.23827 32.00773)
        22653   31.531078 -81.358894  Irma September 2017   Seed line  ...             NaN                                                NaN      NaN  POINT (-81.35889 31.53108)
        ...           ...        ...                  ...         ...  ...             ...                                                ...      ...                         ...
        26171   18.470402 -66.246631  Irma September 2017      Debris  ...             0.5                                                NaN      NaN  POINT (-66.24663 18.47040)
        26173   18.470300 -66.449900  Irma September 2017      Debris  ...             0.5                                levels from GNSS BM      NaN  POINT (-66.44990 18.47030)
        26175   18.463954 -66.140869  Irma September 2017      Debris  ...             0.5                                levels from GNSS BM      NaN  POINT (-66.14087 18.46395)
        26177   18.488720 -66.392160  Irma September 2017      Debris  ...             0.5                                levels from GNSS BM      NaN  POINT (-66.39216 18.48872)
        26179   18.005607 -65.871768  Irma September 2017      Debris  ...             0.5                                levels from GNSS BM      NaN  POINT (-65.87177 18.00561)
        [506 rows x 53 columns]
        >>> flood.high_water_marks(quality=['EXCELLENT', 'GOOD'])
                 latitude  longitude            eventName hwmTypeName  ...                                          hwm_notes peak_summary_id siteZone                    geometry
        hwm_id                                                         ...
        22605   31.453850 -81.362853  Irma September 2017   Seed line  ...                                                NaN             NaN      NaN  POINT (-81.36285 31.45385)
        22612   30.720000 -81.549440  Irma September 2017   Seed line  ...  There is a secondary peak around 5.5 ft, so th...             NaN      NaN  POINT (-81.54944 30.72000)
        22636   32.007730 -81.238270  Irma September 2017   Seed line  ...  Trimble R8 used to establish TBM. Levels ran f...             NaN      NaN  POINT (-81.23827 32.00773)
        22674   32.030907 -80.900605  Irma September 2017   Seed line  ...                                                NaN          5042.0      NaN  POINT (-80.90061 32.03091)
        22849   30.741940 -81.687780  Irma September 2017      Debris  ...                                                NaN          4834.0      NaN  POINT (-81.68778 30.74194)
        ...           ...        ...                  ...         ...  ...                                                ...             ...      ...                         ...
        25150   30.038222 -81.880928  Irma September 2017   Seed line  ...                              GNSS Level II survey.             NaN      NaN  POINT (-81.88093 30.03822)
        25151   30.118110 -81.760220  Irma September 2017   Seed line  ...                             GNSS Level III survey.             NaN      NaN  POINT (-81.76022 30.11811)
        25158   29.720560 -81.506110  Irma September 2017   Seed line  ...                              GNSS Level II survey.             NaN      NaN  POINT (-81.50611 29.72056)
        25159   30.097514 -81.794375  Irma September 2017   Seed line  ...                             GNSS Level III survey.             NaN      NaN  POINT (-81.79438 30.09751)
        25205   29.783890 -81.263060  Irma September 2017   Seed line  ...                              GNSS Level II survey.             NaN      NaN  POINT (-81.26306 29.78389)
        [277 rows x 53 columns]
        """

        if self.__query is None:
            self.__query = HighWaterMarksQuery(
                event_id=self.id,
                event_type=self.event_type,
                event_status=self.event_status,
                us_states=us_states,
                us_counties=us_counties,
                hwm_type=hwm_type,
                quality=quality,
                environment=environment,
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
            if quality is not None:
                self.__query.quality = quality
            if environment is not None:
                self.__query.environment = environment
            if survey_completed is not None:
                self.__query.survey_completed = survey_completed
            if still_water is not None:
                self.__query.still_water = still_water

        return self.__query.data

    def __eq__(self, other: 'USGS_Event') -> bool:
        return (
            self.__query is not None
            and other.__query is not None
            and self.__query == other.__query
        )

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(id={repr(self.id)})'


class USGS_StormEvent(USGS_Event):
    """
    representation of an arbitrary storm flood event as defined by the USGS and NHC
    """

    def __init__(self, name: str, year: int):
        """
        :param name: storm name
        :param year: storm year
        """

        storms = usgs_flood_storms(year=year)
        storm = storms[(storms['nhc_name'] == name.upper().strip()) & (storms['year'] == year)]

        if len(storm) == 0:
            raise ValueError(f'storm "{name} {year}" not found in USGS HWM database')

        super().__init__(id=storm.index[0])
