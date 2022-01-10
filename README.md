# StormEvents

[![tests](https://github.com/zacharyburnettNOAA/StormEvents/workflows/tests/badge.svg)](https://github.com/zacharyburnettNOAA/StormEvents/actions?query=workflow%3Atests)
[![build](https://github.com/zacharyburnettNOAA/StormEvents/workflows/build/badge.svg)](https://github.com/zacharyburnettNOAA/StormEvents/actions?query=workflow%3Abuild)
[![codecov](https://codecov.io/gh/zacharyburnettNOAA/StormEvents/branch/main/graph/badge.svg?token=BQWB1QKJ3Q)](https://codecov.io/gh/zacharyburnettNOAA/StormEvents)
[![version](https://img.shields.io/pypi/v/StormEvents)](https://pypi.org/project/StormEvents)
[![license](https://img.shields.io/github/license/zacharyburnettNOAA/StormEvents)](https://opensource.org/licenses/gpl-license)
[![style](https://sourceforge.net/p/oitnb/code/ci/default/tree/_doc/_static/oitnb.svg?format=raw)](https://sourceforge.net/p/oitnb/code)

`stormevents` provides Python interfaces for observational data surrounding named storm events.

## Usage

### Vortex Track

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

### NHC storms

```python
from stormevents import nhc_storms

nhc_storms()
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

nhc_storms(year=2018)
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
from stormevents import usgs_highwatermark_storms

usgs_highwatermark_storms()
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
