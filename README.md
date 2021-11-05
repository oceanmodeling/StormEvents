# ModelForcings

[![tests](https://github.com/zacharyburnettNOAA/ModelForcings/workflows/tests/badge.svg)](https://github.com/zacharyburnettNOAA/ModelForcings/actions?query=workflow%3Atests)
[![build](https://github.com/zacharyburnettNOAA/ModelForcings/workflows/build/badge.svg)](https://github.com/zacharyburnettNOAA/ModelForcings/actions?query=workflow%3Abuild)
[![codecov](https://codecov.io/gh/zacharyburnettNOAA/ModelForcings/branch/main/graph/badge.svg?token=BQWB1QKJ3Q)](https://codecov.io/gh/zacharyburnettNOAA/ModelForcings)
[![version](https://img.shields.io/pypi/v/ModelForcings)](https://pypi.org/project/ModelForcings)
[![license](https://img.shields.io/github/license/zacharyburnettNOAA/ModelForcings)](https://opensource.org/licenses/gpl-license)
[![style](https://sourceforge.net/p/oitnb/code/ci/default/tree/_doc/_static/oitnb.svg?format=raw)](https://sourceforge.net/p/oitnb/code)

`modelforcings` provides Python interfaces for various forcings commonly used in coupled ocean modeling.

## Usage

### Vortex Data

```python
from modelforcings.vortex import VortexForcing

# retrieve vortex data from the Internet from its ID
vortex = VortexForcing('AL112017')

# you can also use the storm name and year in the lookup
vortex = VortexForcing('irma2017')

# write to a file in the ADCIRC `fort.22` format
vortex.write('fort.22')

# read vortex data from an existing ATCF track file (`*.trk`)
vortex = VortexForcing.from_atcf_file('atcf.trk')

# read vortex data from an existing file in the ADCIRC `fort.22` format
vortex = VortexForcing.from_atcf_file('fort.22')
```
