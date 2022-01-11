# StormEvents

[![tests](https://github.com/zacharyburnettNOAA/StormEvents/workflows/tests/badge.svg)](https://github.com/zacharyburnettNOAA/StormEvents/actions?query=workflow%3Atests)
[![build](https://github.com/zacharyburnettNOAA/StormEvents/workflows/build/badge.svg)](https://github.com/zacharyburnettNOAA/StormEvents/actions?query=workflow%3Abuild)
[![codecov](https://codecov.io/gh/zacharyburnettNOAA/StormEvents/branch/main/graph/badge.svg?token=BQWB1QKJ3Q)](https://codecov.io/gh/zacharyburnettNOAA/StormEvents)
[![version](https://img.shields.io/pypi/v/StormEvents)](https://pypi.org/project/StormEvents)
[![license](https://img.shields.io/github/license/zacharyburnettNOAA/StormEvents)](https://opensource.org/licenses/gpl-license)
[![style](https://sourceforge.net/p/oitnb/code/ci/default/tree/_doc/_static/oitnb.svg?format=raw)](https://sourceforge.net/p/oitnb/code)

`stormevents` provides Python interfaces for observational data surrounding named storm events.

## Usage

### NHC Vortex Tracks

```python
from stormevents import VortexTrack

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

#### listing NHC storms

```python
from stormevents import nhc_storms

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

```python
from stormevents import nhc_storms

nhc_storms_2018 = nhc_storms(year=2018)
```

```
                name                       long_name  year
nhc_code                                                        
al012018     ALBERTO       Subtropical Storm ALBERTO  2018
al022018       BERYL                 Hurricane BERYL  2018
al032018       CHRIS                 Hurricane CHRIS  2018
al042018       DEBBY            Tropical Storm DEBBY  2018
al052018     ERNESTO          Tropical Storm ERNESTO  2018
...              ...                             ...   ...
ep102018      HECTOR                Hurricane HECTOR  2018
ep142018        LANE                  Hurricane LANE  2018
ep152018      MIRIAM                Hurricane MIRIAM  2018
ep162018      NORMAN                Hurricane NORMAN  2018
ep172018      OLIVIA                Hurricane OLIVIA  2018

[47 rows x 3 columns]
```

### USGS High Water Marks

```python
from stormevents import HurricaneHighWaterMarks

hwm_florence2018 = HurricaneHighWaterMarks('florence', 2018)

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

#### listing USGS flood storm events with high water mark data

```python
from stormevents import usgs_highwatermark_storms

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

## Acknowledgements

This code was initially written by [@jreniel](https://github.com/jreniel)
for [`adcircpy`](https://github.com/zacharyburnettNOAA/adcircpy). 
