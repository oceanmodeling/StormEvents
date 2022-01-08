from enum import Enum
from functools import lru_cache
import json
import os
import re
from typing import Any, Dict, List

from matplotlib import pyplot
from matplotlib.axis import Axis
import numpy
import pandas
import requests
from typepigeon import convert_value

from stormevents.storms import nhc_storms
from stormevents.utilities import get_logger

LOGGER = get_logger(__name__)


class EventType(Enum):
    # TODO fill out other options
    HURRICANE = 2


class EventStatus(Enum):
    # TODO fill out other options
    COMPLETED = 0


class HWMType(Enum):
    # TODO fill out other options
    pass


class HWMQuality(Enum):
    # TODO fill out other options
    EXCELLENT = 1
    GOOD = 2
    FAIR = 3
    POOR = 4


class HWMEnvironment(Enum):
    # TODO fill out other options
    COASTAL = 'Coastal'
    RIVERINE = 'Riverine'


class HighWaterMarks:
    URL = 'https://stn.wim.usgs.gov/STNServices/HWMs/FilteredHWMs.json'

    def __init__(
        self,
        event_id: int,
        event_type: EventType,
        event_status: EventStatus = None,
        us_states: List[str] = None,
        us_counties: List[str] = None,
        hwm_type: HWMType = None,
        hwm_quality: HWMQuality = None,
        hwm_environment: HWMEnvironment = None,
        survey_completed: bool = True,
        still_water: bool = False,
    ):
        if event_status is None:
            event_status = EventStatus.COMPLETED
        if hwm_environment is None:
            hwm_environment = HWMEnvironment.RIVERINE

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

    @property
    def event_type(self) -> EventType:
        return self.__event_type

    @event_type.setter
    def event_type(self, event_type: EventType):
        self.__event_type = convert_value(event_type, EventType)

    @property
    def hwm_quality(self) -> HWMQuality:
        return self.__hwm_quality

    @hwm_quality.setter
    def hwm_quality(self, hwm_quality: HWMQuality):
        self.__hwm_quality = convert_value(hwm_quality, HWMQuality)

    @property
    def hwm_type(self) -> HWMType:
        return self.__hwm_type

    @hwm_type.setter
    def hwm_type(self, hwm_type: HWMType):
        self.__hwm_type = convert_value(hwm_type, HWMType)

    @property
    def hwm_environment(self) -> HWMEnvironment:
        return self.__hwm_environment

    @hwm_environment.setter
    def hwm_environment(self, hwm_environment: HWMEnvironment):
        self.__hwm_environment = convert_value(hwm_environment, HWMEnvironment)

    @property
    def query(self) -> Dict[str, Any]:
        return {
            'Event': self.event_id,
            'EventType': self.event_type.value if self.event_type is not None else None,
            'EventStatus': self.event_status.value if self.event_status is not None else None,
            'States': self.us_states,
            'County': self.us_counties,
            'HWMType': self.hwm_type.value if self.hwm_type is not None else None,
            'HWMQuality': self.hwm_quality.value if self.hwm_quality is not None else None,
            'HWMEnvironment': self.hwm_environment.value
            if self.hwm_environment is not None
            else None,
            'SurveyComplete': self.survey_completed,
            'StillWater': self.still_water,
        }

    @property
    def data(self) -> pandas.DataFrame:
        if self.__data is None or self.__previous_query != self.query:
            response = requests.get(self.URL, params=self.query)
            data = pandas.DataFrame(response.json())
            data.set_index('hwm_id', inplace=True)
            self.__data = data
        return self.__data

    def plot(
        self, axis: Axis = None, show: bool = True, **kwargs,
    ):
        if axis is None:
            fig = pyplot.figure()
            axis = fig.add_subplot(111)

        for hwm_id, hwm in self.data.iterrows():
            axis.scatter(
                hwm['longitude'], hwm['latitude'], c=hwm['elev_ft'], **kwargs,
            )

        if show:
            pyplot.show()

        return axis


class HurricaneHighWaterMarks(HighWaterMarks):
    def __init__(
        self,
        storm_name: str,
        storm_year: int,
        hwm_type: HWMType = None,
        hwm_quality: HWMQuality = None,
        hwm_environment: HWMEnvironment = None,
        survey_completed: bool = True,
        still_water: bool = False,
    ):
        if hwm_environment is None:
            hwm_environment = HWMEnvironment.RIVERINE

        self.storms = highwatermark_storms()

        event_id = self.storms[
            (self.storms['name'] == storm_name.upper()) & (self.storms['year'] == storm_year)
        ].index[0]

        super().__init__(
            event_id=event_id,
            event_status=EventStatus.COMPLETED,
            event_type=EventType.HURRICANE,
            us_states=None,
            us_counties=None,
            hwm_type=hwm_type,
            hwm_quality=hwm_quality,
            hwm_environment=hwm_environment,
            survey_completed=survey_completed,
            still_water=still_water,
        )

    @classmethod
    def from_storm_name(cls, name: str, year: int,) -> 'HighWaterMarks':
        event_name, event_year, cls.params['Event'] = cls._get_event_id_from_name(name)
        response = requests.get(cls.URL, params=cls.params)
        response.raise_for_status()
        json_data = json.loads(response.text)
        hwm_stations = dict()
        for data in json_data:
            if 'elev_ft' in data.keys():
                hwm_stations[str(data['hwm_id'])] = data
        filter_dict = cls._init_filter_dict(filter_dict)
        return cls(event_name, event_year, filter_dict=filter_dict, **hwm_stations)


