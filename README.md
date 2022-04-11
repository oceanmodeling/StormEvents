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
CP902021      INVEST    LO  2021    CP      90  METWATCH 2021-07-24 12:00:00                 NaT
CP912021      INVEST    DB  2021    CP      91  METWATCH 2021-08-07 18:00:00                 NaT
EP922021      INVEST    DB  2021    EP      92  METWATCH 2021-06-05 06:00:00                 NaT
EP712022  GENESIS001    DB  2022    EP      71   GENESIS 2022-01-20 12:00:00                 NaT
EP902022      INVEST    LO  2022    EP      90  METWATCH 2022-01-20 12:00:00                 NaT

[2714 rows x 8 columns]
```

##### retrieve storm track by NHC code

```python
from stormevents.nhc import VortexTrack

track = VortexTrack('AL112017')
track.data
```

```
    basin storm_number            datetime advisory_number  ... isowave_radius_for_SWQ extra_values                    geometry  track_start_time
0      AL           11 2017-08-30 00:00:00                  ...                    NaN         <NA>  POINT (-26.90000 16.10000)        2017-08-30
1      AL           11 2017-08-30 06:00:00                  ...                    NaN         <NA>  POINT (-28.30000 16.20000)        2017-08-30
2      AL           11 2017-08-30 12:00:00                  ...                    NaN         <NA>  POINT (-29.70000 16.30000)        2017-08-30
3      AL           11 2017-08-30 18:00:00                  ...                    NaN         <NA>  POINT (-30.80000 16.30000)        2017-08-30
4      AL           11 2017-08-30 18:00:00                  ...                    NaN         <NA>  POINT (-30.80000 16.30000)        2017-08-30
..    ...          ...                 ...             ...  ...                    ...          ...                         ...               ...
168    AL           11 2017-09-12 12:00:00                  ...                    NaN         <NA>  POINT (-86.90000 33.80000)        2017-08-30
169    AL           11 2017-09-12 18:00:00                  ...                    NaN         <NA>  POINT (-88.10000 34.80000)        2017-08-30
170    AL           11 2017-09-13 00:00:00                  ...                    NaN         <NA>  POINT (-88.90000 35.60000)        2017-08-30
171    AL           11 2017-09-13 06:00:00                  ...                    NaN         <NA>  POINT (-89.50000 36.20000)        2017-08-30
172    AL           11 2017-09-13 12:00:00                  ...                    NaN         <NA>  POINT (-90.10000 36.80000)        2017-08-30

[173 rows x 38 columns]
```

##### retrieve storm track by name and year

If you do not know the storm code, you can input the storm name and year:

```python
from stormevents.nhc import VortexTrack

