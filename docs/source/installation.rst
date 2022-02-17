Installation
============

To install ``stormevents``, you need [Python >= version 3.6](https://www.python.org/downloads).

Once you have installed Python, and presumably have ``pip`` that comes with the default installation,
you can run the following command to install ``stormevents`` directly from PyPI:

.. code-block:: bash

    pip install stormevents

You can do this within the system Python installation, in an Anaconda environment, or in a ``virtualenv`` environment.
Of these, ``virtualenv`` is the easiest to work with; to set up an environment, do the following (this example is for Bash):

.. code-block:: bash

    pip install virtualenv
    mkdir ~/environments
    virtualenv ~/environments/stormevents
    source ~/environments/stormevents/bin/activate
    pip install stormevents

To execute a Python script from a ``virtualenv`` environment, do the following:

.. code-block:: bash

    source ~/environments/stormevents/bin/activate
    python /path/to/python/script.py
    deactivate
