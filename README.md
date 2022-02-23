# StormEvents

[![tests](https://github.com/oceanmodeling/StormEvents/workflows/tests/badge.svg)](https://github.com/oceanmodeling/StormEvents/actions?query=workflow%3Atests)
[![build](https://github.com/oceanmodeling/StormEvents/workflows/build/badge.svg)](https://github.com/oceanmodeling/StormEvents/actions?query=workflow%3Abuild)
[![codecov](https://codecov.io/gh/oceanmodeling/StormEvents/branch/main/graph/badge.svg?token=BQWB1QKJ3Q)](https://codecov.io/gh/oceanmodeling/StormEvents)
[![version](https://img.shields.io/pypi/v/StormEvents)](https://pypi.org/project/StormEvents)
[![license](https://img.shields.io/github/license/oceanmodeling/StormEvents)](https://opensource.org/licenses/gpl-license)
[![style](https://sourceforge.net/p/oitnb/code/ci/default/tree/_doc/_static/oitnb.svg?format=raw)](https://sourceforge.net/p/oitnb/code)

`stormevents` provides Python interfaces for observational data surrounding named storm events.

```bash
pip install stormevents
```

Full documentation can be found at https://stormevents.readthedocs.io

## Usage

There are two ways to retrieve observational data via `stormevents`;

1. retrieve data for any arbitrary time interval / region, or
2. retrieve data surrounding a specific storm.

### retrieve data for any arbitrary time interval / region

`stormevents` currently implements retrieval for

- storm tracks from the National Hurricane Center (NHC),
- high-water mark (HWM) surveys provided by the United States Geological Survey (USGS), and
- data products from the Center for Operational Oceanographic Products and Services (CO-OPS).

#### storm tracks from the National Hurricane Center (NHC)

The [National Hurricane Center (NHC)](https://www.nhc.noaa.gov) tracks and tropical cyclones dating back to 1851.

The `nhc_storms()` function provides a list of NHC storms from their online archive:

```python
from stormevents.nhc import nhc_storms

nhc_storms()
```

```
                name class  year basin  number    source          start_date            end_date
nhc_code                                                                                        
AL021851     UNNAMED    HU  1851    AL       2   ARCHIVE 1851-07-05 12:00:00 1851-07-05 12:00:00
AL031851     UNNAMED    TS  1851    AL       3   ARCHIVE 1851-07-10 12:00:00 1851-07-10 12:00:00
AL041851     UNNAMED    HU  1851    AL       4   ARCHIVE 1851-08-16 00:00:00 1851-08-27 18:00:00
AL051851     UNNAMED    TS  1851    AL       5   ARCHIVE 1851-09-13 00:00:00 1851-09-16 18:00:00
AL061851     UNNAMED    TS  1851    AL       6   ARCHIVE 1851-10-16 00:00:00 1851-10-19 18:00:00
...              ...   ...   ...   ...     ...       ...                 ...                 ...
EP922021      INVEST    DB  2021    EP      92  METWATCH 2021-06-05 06:00:00                 NaT
AL952021      INVEST    DB  2021    AL      95  METWATCH 2021-10-28 12:00:00                 NaT
AL962021      INVEST    EX  2021    AL      96  METWATCH 2021-11-07 12:00:00                 NaT
EP712022  GENESIS001    DB  2022    EP      71   GENESIS 2022-01-20 12:00:00                 NaT
EP902022      INVEST    LO  2022    EP      90  METWATCH 2022-01-20 12:00:00                 NaT

[2729 rows x 8 columns]
```

##### retrieve storm track by NHC code

```python
from stormevents.nhc import VortexTrack

track = VortexTrack('AL112017')
track.data
```

```
    basin storm_number record_type            datetime  ...   direction     speed    name                    geometry
0      AL           11        BEST 2017-08-30 00:00:00  ...    0.000000  0.000000  INVEST  POINT (-26.90000 16.10000)
1      AL           11        BEST 2017-08-30 06:00:00  ...  274.421188  6.951105  INVEST  POINT (-28.30000 16.20000)
2      AL           11        BEST 2017-08-30 12:00:00  ...  274.424523  6.947623    IRMA  POINT (-29.70000 16.30000)
3      AL           11        BEST 2017-08-30 18:00:00  ...  270.154371  5.442611    IRMA  POINT (-30.80000 16.30000)
4      AL           11        BEST 2017-08-30 18:00:00  ...  270.154371  5.442611    IRMA  POINT (-30.80000 16.30000)
..    ...          ...         ...                 ...  ...         ...       ...     ...                         ...
168    AL           11        BEST 2017-09-12 12:00:00  ...  309.875306  7.262151    IRMA  POINT (-86.90000 33.80000)
169    AL           11        BEST 2017-09-12 18:00:00  ...  315.455084  7.247674    IRMA  POINT (-88.10000 34.80000)
170    AL           11        BEST 2017-09-13 00:00:00  ...  320.849994  5.315966    IRMA  POINT (-88.90000 35.60000)
171    AL           11        BEST 2017-09-13 06:00:00  ...  321.042910  3.973414    IRMA  POINT (-89.50000 36.20000)
172    AL           11        BEST 2017-09-13 12:00:00  ...  321.262133  3.961652    IRMA  POINT (-90.10000 36.80000)

[173 rows x 22 columns]
```

##### retrieve storm track by name and year

If you do not know the storm code, you can input the storm name and year:

```python
from stormevents.nhc import VortexTrack

vortex = VortexTrack.from_storm_name('irma', 2017)
```

```
VortexTrack('AL112017', Timestamp('2017-08-30 00:00:00'), Timestamp('2017-09-13 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', None)
```

##### specify storm track file deck

By default, `VortexTrack` retrieves data from the `BEST` track file deck (`b`). You can specify that you want
the `ADVISORY` (`a`) or `FIXED` (`f`) file decks with the `file_deck` parameter.

```python
from stormevents.nhc import VortexTrack

track = VortexTrack('AL112017', file_deck='a')
track.data
```

```
      basin storm_number record_type            datetime  ...   direction      speed    name                    geometry
0        AL           11        CARQ 2017-08-27 06:00:00  ...    0.000000   0.000000  INVEST  POINT (-17.40000 11.70000)
1        AL           11        CARQ 2017-08-27 12:00:00  ...  281.524268   2.574642  INVEST  POINT (-17.90000 11.80000)
2        AL           11        CARQ 2017-08-27 12:00:00  ...  281.524268   2.574642  INVEST  POINT (-13.30000 11.50000)
3        AL           11        CARQ 2017-08-27 18:00:00  ...  281.528821   2.573747  INVEST  POINT (-18.40000 11.90000)
4        AL           11        CARQ 2017-08-27 18:00:00  ...  281.528821   2.573747  INVEST  POINT (-16.00000 11.50000)
...     ...          ...         ...                 ...  ...         ...        ...     ...                         ...
10739    AL           11        HMON 2017-09-16 09:00:00  ...   52.414833  11.903071          POINT (-84.30000 43.00000)
10740    AL           11        HMON 2017-09-16 12:00:00  ...    7.196515   6.218772          POINT (-84.30000 41.00000)
10741    AL           11        HMON 2017-09-16 12:00:00  ...    7.196515   6.218772          POINT (-82.00000 39.50000)
10742    AL           11        HMON 2017-09-16 12:00:00  ...    7.196515   6.218772          POINT (-84.30000 44.00000)
10743    AL           11        HMON 2017-09-16 15:00:00  ...  122.402907  22.540200          POINT (-81.90000 39.80000)

[10744 rows x 22 columns
```

##### read storm track from file

If you have an ATCF or `fort.22` file, use the corresponding methods:

```python
from stormevents.nhc import VortexTrack

VortexTrack.from_atcf_file('tests/data/input/test_from_atcf/atcf.trk')
```

```
VortexTrack('BT02008', Timestamp('2008-10-16 17:06:00'), Timestamp('2008-10-20 20:06:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', PosixPath('tests/data/input/test_from_atcf/florence2018_atcf.trk'))
```

```python
from stormevents.nhc import VortexTrack

VortexTrack.from_fort22('tests/data/input/test_from_fort22/irma2017_fort.22')
```

```
VortexTrack('AL112017', Timestamp('2017-09-05 00:00:00'), Timestamp('2017-09-19 00:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', PosixPath('tests/data/input/test_from_fort22/irma2017_fort.22'))
```

##### write storm track to `fort.22` file

```python
from stormevents.nhc import VortexTrack

track = VortexTrack.from_storm_name('florence', 2018)
track.write('fort.22')
```

#### high-water mark (HWM) surveys provided by the United States Geological Survey (USGS)

The [United States Geological Survey (USGS)](https://www.usgs.gov)
conducts surveys of flooded areas following flood events to determine the highest level of water elevation, and provides the
results of these surveys via their API.

##### list flood events that have HWM surveys

```python
from stormevents.usgs import usgs_highwatermark_events

usgs_highwatermark_events()
```

```
                                     name  year
usgs_id                                        
7                      FEMA 2013 exercise  2013
8                                   Wilma  2013
18                         Isaac Aug 2012  2012
19                                   Rita  2005
23                                  Irene  2011
24                                  Sandy  2017
119                               Joaquin  2015
131                               Hermine  2016
133                 Isabel September 2003  2003
135                  Matthew October 2016  2016
180                       Harvey Aug 2017  2017
182                   Irma September 2017  2017
189                  Maria September 2017  2017
196                     Nate October 2017  2017
281                      Lane August 2018  2019
283                     Florence Sep 2018  2018
287                      Michael Oct 2018  2018
291                 2019 Hurricane Dorian  2019
301                 2020 Hurricane Isaias  2020
303      2020 TS Marco - Hurricane  Laura  2020
304                  2020 Hurricane Sally  2020
305                  2020 Hurricane Delta  2020
310           2021 Tropical Cyclone Henri  2021
312             2021 Tropical Cyclone Ida  2021
```

##### retrieve HWM survey data for any flood event

```python
from stormevents.usgs import HighWaterMarks

survey = HighWaterMarks(182)
survey.data
```

```
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
```

```python
from stormevents.usgs import HighWaterMarks

survey = HighWaterMarks(182)
survey.hwm_quality = 'EXCELLENT', 'GOOD'
survey.data
```

```
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
```

#### data products from the Center for Operational Oceanographic Products and Services (CO-OPS)

The [Center for Operational Oceanographic Products and Services (CO-OPS)](https://tidesandcurrents.noaa.gov)
maintains and operates a large array of tidal buoys and oceanic weather stations that measure water and atmospheric variables
across the coastal United States. CO-OPS provides several [data products](https://tidesandcurrents.noaa.gov/products.html)
including hourly water levels, tidal datums and predictions, and trends in sea level over time.

A list of CO-OPS stations can be retrieved with the `coops_stations()` function.

```python
from stormevents.coops import coops_stations

coops_stations()
```

```
        nws_id                          name state removed                     geometry
nos_id                                                                                 
1600012  46125                     QREB buoy           NaT   POINT (122.62500 37.75000)
1611400  NWWH1                    Nawiliwili    HI     NaT  POINT (-159.37500 21.95312)
1612340  OOUH1                      Honolulu    HI     NaT  POINT (-157.87500 21.31250)
1612480  MOKH1                      Mokuoloe    HI     NaT  POINT (-157.75000 21.43750)
1615680  KLIH1       Kahului, Kahului Harbor    HI     NaT  POINT (-156.50000 20.89062)
...        ...                           ...   ...     ...                          ...
9759394  MGZP4                      Mayaguez    PR     NaT   POINT (-67.18750 18.21875)
9759938  MISP4                   Mona Island           NaT   POINT (-67.93750 18.09375)
9761115  BARA9                       Barbuda           NaT   POINT (-61.81250 17.59375)
9999530  FRCB6  Bermuda, Ferry Reach Channel           NaT   POINT (-64.68750 32.37500)
9999531               Calcasieu Test Station    LA     NaT   POINT (-93.31250 29.76562)

[363 rows x 5 columns]
```

Additionally, you can use a Shapely `Polygon` or `MultiPolygon` to constrain the stations query to a specific region:

```python
from shapely.geometry import Polygon
from stormevents.coops import coops_stations_within_region

region = Polygon(...)

coops_stations_within_region(region=region)
```

```
        nws_id                               name state removed                    geometry
nos_id                                                                                     
8651370  DUKN7                               Duck    NC     NaT  POINT (-75.75000 36.18750)
8652587  ORIN7                Oregon Inlet Marina    NC     NaT  POINT (-75.56250 35.78125)
8654467  HCGN7              USCG Station Hatteras    NC     NaT  POINT (-75.68750 35.21875)
8656483  BFTN7          Beaufort, Duke Marine Lab    NC     NaT  POINT (-76.68750 34.71875)
8658120  WLON7                         Wilmington    NC     NaT  POINT (-77.93750 34.21875)
8658163  JMPN7                 Wrightsville Beach    NC     NaT  POINT (-77.81250 34.21875)
8661070  MROS1                    Springmaid Pier    SC     NaT  POINT (-78.93750 33.65625)
8662245  NITS1   Oyster Landing (N Inlet Estuary)    SC     NaT  POINT (-79.18750 33.34375)
8665530  CHTS1  Charleston, Cooper River Entrance    SC     NaT  POINT (-79.93750 32.78125)
8670870  FPKG1                       Fort Pulaski    GA     NaT  POINT (-80.87500 32.03125)
```

##### retrieve CO-OPS data product from within a region and time interval

To retrieve data, you must provide three things:

1. the data product of interest; one of
    - `water_level` - Preliminary or verified water levels, depending on availability.
    - `air_temperature` - Air temperature as measured at the station.
    - `water_temperature` - Water temperature as measured at the station.
    - `wind` - Wind speed, direction, and gusts as measured at the station.
    - `air_pressure` - Barometric pressure as measured at the station.
    - `air_gap` - Air Gap (distance between a bridge and the water's surface) at the station.
    - `conductivity` - The water's conductivity as measured at the station.
    - `visibility` - Visibility from the station's visibility sensor. A measure of atmospheric clarity.
    - `humidity` - Relative humidity as measured at the station.
    - `salinity` - Salinity and specific gravity data for the station.
    - `hourly_height` - Verified hourly height water level data for the station.
    - `high_low` - Verified high/low water level data for the station.
    - `daily_mean` - Verified daily mean water level data for the station.
    - `monthly_mean` - Verified monthly mean water level data for the station.
    - `one_minute_water_level`  One minute water level data for the station.
    - `predictions` - 6 minute predictions water level data for the station.*
    - `datums` - datums data for the stations.
    - `currents` - Currents data for currents stations.
    - `currents_predictions` - Currents predictions data for currents predictions stations.
2. a region within which to retrieve the data product
3. a time interval within which to retrieve the data product

```python
from datetime import datetime, timedelta

from shapely.geometry import Polygon
from stormevents.coops import coops_product_within_region

polygon = Polygon(...)

coops_product_within_region(
    'water_level',
    region=polygon,
    start_date=datetime.now() - timedelta(hours=1),
)
```

```
<xarray.Dataset>
Dimensions:  (nos_id: 10, t: 10)
Coordinates:
  * nos_id   (nos_id) int64 8651370 8652587 8654467 ... 8662245 8665530 8670870
  * t        (t) datetime64[ns] 2022-02-23T08:06:00 ... 2022-02-23T09:00:00
    nws_id   (nos_id) <U5 'DUKN7' 'ORIN7' 'HCGN7' ... 'NITS1' 'CHTS1' 'FPKG1'
    x        (nos_id) float64 -75.75 -75.56 -75.69 ... -79.19 -79.94 -80.88
    y        (nos_id) float64 36.19 35.78 35.22 34.72 ... 33.34 32.78 32.03
Data variables:
    v        (nos_id, t) float32 6.097 6.096 6.059 6.005 ... 2.39 2.324 2.336
    s        (nos_id, t) float32 0.07 0.052 0.054 0.063 ... 0.014 0.02 0.009
    f        (nos_id, t) object '1,0,0,0' '1,0,0,0' ... '0,0,0,0' '1,0,0,0'
    q        (nos_id, t) object 'p' 'p' 'p' 'p' 'p' 'p' ... 'p' 'p' 'p' 'p' 'p'
```

### retrieve data surrounding a specific storm

The `StormEvent` class provides an interface to retrieve data within the time interval and spatial bounds of a specific storm
event.

You can create a new `StormEvent` object from a storm name and year,

```python
from stormevents import StormEvent

StormEvent('FLORENCE', 2018)
```

```
StormEvent('FLORENCE', 2018)
```

or from a storm NHC code,

```python
from stormevents import StormEvent

StormEvent.from_nhc_code('EP172016')
```

```
StormEvent('PAINE', 2016)
```

or from a USGS flood event ID.

```python
from stormevents import StormEvent

StormEvent.from_usgs_id(310)
```

```
StormEvent('HENRI', 2021)
```

To constrain the time interval, you can provide an absolute time range,

```python
from stormevents import StormEvent
from datetime import datetime

StormEvent('paine', 2016, start_date='2016-09-19', end_date=datetime(2016, 9, 19, 12))
```

```
StormEvent('PAINE', 2016, start_date='2016-09-19 00:00:00', end_date='2016-09-19 12:00:00')
```

```python
from stormevents import StormEvent
from datetime import datetime

StormEvent('paine', 2016, end_date=datetime(2016, 9, 19, 12))
```

```
StormEvent('PAINE', 2016, end_date='2016-09-19 12:00:00')
```

or, alternatively, you can provide relative time deltas, which will be interpreted compared to the absolute time interval
provided by the NHC.

```python
from stormevents import StormEvent
from datetime import timedelta

StormEvent('florence', 2018, start_date=timedelta(days=2))  # <- start 2 days after NHC start time
```

```
StormEvent('FLORENCE', 2018, start_date='2018-09-01 06:00:00')
```

```python
from stormevents import StormEvent
from datetime import timedelta

StormEvent(
    'henri',
    2021,
    start_date=timedelta(days=-3),  # <- start 3 days before NHC end time
    end_date=timedelta(days=-2),  # <- end 2 days before NHC end time
)
```

```
StormEvent('HENRI', 2021, start_date='2021-08-21 12:00:00', end_date='2021-08-22 12:00:00')
```

```python
from stormevents import StormEvent
from datetime import timedelta

StormEvent('ida', 2021, end_date=timedelta(days=2))  # <- end 2 days after NHC start time 
```

```
StormEvent('IDA', 2021, end_date='2021-08-29 18:00:00')
```

#### retrieve data for a storm

The following methods are very similar to the data getter functions detailed above. However, these methods are tied to a
specific storm event, and will focus on retrieving data within the spatial region and time interval of their specific storm
event.

##### track data from the National Hurricane Center (NHC)

```python
from stormevents import StormEvent

storm = StormEvent('florence', 2018)
storm.track()
```

```
VortexTrack('AL062018', Timestamp('2018-08-30 06:00:00'), Timestamp('2018-09-18 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', None)
```

```python
from stormevents import StormEvent

storm = StormEvent('florence', 2018)
storm.track(file_deck='b')
```

```
VortexTrack('AL062018', Timestamp('2018-08-30 06:00:00'), Timestamp('2018-09-18 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', None)
```

##### high-water mark (HWM) surveys provided by the United States Geological Survey (USGS)

```python
from stormevents import StormEvent

storm = StormEvent('florence', 2018)
storm.high_water_marks
```

```
         latitude  longitude  ... siteZone                    geometry
hwm_id                        ...                                     
33496   37.298440 -80.007750  ...      NaN  POINT (-80.00775 37.29844)
33502   35.342089 -78.041553  ...      NaN  POINT (-78.04155 35.34209)
33503   35.378963 -78.010596  ...      NaN  POINT (-78.01060 35.37896)
33505   35.216282 -78.935229  ...      NaN  POINT (-78.93523 35.21628)
33508   35.199859 -78.960296  ...      NaN  POINT (-78.96030 35.19986)
           ...        ...  ...      ...                         ...
34191   33.724722 -79.059722  ...      NaN  POINT (-79.05972 33.72472)
34235   34.936308 -76.811223  ...           POINT (-76.81122 34.93631)
34840   34.145930 -78.868567  ...      NaN  POINT (-78.86857 34.14593)
34871   35.424707 -77.593860  ...      NaN  POINT (-77.59386 35.42471)
34876   35.301135 -77.264727  ...      NaN  POINT (-77.26473 35.30114)

[509 rows x 52 columns]
```

##### products from the Center for Operational Oceanographic Products and Services (CO-OPS)

```python

from stormevents import StormEvent

storm = StormEvent('florence', 2018)
storm.coops_product_within_isotach('water_level', wind_speed=34, start_date='2018-09-12 14:03:00', end_date='2018-09-14')
```

```
<xarray.Dataset>
Dimensions:  (nos_id: 7, t: 340)
Coordinates:
  * nos_id   (nos_id) int64 8651370 8652587 8654467 ... 8658120 8658163 8661070
  * t        (t) datetime64[ns] 2018-09-12T14:06:00 ... 2018-09-14
    nws_id   (nos_id) <U5 'DUKN7' 'ORIN7' 'HCGN7' ... 'WLON7' 'JMPN7' 'MROS1'
    x        (nos_id) float64 -75.75 -75.56 -75.69 -76.69 -77.94 -77.81 -78.94
    y        (nos_id) float64 36.19 35.78 35.22 34.72 34.22 34.22 33.66
Data variables:
    v        (nos_id, t) float32 7.181 7.199 7.144 7.156 ... 9.6 9.634 9.686
    s        (nos_id, t) float32 0.317 0.36 0.31 0.318 ... 0.049 0.047 0.054
    f        (nos_id, t) object '0,0,0,0' '0,0,0,0' ... '0,0,0,0' '0,0,0,0'
    q        (nos_id, t) object 'v' 'v' 'v' 'v' 'v' 'v' ... 'v' 'v' 'v' 'v' 'v'
```

## Related Projects

- `searvey` - https://github.com/oceanmodeling/searvey
- `pyStorms` - https://github.com/brey/pyStorms
- `tropycal` - https://tropycal.github.io/tropycal/index.html
- `pyoos` - https://github.com/ioos/pyoos
- `csdllib` - https://github.com/noaa-ocs-modeling/csdllib
- `pyPoseidon` - https://github.com/ec-jrc/pyPoseidon
- `Thalassa` - https://github.com/ec-jrc/Thalassa
- `adcircpy` - https://github.com/noaa-ocs-modeling/adcircpy

## Acknowledgements

Original methodology for retrieving NHC storm tracks and CO-OPS tidal data was written
by [@jreniel](https://github.com/jreniel) for [`adcircpy`](https://github.com/noaa-ocs-modeling/adcircpy).

Original methodology for retrieving USGS high-water mark surveys and CO-OPS tidal station metadata was written
by [@moghimis](https://github.com/moghimis) and [@grapesh](https://github.com/grapesh)
for [`csdllib`](https://github.com/noaa-ocs-modeling/csdllib).
