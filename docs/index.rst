.. PyOmicron documentation master file, created by
   sphinx-quickstart on Tue Apr 26 09:12:21 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PyOmicron's documentation!
=====================================

PyOmicron is a workflow generator and processor tool for the `Omicron gravitational-wave event trigger generator <http://virgo.in2p3.fr/GWOLLUM/v2r2/index.html?Main>`_. It was built chielfy to simplify the automatic processing hundreds of data channels recorded by the `Laser Interferometer Gravitational-wave Observatory (LIGO) <http://ligo.org>`_ detectors in order to characterise the instrumental and environmental noises impacting their sensitivity.

Installing PyOmicron
--------------------

The easiest method to install PyOmicron is using `pip <https://pip.pypa.io/en/stable/>`_ directly from the `GitHub repository <https://github.com/ligovirgo/pyomicron.git>`_:

.. code-block:: bash

   $ pip install git+https://github.com/ligovirgo/pyomicron.git

Documentation
-------------

**Workflow generation**

.. toctree::
   :maxdepth: 1

   workflow/index
   configuration/index

**Utilities**

.. toctree::
   :maxdepth: 1
   :glob:

   utilities/*

**Developer API**

.. toctree::
   :maxdepth: 2

   api/omicron

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

