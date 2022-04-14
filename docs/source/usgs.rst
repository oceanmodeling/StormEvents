USGS high water mark (HWM) surveys
==================================

The `United States Geological Survey (USGS) <https://www.usgs.gov>`_
conducts surveys of flooded areas following flood events to determine the highest level of water elevation,
and provides the results of these surveys via their API.

list flood events that have HWM surveys
---------------------------------------

.. autofunction:: stormevents.usgs.events.usgs_flood_events

abstraction of a USGS flood event
---------------------------------

.. autoclass:: stormevents.usgs.events.USGS_Event
