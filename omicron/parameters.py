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

from __future__ import print_function

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
        parfiles.append(pfile)
        i += 1
    return parfiles
