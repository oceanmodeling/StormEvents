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

VortexTrack.from_storm_name('irma', 2017)
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

[10744 rows x 22 columns]
```

##### read storm track from file

If you have an ATCF or `fort.22` file, use the corresponding methods:

```python
from stormevents.nhc import VortexTrack

VortexTrack.from_file('tests/data/input/test_from_atcf/atcf.trk')
```

```
VortexTrack('BT02008', Timestamp('2008-10-16 17:06:00'), Timestamp('2008-10-20 20:06:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', 'tests/data/input/test_from_atcf/atcf.trk')
```

```python
from stormevents.nhc import VortexTrack

VortexTrack.from_fort22('tests/data/input/test_from_fort22/irma2017_fort.22')
```

```
VortexTrack('AL112017', Timestamp('2017-09-05 00:00:00'), Timestamp('2017-09-19 00:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', 'tests/data/input/test_from_fort22/irma2017_fort.22')
```

##### write storm track to `fort.22` file

```python
from stormevents.nhc import VortexTrack

track = VortexTrack.from_storm_name('florence', 2018)
track.to_file('fort.22')
```

#### high-water mark (HWM) surveys provided by the United States Geological Survey (USGS)

The [United States Geological Survey (USGS)](https://www.usgs.gov)
conducts surveys of flooded areas following flood events to determine the highest level of water elevation, and provides the
results of these surveys via their API.

##### list flood events defined by the USGS that have HWM surveys

```python
from stormevents.usgs import usgs_flood_events

usgs_flood_events()
```

```
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
```

##### retrieve HWM survey data for any flood event

```python
from stormevents.usgs import USGS_Event

flood = USGS_Event(182)
flood.high_water_marks()
```

```
         latitude  longitude            eventName  ...                                          hwm_notes siteZone                    geometry
hwm_id                                             ...                                                                                        
22602   31.170642 -81.428402  Irma September 2017  ...                                                NaN      NaN  POINT (-81.42840 31.17064)
22605   31.453850 -81.362853  Irma September 2017  ...                                                NaN      NaN  POINT (-81.36285 31.45385)
22612   30.720000 -81.549440  Irma September 2017  ...  There is a secondary peak around 5.5 ft, so th...      NaN  POINT (-81.54944 30.72000)
22636   32.007730 -81.238270  Irma September 2017  ...  Trimble R8 used to establish TBM. Levels ran f...      NaN  POINT (-81.23827 32.00773)
22653   31.531078 -81.358894  Irma September 2017  ...                                                NaN      NaN  POINT (-81.35889 31.53108)
...           ...        ...                  ...  ...                                                ...      ...                         ...
26171   18.470402 -66.246631  Irma September 2017  ...                                                NaN      NaN  POINT (-66.24663 18.47040)
26173   18.470300 -66.449900  Irma September 2017  ...                                levels from GNSS BM      NaN  POINT (-66.44990 18.47030)
26175   18.463954 -66.140869  Irma September 2017  ...                                levels from GNSS BM      NaN  POINT (-66.14087 18.46395)
26177   18.488720 -66.392160  Irma September 2017  ...                                levels from GNSS BM      NaN  POINT (-66.39216 18.48872)
26179   18.005607 -65.871768  Irma September 2017  ...                                levels from GNSS BM      NaN  POINT (-65.87177 18.00561)

[506 rows x 53 columns]
```

```python
from stormevents.usgs import USGS_Event

flood = USGS_Event(182)
flood.high_water_marks(quality=['EXCELLENT', 'GOOD'])
```

```
         latitude  longitude            eventName  ...                                          hwm_notes siteZone                    geometry
hwm_id                                             ...                                                                                        
22602   31.170642 -81.428402  Irma September 2017  ...                                                NaN      NaN  POINT (-81.42840 31.17064)
22605   31.453850 -81.362853  Irma September 2017  ...                                                NaN      NaN  POINT (-81.36285 31.45385)
22612   30.720000 -81.549440  Irma September 2017  ...  There is a secondary peak around 5.5 ft, so th...      NaN  POINT (-81.54944 30.72000)
22636   32.007730 -81.238270  Irma September 2017  ...  Trimble R8 used to establish TBM. Levels ran f...      NaN  POINT (-81.23827 32.00773)
22653   31.531078 -81.358894  Irma September 2017  ...                                                NaN      NaN  POINT (-81.35889 31.53108)
...           ...        ...                  ...  ...                                                ...      ...                         ...
26171   18.470402 -66.246631  Irma September 2017  ...                                                NaN      NaN  POINT (-66.24663 18.47040)
26173   18.470300 -66.449900  Irma September 2017  ...                                levels from GNSS BM      NaN  POINT (-66.44990 18.47030)
26175   18.463954 -66.140869  Irma September 2017  ...                                levels from GNSS BM      NaN  POINT (-66.14087 18.46395)
26177   18.488720 -66.392160  Irma September 2017  ...                                levels from GNSS BM      NaN  POINT (-66.39216 18.48872)
26179   18.005607 -65.871768  Irma September 2017  ...                                levels from GNSS BM      NaN  POINT (-65.87177 18.00561)

[506 rows x 53 columns]
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
        nws_id                              name state        status                                            removed                     geometry
nos_id
1600012  46125                         QREB buoy              active                                               <NA>   POINT (122.62500 37.75000)
8735180  DILA1                    Dauphin Island    AL        active  2019-07-18 10:00:00,2018-07-30 16:40:00,2017-0...   POINT (-88.06250 30.25000)
8557380  LWSD1                             Lewes    DE        active  2019-08-01 00:00:00,2018-06-18 00:00:00,2017-0...   POINT (-75.12500 38.78125)
8465705  NWHC3                         New Haven    CT        active  2019-08-18 14:55:00,2019-08-18 14:54:00,2018-0...   POINT (-72.93750 41.28125)
9439099  WAUO3                             Wauna    OR        active  2019-08-19 22:59:00,2014-06-20 21:30:00,2013-0...  POINT (-123.43750 46.15625)
...        ...                               ...   ...           ...                                                ...                          ...
8448725  MSHM3               Menemsha Harbor, MA    MA  discontinued  2013-09-26 23:59:00,2013-09-26 00:00:00,2012-0...   POINT (-70.75000 41.34375)
8538886  TPBN4             Tacony-Palmyra Bridge    NJ  discontinued  2013-11-11 00:01:00,2013-11-11 00:00:00,2012-0...   POINT (-75.06250 40.00000)
9439011  HMDO3                           Hammond    OR  discontinued  2014-08-13 00:00:00,2011-04-12 23:59:00,2011-0...  POINT (-123.93750 46.18750)
8762372  LABL1  East Bank 1, Norco, B. LaBranche    LA  discontinued  2012-11-05 10:38:00,2012-11-05 10:37:00,2012-1...   POINT (-90.37500 30.04688)
8530528  CARN4       CARLSTADT, HACKENSACK RIVER    NJ  discontinued            1994-11-12 23:59:00,1994-11-12 00:00:00   POINT (-74.06250 40.81250)

[433 rows x 6 columns]
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

##### retrieve CO-OPS data product for a specific station

```python
from datetime import datetime
from stormevents.coops import COOPS_Station

station = COOPS_Station(8632200)
station.product('water_level', start_date=datetime(2018, 9, 13), end_date=datetime(2018, 9, 16, 12))
```

```
<xarray.Dataset>
Dimensions:  (nos_id: 1, t: 841)
Coordinates:
  * nos_id   (nos_id) int64 8632200
  * t        (t) datetime64[ns] 2018-09-13 ... 2018-09-16T12:00:00
    nws_id   (nos_id) <U5 'KPTV2'
    x        (nos_id) float64 -76.0
    y        (nos_id) float64 37.16
Data variables:
    v        (nos_id, t) float32 1.67 1.694 1.73 1.751 ... 1.597 1.607 1.605
    s        (nos_id, t) float32 0.026 0.027 0.034 0.03 ... 0.018 0.019 0.021
    f        (nos_id, t) object '0,0,0,0' '0,0,0,0' ... '0,0,0,0' '0,0,0,0'
    q        (nos_id, t) object 'v' 'v' 'v' 'v' 'v' 'v' ... 'v' 'v' 'v' 'v' 'v'
```

##### retrieve CO-OPS data product from within a region and time interval

To retrieve data, you must provide three things:

1. the **data product** of interest; one of
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
2. a **region** within which to retrieve the data product
3. a **time interval** within which to retrieve the data product

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
Dimensions:  (nos_id: 10, t: 11)
Coordinates:
  * nos_id   (nos_id) int64 8651370 8652587 8654467 ... 8662245 8665530 8670870
  * t        (t) datetime64[ns] 2022-03-08T14:48:00 ... 2022-03-08T15:48:00
    nws_id   (nos_id) <U5 'DUKN7' 'ORIN7' 'HCGN7' ... 'NITS1' 'CHTS1' 'FPKG1'
    x        (nos_id) float64 -75.75 -75.56 -75.69 ... -79.19 -79.94 -80.88
    y        (nos_id) float64 36.19 35.78 35.22 34.72 ... 33.34 32.78 32.03
Data variables:
    v        (nos_id, t) float32 6.256 6.304 6.361 6.375 ... 2.633 2.659 2.686
    s        (nos_id, t) float32 0.107 0.097 0.127 0.122 ... 0.005 0.004 0.004
    f        (nos_id, t) object '1,0,0,0' '1,0,0,0' ... '1,0,0,0' '1,0,0,0'
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
StormEvent('HENRI', 2021, end_date='2021-08-24 12:00:00')
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
storm.track(file_deck='a')
```

```
VortexTrack('AL062018', Timestamp('2018-08-30 06:00:00'), Timestamp('2018-09-18 12:00:00'), <ATCF_FileDeck.ADVISORY: 'a'>, <ATCF_Mode.historical: 'ARCHIVE'>, None, None)
```

##### high-water mark (HWM) surveys provided by the United States Geological Survey (USGS)

```python
from stormevents import StormEvent

storm = StormEvent('florence', 2018)
flood = storm.flood_event
flood.high_water_marks()
```

```
         latitude  longitude          eventName  ... siteZone peak_summary_id                    geometry
hwm_id                                           ...                                                     
33496   37.298440 -80.007750  Florence Sep 2018  ...      NaN             NaN  POINT (-80.00775 37.29844)
33497   33.699720 -78.936940  Florence Sep 2018  ...      NaN             NaN  POINT (-78.93694 33.69972)
33498   33.758610 -78.792780  Florence Sep 2018  ...      NaN             NaN  POINT (-78.79278 33.75861)
33499   33.641389 -78.947778  Florence Sep 2018  ...                      NaN  POINT (-78.94778 33.64139)
33500   33.602500 -78.973889  Florence Sep 2018  ...                      NaN  POINT (-78.97389 33.60250)
...           ...        ...                ...  ...      ...             ...                         ...
34872   35.534641 -77.038183  Florence Sep 2018  ...      NaN             NaN  POINT (-77.03818 35.53464)
34873   35.125000 -77.050044  Florence Sep 2018  ...      NaN             NaN  POINT (-77.05004 35.12500)
34874   35.917467 -76.254367  Florence Sep 2018  ...      NaN             NaN  POINT (-76.25437 35.91747)
34875   35.111000 -77.037851  Florence Sep 2018  ...      NaN             NaN  POINT (-77.03785 35.11100)
34876   35.301135 -77.264727  Florence Sep 2018  ...      NaN             NaN  POINT (-77.26473 35.30114)

[644 rows x 53 columns]
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
