# ! /usr/bin/env python

import pandas

from stormevents import usgs_highwatermark_storms
from tests import REFERENCE_DIRECTORY


def test_usgs_highwatermark_storms():
    reference_directory = REFERENCE_DIRECTORY / 'test_usgs_highwatermark_storms'

    storms = usgs_highwatermark_storms()

    reference_storms = pandas.read_csv(reference_directory / 'storms.csv', index_col='usgs_id')

    assert storms.equals(reference_storms)
