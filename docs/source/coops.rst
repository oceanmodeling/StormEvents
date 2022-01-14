CO-OPS tidal station data
=========================

The [Center for Operational Oceanographic Products and Services (CO-OPS)]https://tidesandcurrents.noaa.gov)
maintains and operates a large amount of tidal stations that measure water levels across the coastal United States.
CO-OPS provides several [data products](https://tidesandcurrents.noaa.gov/products.html)
including hourly water levels, tidal datums and predictions, and trends in sea level over time.

list CO-OPS tidal stations
--------------------------

.. autofunction:: stormevents.coops.tidalstations.coops_stations
.. autofunction:: stormevents.coops.tidalstations.coops_stations_within_region
.. autoclass:: stormevents.coops.tidalstations.COOPS_Station

list CO-OPS tidal stations within a region
------------------------------------------

.. autofunction:: stormevents.coops.tidalstations.coops_data_within_region

construct an individual data query
""""""""""""""""""""""""""""""""""

.. autoclass:: stormevents.coops.tidalstations.COOPS_Query
