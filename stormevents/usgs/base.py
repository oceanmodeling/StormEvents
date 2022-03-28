from enum import Enum


class EventType(Enum):
    """
    https://stn.wim.usgs.gov/STNServices/EventTypes.json
    """

    RIVERINE_FLOOD = 1
    HURRICANE = 2
    DROUGHT = 3
    NOREASTER = 4
    TSUNAMI = 6


class EventStatus(Enum):
    """
    https://stn.wim.usgs.gov/STNServices/EventStatus.json
    """

    ACTIVE = 1
    COMPLETED = 2


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
