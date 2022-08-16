Status checks
=============

The program ``omicron-status`` check for several common problems:

* Gaps: the dectector was in an analyzable state, frames of the appropriate
  type are available but there are no trigger files.
* Latency: <todo: working on what this is??>
* Overlaps: checks for trigger files that duplicate or overlap others

When used with the ``--json`` option the program writes files compatible
with the dashboard LIGO Nagios monitors. See
`Omicron dashboard <https://dashboard.ligo.org/cgi-bin/nagios3/status.cgi?servicegroup=detchar-omicron&style=detail>`_

The ``--html`` option creates a plot of latency and a list of parameters used.
The results are shown in the "Service status" tab of the network nummary pages.


.. figure:: ../_static/nagios-latency-L1-GDS-CALIB_STRAIN.png
    :align: center
    :alt: Latency plot
    :figclass: align-center


The full list of options is available from the help message:

.. command-output:: omicron-status --help

