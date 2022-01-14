USGS high water mark (HWM) surveys
==================================

The [United States Geological Survey (USGS)](https://www.usgs.gov)
conducts surveys of flooded areas following flood events to determine the highest level of water elevation,
and provides the results of these surveys via their API.

list storm flood events that have HWM surveys
---------------------------------------------

.. autofunction:: stormevents.usgs.highwatermarks.usgs_highwatermark_storms

retrieve HWM data for a specific storm
""""""""""""""""""""""""""""""""""""""

.. autoclass:: stormevents.usgs.highwatermarks.StormHighWaterMarks

list all flood events that have HWM surveys
-------------------------------------------

.. autofunction:: stormevents.usgs.highwatermarks.usgs_highwatermark_events

retrieve HWM data for a specific flood event
""""""""""""""""""""""""""""""""""""""""""""

.. autoclass:: stormevents.usgs.highwatermarks.HighWaterMarks
