# ModelForcings

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
