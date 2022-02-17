USGS high water mark (HWM) surveys
==================================

The [United States Geological Survey (USGS)](https://www.usgs.gov)
conducts surveys of flooded areas following flood events to determine the highest level of water elevation,
and provides the results of these surveys via their API.

list flood events that have HWM surveys
---------------------------------------

.. autofunction:: stormevents.usgs.highwatermarks.usgs_highwatermark_events

retrieve HWM survey data for any flood event
--------------------------------------------

.. autoclass:: stormevents.usgs.highwatermarks.HighWaterMarks
