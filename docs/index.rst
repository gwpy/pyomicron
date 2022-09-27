PyOmicron
=========

PyOmicron is a workflow generator and processor tool for
the `Omicron gravitational-wave event trigger
generator <https://virgo.docs.ligo.org/virgoapp/Omicron/>`_.
It was built chiefly to simplify the automatic processing hundreds of
data channels recorded by the `Laser Interferometer Gravitational-wave Observatory
(LIGO) <https://www.ligo.caltech.edu>`_ and `Virgo <https://www.ego-gw.it/>`_
detectors in order to characterise the instrumental and environmental noises
impacting their sensitivity.

Built: |today|

Installing PyOmicron
--------------------

Installation
------------

PyOmicron can be installed with `conda <https://conda.io/>`_
(or `Mamba <https://mamba.readthedocs.io/>`_):

.. code-block:: shell

   conda install -c conda-forge pyomicron

or `pip <https://pip.pypa.io>`_:

.. code-block:: shell

   python -m pip install pyomicron

.. warning::

   Omicron (the C++ application) cannot be installed with `pip`, so installing
   PyOmicron with `conda/mamba` is strongly encouraged.

Documentation
-------------

**Workflow generation**

.. toctree::
   :maxdepth: 1

   workflow/index
   configuration/index
   workflow/simulations

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

