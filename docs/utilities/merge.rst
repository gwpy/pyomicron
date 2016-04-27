Merging ROOT files
##################

In order to not end up with millions of small ``.root`` files each representing a small chunk of processed time, the ``omicron-process`` workflow will merge contiguous files together using the ``omicron-root-merge`` command-line executable.

The executable is a thin wrapper on top of the :meth:`omicron.io.merge_root_files` method:

.. automethod:: omicron.io.merge_root_files

--------------------
Command-line options
--------------------

For detailed documentation of all command-line options and arguments, print the ``--help`` message:

.. command-output:: omicron-root-merge --help
