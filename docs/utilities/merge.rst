Merging teigger files
#####################

In order to not end up with millions of small ``.root``, ``.hdf5``, and
``.xml`` files each representing a
small chunk of processed time, the ``omicron-process`` workflow will merge
contiguous files together using the following command-line utilities:

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

.. command-output:: omicron-root-merge --help

.. command-output:: omicron-hdf5-merge --help

.. command-output:: ligolw_add --help

