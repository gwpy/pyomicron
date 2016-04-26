
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

-----------------------
Details of the workflow
-----------------------

The ``omicron-process`` executable will do the following

* find the relevant time segments to process (if ``state-flag`` or ``state-channel`` has been defined in the configuration),
* find the frame files containing the data (using `gw_data_find <glue.datafind>`),
* build a Directed Acyclic Graph (DAG) defining the workflow.

By default the DAG will do something like this

#. process raw data using ``omicron.exe``
#. merge contiguous ouput files for both ``.root`` and ``.xml`` extensions
#. gzip ``.xml`` files to save space

----------------------------
Archiving multiple workflows
----------------------------

Optionally, you can specify the ``--archive`` option to copy files from the run directory into a structured archive under ``~/triggers/``. Each file is re-located as follows::

   ~/triggers/{IFO}/{filetag}/{gps5}/{filename}

where the path components are as follows

* ``{IFO}`` is the two-character interferometer prefix for the raw data channel (e.g. ``L1``),
* ``{filetag}`` is an underscore-delimited tag including the rest of the channel name and ``OMICRON``, e.g. (``GDS_CALIB_STRAIN_OMICRON``),
* ``{gps5}`` is the 5-digit GPS epoch for the start time of the file, e.g. ``12345`` if the file starts at GPS ``1234567890``.
* ``{filename}`` is the `T050017 <https://dcc.ligo.org/LIGO-T050017/public>`_-compatible name, which will be of the form ``{IFO}-{filetag}-<gpsstart>-<duration>.<ext>``

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

---------
More help
---------

For detailed documentation of all command-line options and arguments, print the ``--help`` message:

.. command-output:: omicron-process --help
