``StormEvent``
==============

The ``StormEvent`` class can be used to retrieve data related to any arbitrary named storm event.
You can instantiate a new ``StormEvent`` object from the NHC storm name and year
(i.e. ``FLORENCE 2018``, the NHC storm code (i.e. ``AL062018``), or the USGS flood event ID (i.e. ``304``).

.. code-block:: python

    from stormevents import StormEvent

    florence2018 = StormEvent('florence', 2018)
    paine2016 = StormEvent.from_nhc_code('EP172016')
    sally2020 = StormEvent.from_usgs_id(304)

You can then retrieve track data from NHC, high-water mark data from USGS, and water level products from CO-OPS for this storm.
By default, these functions operate within the time interval defined by the NHC best track.

.. code-block:: python

    from stormevents import StormEvent

    florence2018 = StormEvent('florence', 2018)

    track = florence2018.track()
    high_water_marks = florence2018.high_water_marks()
    water_levels = florence2018.tidal_data_within_isotach(isotach=34)
