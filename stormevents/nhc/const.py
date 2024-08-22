from enum import Enum, auto

from numpy import isnan, array, argwhere
from pandas import DataFrame


class RMWFillMethod(Enum):
    none = None
    persistent = auto()
    regression_penny_2023 = auto()


# Bias correction values for the Rmax forecast
# ref: Penny et al. (2023). https://doi.org/10.1175/WAF-D-22-0209.1
bias_lat = [
    0.0063,
    0.0301,
    0.0299,
    0.0085,
    -0.0199,
    -0.0354,
    -0.0799,
    -0.1240,
    -0.1572,
    -0.1982,
    -0.1706,
]

bias_vmax = [
    -0.8047,
    -0.2003,
    -0.2001,
    -0.4070,
    -0.6271,
    -0.7515,
    -0.3369,
    -0.3338,
    -0.3930,
    -0.8167,
    -1.4322,
]

bias_r34 = [
    -2.0503,
    -5.5195,
    -7.7374,
    -8.4337,
    -8.1458,
    -10.2065,
    -12.6435,
    0,
    0,
    0,
    0,
]

bias_r50 = [
    -0.7659,
    -3.2270,
    -4.5476,
    -6.2219,
    -7.7406,
    -8.5449,
    -10.0759,
    0,
    0,
    0,
    0,
]

bias_r64 = [
    -0.5082,
    -2.4170,
    -3.6993,
    -4.7795,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
]

RMW_bias_correction = DataFrame(
    index=range(0, 132, 12),
    data={
        "latitude": bias_lat,
        "max_sustained_wind_speed": bias_vmax,
        "isotach_radius_34": bias_r34,
        "isotach_radius_50": bias_r50,
        "isotach_radius_64": bias_r64,
    },
)

# Regression coefficients for the Rmax forecast
# ref: Penny et al. (2023). https://doi.org/10.1175/WAF-D-22-0209.1
fhrs = [12, 24, 36, 48, 72, 96, 120]
RMW_regression_coefs = {
    3: [  # a0    #a1      #a2     #a3      #a4     #a5     #a6
        [3.1894, 0.3524, 0.1208, -0.1091, 0.5862, -0.8070, 0.0057],
        [4.4373, 0.1473, 0.1045, -0.1112, 0.7566, -1.0689, 0.0061],
        [4.9447, 0.0784, 0.1168, -0.1448, 0.8246, -1.1709, 0.0059],
        [5.1818, 0.0549, 0.1335, -0.2345, 0.8972, -1.2038, 0.0063],
    ],
    2: [  # a0    #a1      #a2     #a3      #a5     #a6
        [3.1131, 0.3680, 0.1589, 0.4710, -0.9111, 0.0068],
        [4.1567, 0.1834, 0.2085, 0.5873, -1.1841, 0.0073],
        [4.6694, 0.1062, 0.2330, 0.6295, -1.3122, 0.0074],
        [4.9434, 0.0459, 0.3027, 0.5828, -1.3675, 0.0079],
        [4.7906, 0.0157, 0.3953, 0.5321, -1.3617, 0.0067],
    ],
    1: [  # a0    #a1      #a2     #a5      #a6
        [2.6272, 0.4230, 0.6320, -0.9117, 0.0064],
        [3.6525, 0.2142, 0.8222, -1.2158, 0.0082],
        [4.2822, 0.0884, 0.9059, -1.3656, 0.0091],
        [4.7700, -0.0042, 0.9225, -1.4349, 0.0102],
        [4.7307, -0.0365, 0.9153, -1.3882, 0.0086],
    ],
    0: [  # a0    #a1      #a5     #a6
        [2.1633, 0.6360, -0.3314, 0.0154],
        [3.7884, 0.3953, -0.5738, 0.0219],
        [5.0213, 0.1999, -0.7481, 0.0276],
        [5.8092, 0.0615, -0.8508, 0.0318],
        [6.3321, -0.0362, -0.9079, 0.0343],
        [6.6181, 0.0041, -0.9599, 0.0295],
        [6.7073, -0.0028, -0.9478, 0.0257],
    ],
}


def get_RMW_regression_coefs(fcst_hr, radii_values):
    num_radii_available = (~isnan(radii_values)).sum()
    coefs_by_radii_available = array(RMW_regression_coefs[num_radii_available])
    fcst_index = argwhere(fhrs == fcst_hr)
    if fcst_index.size == 0 or fcst_index > coefs_by_radii_available.shape[0] - 1:
        return coefs_by_radii_available[-1].flatten()
    else:
        return coefs_by_radii_available[fcst_index].flatten()
