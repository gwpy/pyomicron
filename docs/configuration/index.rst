.. _configuration:

Configuration files for ``omicron-process``
###########################################

The critical user-controlled component of a workflow built with PyOmicron is
the configuration file, an INI-format set of (key, value) pairs that define
how the workflow should be generated.

Each workflow will be configured from a single ``[section]``, which can
have the following keys

**Data selection**
[required]

=============  =============================================================
``channels``   tab-indented, line-separated list of channel names to process
``frametype``  frame type name of data files containing these channels
=============  =============================================================

**Timing**
[required]

====================  ==========================================================
``chunk-duration``    duration of data (seconds) for PSD estimation
``segment-duration``  duration of data (seconds) for FFT
``overlap-duration``  overlap (seconds) between neighbouring segments and chunks
====================  ==========================================================

**State**
[optional]

===================  ========================================================
``state-flag``       name of data-quality flag defining active state segments
===================  ========================================================

OR all of

===================  ========================================================
``state-channel``    name of data channel defining active state
``state-frametype``  frame type name for the ``state-channel``
``state-bits``       comma-separated list of bit numbers that define active
                     state in the ``state-channel``
===================  ========================================================

.. note::

   If both are ``state-flag`` and ``state-channel`` are given, the
   ``state-flag`` will be used for 'offline' workflows generated with
   ``--gps``, while the ``state-channel`` (and related options) will be used
   for 'online' workflows using the latest available data

**Search parameters**
[optional]

===================  ========================================
``frequency-range``  `(low, high)` limits for this search
``q-range``          `(low, high)` limits for this search
``mismatch-max``     maximum distance between `(Q, f)` tiles
``snr-threshold``    minimum SNR for recorded triggers
===================  ========================================

For example:

.. code-block:: ini

   [GW]
   q-range = 3.3166 150
   frequency-range = 4.0 8192.0
   frametype = H1_HOFT_C00
   state-flag = H1:DMT-CALIBRATED:1
   sample-frequency = 16384
   chunk-duration = 124
   segment-duration = 64
   overlap-duration = 4
   mismatch-max = 0.2
   snr-threshold = 5
   channels = H1:GDS-CALIB_STRAIN
