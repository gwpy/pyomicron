# -*- coding: utf-8 -*-
# Copyright (C) Duncan Macleod (2013)
#
# This file is part of LIGO-Omicron.
#
# LIGO-Omicron is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LIGO-Omicron is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LIGO-Omicron.  If not, see <http://www.gnu.org/licenses/>.

"""Read/write/modify Omicron-format parameters files
"""

from __future__ import (division, print_function)

try:
    import ConfigParser as configparser
except ImportError:  # python 2.x
    import configparser

from math import (ceil, exp, floor, log)
import os.path

DEFAULTS = {
    'PARAMETER': {
        'CLUSTERING': 'TIME',
    },
    'OUTPUT': {
        'PRODUCTS': 'triggers',
        'VERBOSITY': 2,
        'FORMAT': 'rootxml',
        'NTRIGGERMAX': 1e7,
    },
    'DATA': {
    }
}

UNUSED_PARAMS = ['state-flag', 'frametype']
OMICRON_PARAM_MAP = {
    'sample-frequency': ('DATA', 'SAMPLEFREQUENCY')
}


def generate_parameters_files(config, section, cachefile, rundir,
                              channellimit=10, **kwargs):
    pardir = os.path.join(rundir, 'parameters')
    trigdir = os.path.join(rundir, 'triggers')
    for d in [pardir, trigdir]:
        if not os.path.isdir(d):
            os.makedirs(d)

    # reformat from LCF format
    for (range_, low_, high_) in [('frequency-range', 'flow', 'fhigh'),
                                  ('q-range', 'qlow', 'qhigh')]:
        if (not config.has_option(section, range_) and
                config.has_option(section, low_)):
            config.set(
                section, range_,
                '%s %s' % (config.getfloat(section, low_),
                           config.getfloat(section, high_)))
        for opt in (low_, high_):
            try:
                config.remove_option(section, opt)
            except configparser.NoOptionError:
                pass

    # get parameters
    params = DEFAULTS.copy()
    cpparams = dict(config.items(section))
    channellist = cpparams.pop('channels').split('\n')
    # remove params that can't be parsed
    for key in UNUSED_PARAMS:
        cpparams.pop(key, None)
    # set custom params
    params['DATA']['FFL'] = cachefile
    params['OUTPUT']['DIRECTORY'] = trigdir

    for d in [cpparams, kwargs]:
        for key in d:
            try:
                group, attr = OMICRON_PARAM_MAP[key]
            except KeyError:
                params['PARAMETER'][''.join(key.split('-')).upper()] = d[key]
            else:
                params[group][attr] = d[key]

    # write files
    parfiles = []
    i = 0
    while i * channellimit < len(channellist):
        channels = channellist[i * channellimit:(i+1) * channellimit]
        pfile = os.path.join(pardir, 'parameters_%d.txt' % i)
        with open(pfile, 'w') as f:
            for group in params:
                for key, val in params[group].iteritems():
                    if isinstance(val, (list, tuple)):
                        val = ' '.join(val, (list, tuple))
                    print('{0: <10}'.format(group), '{0: <16}'.format(key), val,
                          file=f, sep=' ')
                print("", file=f)
            for c in channels:
                print('{0: <10}'.format('DATA'), '{0: <16}'.format('CHANNELS'),
                      str(c), file=f, sep=' ')
        parfiles.append((pfile, channels))
        i += 1
    return parfiles


def validate_parameters(chunk, segment, overlap, frange, sampling=None):
    """Validate that Omicron will accept the segment parameters

    Parameters
    ----------
    chunk : `int`
        omicron CHUNKDURATION parameter
    segment : `int`
        omicron SEGMENTDURATION parameter
    overlap : `int`
        omicron OVERLAPDURATION parameter
    frange : `tuple` of `float`
        omicron FREQUENCYRANGE parameter

    Raises
    ------
    AssertionError
        if any of the parameters isn't acceptable for Omicron to process
    """
    assert segment <= chunk, "Segment length is greater than chunk length"
    assert overlap <= segment, "Overlap length is greater than segment length"
    assert overlap % 2 == 0, "Padding (overlap/2) is non-integer"
    dchunk = chunk - overlap
    dseg = segment - overlap
    assert dchunk % dseg == 0, (
        "Chunk duration doesn't allow an integer number of segments, "
        "%ds too large" % (dchunk % dseg))
    if sampling is None:
        return
    if frange[0] < 1:
        x = 10 * floor(sampling / frange[0])
        psdsize = 2 * int(2 ** ceil(log(x) / log(2.)))
    else:
        psdsize = 2 * sampling
    psdlen = psdsize / sampling
    chunkp = chunk * sampling
    overlapp = overlap * sampling
    flow = 5 * sampling / exp(log((chunk - overlap)/4., 2))
    assert (chunkp - overlapp) >= 2 * psdsize, (
        "Chunk duration not large enough to resolve lower-frequency bound, "
        "Omicron needs at least %ds. Minimum lower-frequency bound for "
        "this chunk duration is %.2gHz" % (2 * psdlen + overlap, flow))
