Merge trigger files
###################

In order to not end up with millions of small ``.root``, ``.hdf5``, and
``.xml`` files each representing a
small chunk of processed time, the ``omicron-process`` workflow will merge
contiguous files together using the ``omicron-merge-with-gaps`` command line utility.
The purpose of this control utility is to detect any gaps in the expected list
trigger files.  The gaps are data dependent failures of Omicron to process
one of the short time intervals. 


``omicron-merge-with-gaps`` uses the following command-line utilities to
merge te contiguous trigger files:

+------------+-----------+-------------------------------------------------+
| File type  | Extension | Program                                         |
+============+===========+=================================================+
| Root       | ``.root`` | ``omicron-root-merge``                          |
+------------+-----------+-------------------------------------------------+
| HDF5       | ``.hdf5`` | ``omicron-hdf5-merge``                          |
+------------+-----------+-------------------------------------------------+
| ligolw     | ``.xml `` | ``ligolw_add`` and ``gzip``                     |
+------------+-----------+-------------------------------------------------+
| Text       | ``.txt `` | ``?``                                           |
+------------+-----------+-------------------------------------------------+

The ``omicron-root-merge`` executable is a thin wrapper on top of
the :meth:`omicron.io.merge_root_files` method:

.. automethod:: omicron.io.merge_root_files

The ``omicron-hdf5-merge`` executable is a thin wrapper on top of
the :meth:`omicron.io.merge_hdf5_files` method:

.. automethod:: omicron.io.merge_hdf5_files

The ``ligolw_add`` is an external program contained in the ``lscsoft-glue`` package.



--------------------
Command-line options
--------------------

For detailed documentation of all command-line options and arguments, print the ``--help``
message of each program:

.. command-output:: omicron-merge-with-gaps --help

.. command-output:: omicron-root-merge --help

.. command-output:: omicron-hdf5-merge --help

.. command-output:: ligolw_add --help

Reducing file count and disk space
##################################

Current operations run ``omicron-proocess`` every 12 minutes to provide near
real time triggers. Over a day this can result in up to 360 (5 * 24 * 3) files per
channel with O(1000) channels per day.

To address this issue, the program ``omicron-metric-day-merge`` will scan each channel
for trigger files in a specific metric day. A metric  day is used to mean 100,000 second
boundary of GPS time. It will colaesce all contiguous trigger files into a temporary diretory

.. command-output:: omicron-metric-day-merge --help


Archive trigger files
#####################

Archiving is also complicated by the potential gaps in triggers. The ``omicron-archive``
program examines all the merged trigger files organizing them by channel and metric day
(int(gps_start_time/1e5)). These are then *copied* to the archive directory, usually
/home/detchar/triggers/<ifo>, but it can be overridden for testing on the command
line or by setting the envirnment variable ``OMICRON_HOME``. The full help opions are:

.. command-output:: omicron-merge-with-gaps --help
