from enum import Enum

import pandas
from pandas import DataFrame


class SensorType(Enum):
    """
    https://stn.wim.usgs.gov/STNServices/SensorTypes.json
    """

    PRESSURE_TRANSDUCER = 1
    METEROLOGICAL_STATION = 2
    THERMOMETER = 3
    WEBCAM = 4
    RAPID_DEPLOYMENT_GAGE = 5
    RAIN_GAGE = 6


class FileType(Enum):
    """
    https://stn.wim.usgs.gov/STNServices/FileTypes.json
    """

    PHOTO = 1
    DATA = 2
    HISTORIC_CITATION = 3
    FIELD_SHEETS = 4
    LEVEL_NOTES = 5
    SITE_SKETCH = 6
    OTHER = 7
    LINK = 8
    NGS_DATASHEET = 9
    SKETCH = 10
    LANDOWNER_PERMISSION_FORM = 11
    HYDROGRAPH = 13


class DeploymentType(Enum):
    """
    https://stn.wim.usgs.gov/STNServices/DeploymentTypes.json
    """

    WATER_LEVEL = 1
    WAVE_HEIGHT = 2
    BAROMETRIC = 3
    TEMPERATURE = 4
    WIND_SPEED = 5
    HUMIDITY = 6
    AIR_TEMPERATURE = 7
    WATER_TEMPERATURE = 8
    RAPID_DEPLOYMENT = 9


def usgs_sensors() -> DataFrame:
    """
    this function collects all USGS flood events of the given type and status that have high-water mark data

    https://stn.wim.usgs.gov/STNServices/Instruments.json

    :return: table of sensors

    >>> usgs_sensors()
                   sensor_type_id  ...  housing_serial_number
    instrument_id                  ...
    8080                        1  ...                    NaN
    7755                        5  ...                    NaN
    9512                        1  ...                    NaN
    9568                        1  ...                    NaN
    7595                        1  ...                    NaN
    ...                       ...  ...                    ...
    10432                       1  ...                    NaN
    10427                       1  ...                    NaN
    10450                       1  ...                    NaN
    10449                       1  ...                    NaN
    9505                        1  ...                    NaN
    [4155 rows x 17 columns]
    """
    sensors = pandas.read_json('https://stn.wim.usgs.gov/STNServices/Instruments.json')
    sensors.set_index('instrument_id', inplace=True)
    return sensors
