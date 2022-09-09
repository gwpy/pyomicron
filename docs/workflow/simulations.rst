How to run omicron on simulated data
====================================

The pyomicron system can be used to process data in frames outside the usual
process. That is when the data frames are not in the datafind
system and data quality segments and Guardian states do not apply.

The steps are:

* Create a configuration file
* Create a frame cache
* Specify to not use the data quality segments

Below is a sample Python program which creates an example frame file
with 200 seconds of gaussian noise and adds a few sine-gaussiasn glitches.
It produces a frame file in /tmp.

.. code-block:: python

    from gwpy.timeseries import TimeSeries
    from numpy.random import normal
    from numpy import linspace
    from scipy.signal import gausspulse
    from gpstime import tconvert
    from pathlib import Path

    # Generate a TimeSeries containing Gaussian noise sampled at 4096 Hz,
    # with several sine-Gaussian pulses (‘glitch’) at different frequencies:
    strt = tconvert('9/1/2022')
    fs = 4096
    dur = 200
    ndata = fs * dur
    outdir = Path('/tmp')

    # sine gaussian "glitches"
    t = linspace(-1, 1, 2 * fs, endpoint=False)
    sg = gausspulse(t, fc=250, retquad=False, retenv=False)
    sg2 = gausspulse(t, fc=500, retquad=False, retenv=False)
    sg3 = gausspulse(t, fc=750, retquad=False, retenv=False)

    # add  several sets of glitches to the noise
    data = normal(loc=1, size=ndata)  # Gaussian noise

    for t in range(int(dur/4), int(3*dur/4), int(dur/10)):
        data[fs*(t-1):fs*(t+1)] += sg * 12
        data[fs*(t+6):fs*(t+8)] += sg2 * 10
        data[fs*(t+13):fs*(t+15)] += sg3 * 8

    ts = TimeSeries(data, t0=strt, sample_rate=fs, name='Z1:SIM-SINE_GAUSS',
                    channel='Z1:SIM-SINE_GAUSS')
    out_file = str(outdir / f'Z-Z1_SIM-{int(strt)}-{dur}.gwf')
    ts.write(out_file)
    print(f'Wrote {out_file}')

Create a LAL format cache file such as sim.lcf:

.. code-block::

      file://localhost/tmp/Z-Z1_SIM-1346050818-200.gwf

Create a pyomicron configuration file named sim.ini:

.. code-block::

    [SIM]
    q-range = 3.3166 150
    frequency-range = 4.0 2048.0
    frametype = Z-Z1_SIM
    sample-frequency = 4096
    chunk-duration = 124
    segment-duration = 64
    overlap-duration = 4
    mismatch-max = 0.2
    snr-threshold = 6
    channels = Z1:SIM-SINE_GAUSS

We can now run pyomicron:

.. code-block::

    omicron-process --gps 1346050818 1346051018 --ifo Z1 --config-file ./sim.ini \
        --output-dir ./run --no-segdb --cache-file ./sim.lcf -vvv --file-tag SIM SIM

The results will be in the directory:

.. code-block::

    ./run/merge/Z1:SIM-SINE_GAUSS/

One way to view them is to use ligolw_print. The results, formatted for readability:

.. code-block::

    ligolw_print -t sngl_burst -c 'peak_time' -c 'snr' -c 'peak_frequency' \
        'run/merge/Z1:SIM-SINE_GAUSS/Z1-SIM_SINE_GAUSS_OMICRON-1346050820-196.xml.gz'

    +------------+-----------+--------------+
    | peak_time  | SNR       | Frequency    |
    +============+===========+==============|
    | 1346050868 | 37.1      | 236.4        |
    | 1346050875 | 22.1      | 480.7        |
    | 1346050882 | 15.2      | 771.3        |
    | 1346050888 | 37.1      | 243.9        |
    | 1346050894 | 21.4      | 459.1        |
    | 1346050902 | 13.7      | 699.8        |
    | 1346050908 | 36.5      | 266.1        |
    | 1346050915 | 22.4      | 480.7        |
    | 1346050922 | 13.9      | 771.3        |
    | 1346050928 | 36.0      | 236.4        |
    | 1346050935 | 22.1      | 480.6        |
    | 1346050942 | 14.2      | 771.3        |
    | 1346050948 | 38.7      | 243.9        |
    | 1346050954 | 24.3      | 459.1        |
    | 1346050962 | 15.0      | 699.7        |
    +------------+-----------+--------------+



