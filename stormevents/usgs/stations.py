from enum import Enum


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


class USGS_Station:
    # TODO implement sensor interface
    pass


class USGS_StationQuery:
    # TODO implement query interface
    pass