VortexTrack.from_storm_name('irma', 2017)
```

```
VortexTrack('AL112017', Timestamp('2017-08-30 00:00:00'), Timestamp('2017-09-13 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, [<ATCF_Advisory.BEST: 'BEST'>], None)
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
      basin storm_number            datetime advisory_number  ... isowave_radius_for_SWQ extra_values                    geometry    track_start_time
0        AL           11 2017-08-27 06:00:00              01  ...                    NaN         <NA>  POINT (-17.40000 11.70000) 2017-08-28 06:00:00
1        AL           11 2017-08-27 12:00:00              01  ...                    NaN         <NA>  POINT (-17.90000 11.80000) 2017-08-28 06:00:00
2        AL           11 2017-08-27 18:00:00              01  ...                    NaN         <NA>  POINT (-18.40000 11.90000) 2017-08-28 06:00:00
3        AL           11 2017-08-28 00:00:00              01  ...                    NaN         <NA>  POINT (-19.00000 12.00000) 2017-08-28 06:00:00
4        AL           11 2017-08-28 06:00:00              01  ...                    NaN         <NA>  POINT (-19.50000 12.00000) 2017-08-28 06:00:00
...     ...          ...                 ...             ...  ...                    ...          ...                         ...                 ...
10739    AL           11 2017-09-12 00:00:00              03  ...                    NaN         <NA>  POINT (-84.40000 31.90000) 2017-09-12 00:00:00
10740    AL           11 2017-09-12 03:00:00              03  ...                    NaN         <NA>  POINT (-84.90000 32.40000) 2017-09-12 00:00:00
10741    AL           11 2017-09-12 12:00:00              03  ...                    NaN         <NA>  POINT (-86.40000 33.80000) 2017-09-12 00:00:00
10742    AL           11 2017-09-13 00:00:00              03  ...                    NaN         <NA>  POINT (-88.20000 35.20000) 2017-09-12 00:00:00
10743    AL           11 2017-09-13 12:00:00              03  ...                    NaN         <NA>  POINT (-88.60000 36.40000) 2017-09-12 00:00:00

[10434 rows x 38 columns]
```

##### read storm track from file

If you have an ATCF or `fort.22` file, use the corresponding methods:

```python
from stormevents.nhc import VortexTrack

VortexTrack.from_file('tests/data/input/test_vortex_track_from_file/AL062018.dat')
```

```
VortexTrack('AL062018', Timestamp('2018-08-30 06:00:00'), Timestamp('2018-09-18 12:00:00'), None, <ATCF_Mode.HISTORICAL: 'ARCHIVE'>, ['BEST', 'OFCL', 'OFCP', 'HMON', 'CARQ', 'HWRF'], PosixPath('/home/zrb/Projects/StormEvents/tests/data/input/test_vortex_track_from_file/AL062018.dat'))
```

```python
from stormevents.nhc import VortexTrack

VortexTrack.from_file('tests/data/input/test_vortex_track_from_file/irma2017_fort.22')
```

```
VortexTrack('AL112017', Timestamp('2017-09-05 00:00:00'), Timestamp('2017-09-12 00:00:00'), None, <ATCF_Mode.HISTORICAL: 'ARCHIVE'>, ['BEST', 'OFCL', 'OFCP', 'HMON', 'CARQ', 'HWRF'], PosixPath('/home/zrb/Projects/StormEvents/tests/data/input/test_vortex_track_from_file/irma2017_fort.22'))
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
                                            name  year                                        description  ... last_updated_by          start_date            end_date
usgs_id                                                                                                    ...
7                             FEMA 2013 exercise  2013                   Ardent/Sentry 2013 FEMA Exercise  ...             NaN 2013-05-15 04:00:00 2013-05-23 04:00:00
8                                          Wilma  2005  Category 3 in west FL. \nHurricane Wilma was t...  ...             NaN 2005-10-20 00:00:00 2005-10-31 00:00:00
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
```

##### retrieve HWM survey data for any flood event

```python
from stormevents.usgs import USGS_Event

flood = USGS_Event(182)
flood.high_water_marks()
```

```
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
```

```python
from stormevents.usgs import USGS_Event

flood = USGS_Event(182)
flood.high_water_marks(quality=['EXCELLENT', 'GOOD'])
```

```
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
        nws_id                         name state        status                                            removed                      geometry
nos_id
1600012  46125                    QREB buoy              active                                               <NA>    POINT (122.62500 37.75000)
1619910  SNDP5  Sand Island, Midway Islands              active                                               <NA>   POINT (-177.37500 28.21875)
1630000  APRP7            Apra Harbor, Guam              active                                               <NA>    POINT (144.62500 13.44531)
1631428  PGBP7               Pago Bay, Guam              active                                               <NA>    POINT (144.75000 13.42969)
1770000  NSTP6    Pago Pago, American Samoa              active                                               <NA>  POINT (-170.75000 -14.27344)
...        ...                          ...   ...           ...                                                ...                           ...
8423898  FTPN3                   Fort Point    NH  discontinued  2020-04-13 00:00:00,2014-08-05 00:00:00,2012-0...    POINT (-70.68750 43.06250)
8726667  MCYF1           Mckay Bay Entrance    FL  discontinued  2020-05-20 00:00:00,2019-03-08 00:00:00,2017-0...    POINT (-82.43750 27.90625)
8772447  FCGT2                     Freeport    TX  discontinued  2020-05-24 18:45:00,2018-10-10 21:50:00,2018-1...    POINT (-95.31250 28.93750)
9087079  GBWW3                    Green Bay    WI  discontinued  2020-10-28 13:00:00,2007-08-06 23:59:00,2007-0...    POINT (-88.00000 44.53125)
8770570  SBPT2            Sabine Pass North    TX  discontinued  2021-01-18 00:00:00,2020-09-30 15:45:00,2020-0...    POINT (-93.87500 29.73438)

[435 rows x 6 columns]
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
StormEvent(name='FLORENCE', year=2018, start_date=Timestamp('2018-08-30 06:00:00'), end_date=Timestamp('2018-09-18 12:00:00'))
```

or from a storm NHC code,

```python
from stormevents import StormEvent

StormEvent.from_nhc_code('EP172016')
```

```
StormEvent(name='PAINE', year=2016, start_date=Timestamp('2016-09-18 00:00:00'), end_date=Timestamp('2016-09-21 12:00:00'))
```

or from a USGS flood event ID.

```python
from stormevents import StormEvent

StormEvent.from_usgs_id(310)
```

```
StormEvent(name='HENRI', year=2021, start_date=Timestamp('2021-08-20 18:00:00'), end_date=Timestamp('2021-08-24 12:00:00'))
```

To constrain the time interval, you can provide an absolute time range,

```python
from stormevents import StormEvent
from datetime import datetime

StormEvent('paine', 2016, start_date='2016-09-19', end_date=datetime(2016, 9, 19, 12))
```

```
StormEvent(name='PAINE', year=2016, start_date=datetime.datetime(2016, 9, 19, 0, 0), end_date=datetime.datetime(2016, 9, 19, 12, 0))
```

```python
from stormevents import StormEvent
from datetime import datetime

StormEvent('paine', 2016, end_date=datetime(2016, 9, 19, 12))
```

```
StormEvent(name='PAINE', year=2016, start_date=Timestamp('2016-09-18 00:00:00'), end_date=datetime.datetime(2016, 9, 19, 12, 0))
```

or, alternatively, you can provide relative time deltas, which will be interpreted compared to the absolute time interval
provided by the NHC.

```python
from stormevents import StormEvent
from datetime import timedelta

StormEvent('florence', 2018, start_date=timedelta(days=2))  # <- start 2 days after NHC start time
```

```
StormEvent(name='FLORENCE', year=2018, start_date=Timestamp('2018-09-01 06:00:00'), end_date=Timestamp('2018-09-18 12:00:00'))
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
StormEvent(name='HENRI', year=2021, start_date=Timestamp('2021-08-21 12:00:00'), end_date=Timestamp('2021-08-22 12:00:00'))
```

```python
from stormevents import StormEvent
from datetime import timedelta

StormEvent('ida', 2021, end_date=timedelta(days=2))  # <- end 2 days after NHC start time 
```

```
StormEvent(name='IDA', year=2021, start_date=Timestamp('2021-08-27 18:00:00'), end_date=Timestamp('2021-08-29 18:00:00'))
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
VortexTrack('AL062018', Timestamp('2018-08-30 06:00:00'), Timestamp('2018-09-18 12:00:00'), <ATCF_FileDeck.BEST: 'b'>, <ATCF_Mode.HISTORICAL: 'ARCHIVE'>, [<ATCF_Advisory.BEST: 'BEST'>], None)
```

```python
from stormevents import StormEvent

storm = StormEvent('florence', 2018)
storm.track(file_deck='a')
```

```
VortexTrack('AL062018', Timestamp('2018-08-30 06:00:00'), Timestamp('2018-09-18 12:00:00'), <ATCF_FileDeck.ADVISORY: 'a'>, <ATCF_Mode.HISTORICAL: 'ARCHIVE'>, ['OFCL', 'OFCP', 'HMON', 'CARQ', 'HWRF'], None)
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
