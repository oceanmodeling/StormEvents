# ModelForcings

`modelforcings` provides Python interfaces for various forcings commonly used in coupled ocean modeling.

## Usage

### Vortex Data

```python
from modelforcings.vortex import VortexForcing

# retrieve vortex data for Florence 2018 from the Internet
vortex_florence2018 = VortexForcing('irma2017')

# write to a file in the ADCIRC `fort.22` format
vortex_florence2018.write('fort.22')

# read vortex data from an existing ATCF track file (`*.trk`)
vortex_irma2017 = VortexForcing.from_atcf_file('irma2017_atcf.trk')

# read vortex data from an existing file in the ADCIRC `fort.22` format
vortex_from_fort22 = VortexForcing.from_atcf_file('fort.22')
```
