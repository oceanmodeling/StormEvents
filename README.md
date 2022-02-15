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

### `StormEvent`

#### instantiate from NHC storm name and year

```python
from stormevents import StormEvent

StormEvent('florence', 2018)
```

```
StormEvent('FLORENCE', 2018)
```

#### instantiate from NHC storm code

```python
from stormevents import StormEvent

StormEvent.from_nhc_code('EP172016')
```

```
StormEvent('PAINE', 2016)
```

#### instantiate from USGS flood event ID

```python
from stormevents import StormEvent

StormEvent.from_usgs_id(310)
```

```
StormEvent('HENRI', 2021)
```

#### constrain time interval to an absolute range

```python
from stormevents import StormEvent
from datetime import datetime

StormEvent('paine', 2016, start_date='2016-09-18', end_date=datetime(2016, 9, 19, 12))
```

```
StormEvent('PAINE', 2016, end_date='2016-09-19 12:00:00')
```

#### constrain time interval to relative times (compared to storm start and end times provided by the NHC)

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
StormEvent('HENRI', 2021, start_date='2021-08-24 18:00:00', end_date='2021-08-25 18:00:00')
```

```python
from stormevents import StormEvent
from datetime import timedelta

StormEvent('ida', 2021, end_date=timedelta(days=2))  # <- end 2 days after NHC start time 
```

```
StormEvent('IDA', 2021, end_date='2021-08-29 18:00:00')
```


#### retrieve storm track data from the National Hurricane Center (NHC)

```python
from stormevents import StormEvent

florence2018 = StormEvent('florence', 2018)

florence2018.track()
```

```
VortexTrack('AL062018', Timestamp('2018-08-30 06:00:00'), Timestamp('2018-09-18 12:00:00'), <ATCF_FileDeck.a: 'a'>, <ATCF_Mode.historical: 'ARCHIVE'>, None, None)
```

```python
from stormevents import StormEvent

florence2018 = StormEvent('florence', 2018)

florence2018.track(file_deck='b')
```

```
VortexTrack('AL062018', Timestamp('2018-08-30 06:00:00'), Timestamp('2018-09-18 12:00:00'), <ATCF_FileDeck.b: 'b'>, <ATCF_Mode.historical: 'ARCHIVE'>, 'BEST', None)
```

#### retrieve high-water mark surveys conducted provided by the United States Geological Survey (USGS)

```python
from stormevents import StormEvent

florence2018 = StormEvent('florence', 2018)

florence2018.high_water_marks
```

```
         latitude  ...  siteZone
hwm_id             ...          
33496   37.298440  ...       NaN
33502   35.342089  ...       NaN
33503   35.378963  ...       NaN
33505   35.216282  ...       NaN
33508   35.199859  ...       NaN
  ...         ...  ...       ...
34191   33.724722  ...       NaN
34235   34.936308  ...          
34840   34.145930  ...       NaN
34871   35.424707  ...       NaN
34876   35.301135  ...       NaN

[509 rows x 51 columns]
```

##### retrieve water level products from tidal buoys maintained by the National Oceanic and Atmospheric Administration (NOAA) Center for Operational Oceanographic Products and Services (CO-OPS)

```python

from stormevents import StormEvent

florence2018 = StormEvent('florence', 2018)

florence2018.tidal_data_within_isotach(
    wind_speed=34,
    start_date='20180913230000',
    end_date='20180914',
)
```

```
Dimensions:  (nos_id: 10, t: 11)
Coordinates:
  * t        (t) datetime64[ns] 2018-09-13T23:00:00 ... 2018-09-14
  * nos_id   (nos_id) int64 8639348 8651370 8652587 ... 8661070 8662245 8665530
    nws_id   (nos_id) <U5 'MNPV2' 'DUKN7' 'ORIN7' ... 'MROS1' 'NITS1' 'CHTS1'
    x        (nos_id) float64 -76.31 -75.75 -75.56 ... -78.94 -79.19 -79.94
    y        (nos_id) float64 36.78 36.19 35.78 35.22 ... 33.66 33.34 32.78
Data variables:
    v        (nos_id, t) float32 7.271 7.274 7.27 7.27 ... 1.549 1.587 1.624
    s        (nos_id, t) float32 0.005 0.004 0.005 0.004 ... 0.005 0.007 0.006
    f        (nos_id, t) object '0,0,0,0' '0,0,0,0' ... '0,0,0,0' '0,0,0,0'
    q        (nos_id, t) object 'v' 'v' 'v' 'v' 'v' 'v' ... 'v' 'v' 'v' 'v' 'v'
```

## Related Projects

- `searvey` - https://github.com/pmav99/searvey
- `pyStorms` - https://github.com/brey/pyStorms
- `tropycal` - https://tropycal.github.io/tropycal/index.html
- `pyoos` - https://github.com/ioos/pyoos
- `csdllib` - https://github.com/noaa-ocs-modeling/csdllib
- `pyPoseidon` - https://github.com/ec-jrc/pyPoseidon
- `Thalassa` - https://github.com/ec-jrc/Thalassa
- `adcircpy` - https://github.com/zacharyburnettNOAA/adcircpy

## Acknowledgements

This code was initially written by [@jreniel](https://github.com/jreniel)
for `adcircpy`. Additionally, methodology for retrieving USGS high water marks data and CO-OPS tidal station data came
from [@moghimis](https://github.com/moghimis) and @Sergey.Vinogradov
