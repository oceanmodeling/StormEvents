# StormEvents

[![tests](https://github.com/zacharyburnettNOAA/StormEvents/workflows/tests/badge.svg)](https://github.com/zacharyburnettNOAA/StormEvents/actions?query=workflow%3Atests)
[![build](https://github.com/zacharyburnettNOAA/StormEvents/workflows/build/badge.svg)](https://github.com/zacharyburnettNOAA/StormEvents/actions?query=workflow%3Abuild)
[![codecov](https://codecov.io/gh/zacharyburnettNOAA/StormEvents/branch/main/graph/badge.svg?token=BQWB1QKJ3Q)](https://codecov.io/gh/zacharyburnettNOAA/StormEvents)
[![version](https://img.shields.io/pypi/v/StormEvents)](https://pypi.org/project/StormEvents)
[![license](https://img.shields.io/github/license/zacharyburnettNOAA/StormEvents)](https://opensource.org/licenses/gpl-license)
[![style](https://sourceforge.net/p/oitnb/code/ci/default/tree/_doc/_static/oitnb.svg?format=raw)](https://sourceforge.net/p/oitnb/code)

`stormevents` provides Python interfaces for observational data surrounding named storm events.

## Usage

### storm interface

you can instantiate a new `StormEvent` object from the NHC storm name and year
(i.e. `FLORENCE 2018`, the NHC storm code (i.e. `AL062018`), or the USGS flood event ID (i.e. `304`).

```python
from stormevents import StormEvent

florence2018 = StormEvent('florence', 2018)
paine2016 = StormEvent.from_nhc_code('EP172016')
sally2020 = StormEvent.from_usgs_id(304)
```

you can then retrieve track data from NHC, high-water mark data from USGS, and water level products from CO-OPS for this storm

by default, these functions operate within the time interval defined by the NHC best track

```python
from stormevents import StormEvent

florence2018 = StormEvent('florence', 2018)

track = florence2018.track()
high_water_marks = florence2018.high_water_marks()
water_levels = florence2018.tidal_data_within_isotach(isotach=34)
```

### vortex tracks from the National Hurricane Center (NHC)

#### list storm events defined by the NHC since 2008

```python
from stormevents.nhc import nhc_storms

nhc_storms = nhc_storms()
```

```
               name                 long_name  year
nhc_code                                                 
al012008     ARTHUR     Tropical Storm ARTHUR  2008
al022008     BERTHA          Hurricane BERTHA  2008
al032008  CRISTOBAL  Tropical Storm CRISTOBAL  2008
al042008      DOLLY           Hurricane DOLLY  2008
al052008    EDOUARD    Tropical Storm EDOUARD  2008
...             ...                       ...   ...
ep152021       OLAF            Hurricane OLAF  2021
ep162021     PAMELA          Hurricane PAMELA  2021
ep172021       RICK            Hurricane RICK  2021
ep182021      TERRY      Tropical Storm TERRY  2021
ep192021     SANDRA     Tropical Storm SANDRA  2021

[523 rows x 3 columns]
```

#### retrieve spatial storm tracks provided by the NHC

```python
from stormevents.nhc import VortexTrack

# retrieve vortex data from the Internet from its ID
vortex = VortexTrack('AL112017')

# you can also use the storm name and year in the lookup
vortex = VortexTrack('irma2017')

# write to a file in the ADCIRC `fort.22` format
vortex.write('fort.22')

# read vortex data from an existing ATCF track file (`*.trk`)
vortex = VortexTrack.from_atcf_file('atcf.trk')

# read vortex data from an existing file in the ADCIRC `fort.22` format
vortex = VortexTrack.from_fort22('fort.22')
```

### high water mark (HWM) surveys from the United States Geological Survey (USGS)

#### list storm flood events that have HWM surveys

```python
from stormevents.usgs import usgs_highwatermark_storms

hwm_storms = usgs_highwatermark_storms()
```

```
         year                         usgs_name  nhc_name  nhc_code
usgs_id                                                            
7        2013                FEMA 2013 exercise      None      None
8        2013                             Wilma      None      None
18       2012                    Isaac Aug 2012     ISAAC  al092012
19       2005                              Rita      None      None
23       2011                             Irene     IRENE  al092011
...       ...                               ...       ...       ...
303      2020  2020 TS Marco - Hurricane  Laura     MARCO  al142020
304      2020              2020 Hurricane Sally     SALLY  al192020
305      2020              2020 Hurricane Delta     DELTA  al262020
310      2021       2021 Tropical Cyclone Henri     HENRI  al082021
312      2021         2021 Tropical Cyclone Ida       IDA  al092021

[24 rows x 3 columns]
```

#### retrieve HWM data for a specific storm

```python
from stormevents.usgs import StormHighWaterMarks

hwm_florence2018 = StormHighWaterMarks('florence', 2018)

hwm_florence2018.data
hwm_florence2018.data.columns
```

```
         latitude  ...  siteZone
hwm_id             ...          
33496   37.298440  ...       NaN
33502   35.342089  ...       NaN
33503   35.378963  ...       NaN
33505   35.216282  ...       NaN
33508   35.199859  ...       NaN
...           ...  ...       ...
34191   33.724722  ...       NaN
34235   34.936308  ...          
34840   34.145930  ...       NaN
34871   35.424707  ...       NaN
34876   35.301135  ...       NaN

[509 rows x 51 columns]
```

```
Index(['latitude', 'longitude', 'eventName', 'hwmTypeName', 'hwmQualityName',
       'verticalDatumName', 'verticalMethodName', 'approvalMember',
       'markerName', 'horizontalMethodName', 'horizontalDatumName',
       'flagMemberName', 'surveyMemberName', 'site_no', 'siteDescription',
       'sitePriorityName', 'networkNames', 'stateName', 'countyName',
       'sitePermHousing', 'site_latitude', 'site_longitude', 'waterbody',
       'site_id', 'event_id', 'hwm_type_id', 'hwm_quality_id',
       'hwm_locationdescription', 'latitude_dd', 'longitude_dd', 'survey_date',
       'elev_ft', 'vdatum_id', 'vcollect_method_id', 'bank', 'marker_id',
       'hcollect_method_id', 'hwm_environment', 'flag_date', 'stillwater',
       'hdatum_id', 'flag_member_id', 'survey_member_id', 'uncertainty',
       'hwm_uncertainty', 'hwm_label', 'files', 'approval_id',
       'height_above_gnd', 'hwm_notes', 'siteZone'],
      dtype='object')
```

### tidal station data from the Center for Operational Oceanographic Products and Services (CO-OPS)

#### list CO-OPS tidal stations

```python
from stormevents.coops import coops_stations

stations = coops_stations()
```

```
        NWS ID  Latitude  ...                   Station Name   Removed Date/Time
NOS ID                    ...                                                   
1600012  46125  37.75008  ...                      QREB buoy                 NaT
1611400  NWWH1  21.95440  ...                     Nawiliwili                 NaT
1612340  OOUH1  21.30669  ...                       Honolulu                 NaT
1612480  MOKH1  21.43306  ...                       Mokuoloe                 NaT
1615680  KLIH1  20.89500  ...        Kahului, Kahului Harbor                 NaT
    ...    ...       ...  ...                            ...                 ...
8637689  YKTV2  37.22650  ...  Yorktown USCG Training Center 2010-09-13 13:00:00
8637689  YKTV2  37.22650  ...  Yorktown USCG Training Center 2015-08-20 00:00:00
8637689  YKTV2  37.22650  ...  Yorktown USCG Training Center 2014-12-12 15:29:00
9414458  ZSMC1  37.58000  ...               San Mateo Bridge 2005-04-05 00:00:00
9414458  ZSMC1  37.58000  ...               San Mateo Bridge 2005-04-05 23:59:00

[7877 rows x 6 columns]
```

#### list CO-OPS tidal stations within a region

```python
from shapely.geometry import Polygon
from stormevents.coops import coops_stations_within_region

polygon = Polygon(...)

stations = coops_stations_within_region(region=polygon)
```

#### retrieve CO-OPS tidal data within a region

```python
from datetime import datetime, timedelta

from shapely.geometry import MultiPolygon
from stormevents.coops import coops_data_within_region

polygon = MultiPolygon(...)

coops_data_within_region(region=polygon, start_date=datetime.now() - timedelta(days=2), end_date=datetime.now())
```

## Related Projects

- `tropycal` - https://tropycal.github.io/tropycal/index.html
- `pyoos` - https://github.com/ioos/pyoos
- `adcircpy` - https://github.com/zacharyburnettNOAA/adcircpy

## Acknowledgements

This code was initially written by [@jreniel](https://github.com/jreniel)
for `adcircpy`. 
