Printing Omicron data
#####################

PyOmicron provides the ``omicron-print`` utility to find and display the location of Omicron event trigger files, or the contents of those files in ASCII format.

Printing file locations
=======================

``omicron-print files`` can be used to display the location of Omicron event files for a given channel in a given GPS interval

.. code-block:: bash

   $ omicron-print files <channel> <gpsstart> <gpsend>

where ``<channel>`` is the name of a data channel, e.g. ``L1:GDS-CALIB_STRAIN``, and ``<gpsstart>`` and ``<gpsend>`` are the start and end times of your query.

.. note::

   The ``--gaps`` option can be give to display while time segments are *not* covered by the files avialable.

More help
---------

Run ``omicron-print files --help`` to see the full list of options and arguments

.. command-output:: omicron-print files --help


Printing event data
===================

``omicron-print events`` can bs used to print the parameters of events themselves to the screen:

.. code-block:: bash

   $ omicron-print events <channel> <gpsstart> <gpsend>

By default this will print the peak time, peak frequency, and signal-to-noise ratio (SNR) of all events that are found. You can specify the columns you want via the ``-c/--column`` argument (give once for each column you want).

Conditions
----------

You can restrict which events to display based on their parameters by using the ``-x/--condition`` option on the command line, give it once per mathematical condition you want.

The conditions should be formatted as ``<column> <operator> <threshold>``, e.g. ``snr > 5``, or ``<min> < <column> < <max>`` for bounds, e.g. ``100 < peak_freqency < 200``.

.. code-block:: bash

   $ omicron-print events L1:GDS-CALIB_STRAIN 1000000000 1000000100 -c time -c snr -x "snr > 100" -x "peak_frequency < 50"

More help
---------

Run ``omicron-print events --help`` to see the full list of options and arguments

.. command-output:: omicron-print events --help

