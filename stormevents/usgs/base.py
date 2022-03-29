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