@lru_cache(maxsize=None)
def highwatermark_events(
    event_type: EventType, event_status: EventStatus,
) -> pandas.DataFrame:
    """
    USGS is not standardizing event naming. Sometimes years are included,
    but sometimes they are ommitted. The order in which the names are in
    the response is also not standardized. Some workaround come into play
    in this algorithm in order to identify and categorize the dataset.
    USGS should standardize their REST server data.
    """

    response = requests.get(
        HighWaterMarks.URL,
        params={
            'Event': None,
            'EventType': event_type.value,
            'EventStatus': event_status.value,
            'States': None,
            'County': None,
            'HWMType': None,
            'HWMQuality': None,
            'HWMEnvironment': None,
            'SurveyComplete': None,
            'StillWater': None,
        },
    )

    LOGGER.info('building table of USGS high water mark survey events')

    data = response.json()

    events = {}
    for entry in data:
        event_id = entry['event_id']
        if event_id not in events or events[event_id][2] is None:
            name = entry['eventName']
            event = [event_id, name]
            if 'survey_date' in entry:
                year = int(entry['survey_date'].split('-')[0])
            elif 'flag_date' in entry:
                year = int(entry['flag_date'].split('-')[0])
            else:
                search = re.findall('\d{4}', name)
                if len(search) > 0:
                    year = int(search[0])
                else:
                    # otherwise, search the NHC database for the storm year
                    storms = nhc_storms()
                    storm_names = pandas.unique(storms['name'])
                    storm_names.sort()
                    for storm_name in storm_names:
                        if storm_name.lower() in name.lower():
                            years = storms[storms['name'] == storm_name]['year']
                            if len(years) == 1:
                                year = years[0]
                            else:
                                LOGGER.warning(
                                    f'could not find year of "{name}" in USGS high water mark database nor in NHC table'
                                )
                                year = None
                            break
                    else:
                        year = None
            event.append(year)
            events[event_id] = event

    events = pandas.DataFrame(list(events.values()), columns=['id', 'name', 'year'],)
    events.set_index('id', inplace=True)

    return events


@lru_cache(maxsize=None)
def highwatermark_storms() -> pandas.DataFrame:
    events = highwatermark_events(
        event_type=EventType.HURRICANE, event_status=EventStatus.COMPLETED,
    )

    events.rename(columns={'name': 'usgs_name'}, inplace=True)
    events['name'] = None
    events['nhc_code'] = None

    storms = nhc_storms()

    storm_names = pandas.unique(storms['name'])
    storm_names.sort()
    for storm_name in storm_names:
        event_storms = events[
            events['usgs_name'].str.contains(storm_name, flags=re.IGNORECASE,)
        ]
        for event_id, event in event_storms.iterrows():
            storms_matching = storms[
                (storms['name'] == storm_name) & (storms['year'] == event['year'])
            ]

            for nhc_code, storm in storms_matching.iterrows():
                events.at[event_id, 'name'] = storm['name']
                events.at[event_id, 'nhc_code'] = storm.name

    return events[['name', 'year', 'nhc_code', 'usgs_name']]


def write_high_water_marks(obs_dir, name, year):
    url = 'https://stn.wim.usgs.gov/STNServices/HWMs/FilteredHWMs.json'
    params = {'EventType': 2, 'EventStatus': 0}  # 2 for hurricane  # 0 for completed
    default_filter = {'riverine': True, 'non_still_water': True}

    nameyear = (name + year).lower()

    out_dir = os.path.join(obs_dir, 'hwm')

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    fname = os.path.join(out_dir, nameyear + '.csv')
    usgs_json_file = os.path.join(out_dir, 'usgs_hwm_tmp.json')

    if not os.path.exists(usgs_json_file):
        response = requests.get(url, params=params)
        response.raise_for_status()
        json_data = json.loads(response.text)
        with open(usgs_json_file, 'w') as outfile:
            json.dump(json_data, outfile)
    else:
        with open(usgs_json_file) as json_file:
            json_data = json.load(json_file)

    hwm_stations = dict()
    for data in json_data:
        if 'elev_ft' in data.keys() and name.lower() in data['eventName'].lower():
            hwm_stations[str(data['hwm_id'])] = data

    log = pandas.DataFrame.from_dict(hwm_stations)

    hwm = []
    ii = 0
    for key in log.keys():
        l0 = []
        for key0 in log[key].keys():
            l0.append(log[key][key0])
        hwm.append(l0)
    #
    hwm = numpy.array(hwm)
    df = pandas.DataFrame(data=hwm, columns=log[key].keys())

    drop_poor = False
    if drop_poor:
        for i in range(len(df)):
            tt = df.hwmQualityName[i]
            if 'poor' in tt.lower():
                df.hwmQualityName[i] = numpy.nan

        df = df.dropna()
    df['elev_m'] = pandas.to_numeric(df['elev_ft']) * 0.3048  # in meter
    #
    df.to_csv(fname)
