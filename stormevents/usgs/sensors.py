from enum import Enum
from os import PathLike

import pandas
from pandas import DataFrame
import requests


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


class USGS_File:
    def __init__(self, id: int):
        files = usgs_files()
        if id not in files:
            raise FileNotFoundError(self.url)

        self.id = id

    @property
    def url(self) -> str:
        return f'https://stn.wim.usgs.gov/STNServices/Files/{id}/item'

    def to_file(self, path: PathLike):
        response = requests.get(self.url, stream=True)
        with open(path, 'wb') as output_file:
            for chunk in response.iter_content(chunk_size=1024):
                output_file.write(chunk)


def usgs_files(file_type: FileType = None, event_id: int = None) -> DataFrame:
    """
    this function collects USGS files

    https://stn.wim.usgs.gov/STNServices/Files.json

    :param file_type: file type
    :param event_id: USGS event ID
    :return: table of files

    >>> usgs_files()
                                                   name  ... script_parent
    file_id                                              ...
    8075                              AlafiaRv@41_1.JPG  ...           NaN
    8076                              AlafiaRv@41_2.JPG  ...           NaN
    8079                        SSS-FL-MIA-001WL-01.JPG  ...           NaN
    8080                        SSS-FL-MIA-001WL-02.JPG  ...           NaN
    8081                        SSS-FL-MIA-001WL-03.JPG  ...           NaN
    ...                                             ...  ...           ...
    125592   chetco 1 20201019 04-Nov-2020 11-18-17.pdf  ...           NaN
    125593   chetco 1 20201022 04-Nov-2020 11-17-08.pdf  ...           NaN
    125594              chetco 21-Dec-2020 10-06-59.pdf  ...           NaN
    125595                        stn-db-schema (1).pdf  ...           NaN
    125596                        stn-db-schema (1).pdf  ...           NaN
    [89421 rows x 19 columns]
    """

    if event_id is None:
        url = 'https://stn.wim.usgs.gov/STNServices/Files.json'
    else:
        url = f'https://stn.wim.usgs.gov/STNServices/Events/{event_id}/Files.json'

    files = pandas.read_json(url)
    files.set_index('file_id', inplace=True)

    if file_type is not None:
        if isinstance(file_type, FileType):
            file_type = file_type.value

        files = files[files['filetype_id'] == file_type]
    return files


def usgs_sensors(
    sensor_type: SensorType = None,
    deployment_type: DeploymentType = None,
    event_id: int = None,
) -> DataFrame:
    """
    this function collects USGS sensors with the given type and deployment

    https://stn.wim.usgs.gov/STNServices/Instruments.json

    :param sensor_type: type of sensor
    :param deployment_type: deployment type of sensor
    :param event_id: USGS event ID
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

    if event_id is None:
        url = 'https://stn.wim.usgs.gov/STNServices/Instruments.json'
    else:
        url = f'https://stn.wim.usgs.gov/STNServices/Events/{event_id}/Instruments.json'

    sensors = pandas.read_json(url)
    sensors.set_index('instrument_id', inplace=True)

    if sensor_type is not None:
        if isinstance(sensor_type, SensorType):
            sensor_type = sensor_type.value
        sensors = sensors[sensors['sensor_type_id'] == sensor_type]

    if deployment_type is not None:
        if isinstance(deployment_type, DeploymentType):
            deployment_type = deployment_type.value
        sensors = sensors[sensors['deployment_type_id'] == deployment_type]

    return sensors
