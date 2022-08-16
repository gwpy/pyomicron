
Generating a workflow using ``omicron-process``
###############################################

PyOmicron provides the `omicron-process` command-line executable, designed for creating and managing `HTCondor <https://research.cs.wisc.edu/htcondor/>`_ workflows.


The only hard requirement in order to run `omicron-process` is a :ref:`configuration <configuration>` file. Once you have that you can run automatically over the most recent chunk of data as

.. code-block:: bash

   $ omicron-process <group> --config-file <config-file>

where ``<config-file>`` is the name of your configuration file, and ``<group>`` is the name of the section inside that file that configures this workflow.

.. warning::

   By default, this command will automatically generate the workflow as an
   HTCondor DAG and submit it to via ``condor_submit_dag``.
   To generate the workflow but *not* submit the DAG, add the ``--no-submit``
   option on the command line.

.. note::

   By default, `omicron-process` won't output very much to the screen, so it
   can be useful to supply ``--verbose --verbose`` (i.e. ``--verbose`` twice)
   to get the ``DEBUG`` logging statements. This will provide a running
   progress report for the workflow, which can be very informative.

.. warning::

   `omicron-process` will complain loudly if it can't find ``omicron.exe``
   on the path somewhere.

You can either specify ``--executable`` manually
on the command line, or **if you are working in the detchar account on the LIGO Data Grid**
you enable the standard conda environment for omicron with the following command:

.. code-block:: bash

    conda_omicron

The other alternative is to install omicron into your conda environment with:

.. code-block:: bash

    mamba install omicron

-----------------------
Details of the workflow
-----------------------

The ``omicron-process`` executable will do the following

* find the relevant time segments to process (if ``state-flag`` or ``state-channel`` has been defined in the configuration),
* find the frame files containing the data (using :mod:`gw_data_find <glue.datafind>`),
* build a Directed Acyclic Graph (DAG) defining the workflow.

The DAG will normally do something like this:

#. process raw data using ``omicron.exe``
#. merge contiguous output files with ``.root``, ``.h5``, and ``.xml`` extensions
#. gzip ``.xml`` files to save space
#. the merged files are copied to the archive directory, nominally
   ``/home/detchar/triggers/<ifo>/<channel-filetag>/<metric day>``
#. if everything completes successfully, trigger and log files are deleted

.. figure:: ../_static/omicron-GW.png
    :align: center
    :alt: typical DAG diagram
    :figclass: align-center

.. note::
    The workflow will break the interval into *chunks* defined in the configuration
    file ``chunkdur`` parameter, which includes the padding. The nominal value
    is 120 sec. This results in multiple htCondor jobs.

----------------------------
Archiving multiple workflows
----------------------------

Optionally, you can specify the ``--archive`` option to copy files from the run directory into a structured archive under ``~/triggers/``. Each file is re-located as follows::

   ~/triggers/{IFO}/{filetag}/{gps5}/{filename}

where the path components are as follows

* ``{IFO}`` is the two-character interferometer prefix for the raw data channel (e.g. ``L1``),
* ``{filetag}`` is an underscore-delimited tag including the rest of the channel name and ``OMICRON``, e.g. (``GDS_CALIB_STRAIN_OMICRON``),
* ``{gps5}`` is the 5-digit GPS epoch for the start time of the file, e.g. ``12345`` if the file starts at GPS ``1234567890``.
* ``{filename}`` is the `T050017 <https://dcc.ligo.org/LIGO-T050017/>`_-compatible name, which will be of the form ``{IFO}-{filetag}-<gpsstart>-<duration>.<ext>``

e.g.::

   ~/triggers/L1/GDS_CALIB_STRAIN_OMICRON/12345/L1-GDS_CALIB_STRAIN_OMICRON-1234567890-100.xml.gz

-----------------------------------
Processing a specific time interval
-----------------------------------

If you have a specific time interval that you're most interested in, you will need to use the ``--gps`` option on the command line:

.. code-block:: bash

   $ omicron-process <group> --config-file <config-file> --gps <gpsstart> <gpsend>

where ``<gpsstart>`` and ``<gpsend>`` are your two GPS times.

.. note::

   You can also give the GPS arguments as date strings, in quotes, as follows

   .. code-block:: bash

      $ omicron-process <group> --config-file <config-file> --gps "Jan 1" "Jan 2"

Additionally, when using ``-gps``, you can specify ``--cache-file`` to submit your own LAL-formatted data cache file:

.. code-block:: bash

   $ omicron-process <group> --config-file <config-file> --gps <gpsstart> <gpsend> --cache-file /path/to/cache.lcf


---------
More help
---------

For detailed documentation of all command-line options and arguments, print the ``--help`` message:

.. command-output:: omicron-process --help
