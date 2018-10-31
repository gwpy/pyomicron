# -*- coding: utf-8 -*-
# Copyright (C) Duncan Macleod (2016)
#
# This file is part of PyOmicron.
#
# PyOmicron is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyOmicron is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyOmicron.  If not, see <http://www.gnu.org/licenses/>.

"""Constants and variables for Omicron processing
"""

import os

from ligo.segments import segment as Segment

# -- generic parameters
try:
    IFO = os.environ['IFO']
except KeyError:
    from socket import getfqdn
    fqdn = getfqdn()
    if '.uni-hannover.' in fqdn:
        IFO = 'G1'
    elif '.ligo-wa.' in fqdn:
        IFO = 'H1'
    elif '.ligo-la.' in fqdn:
        IFO = 'L1'
    elif '.virgo.' in fqdn or '.ego-gw.' in fqdn:
        IFO = 'V1'
    else:
        IFO = None
    ifo = os.getenv('ifo')
else:
    ifo = os.getenv('ifo', IFO.lower())
SITE = os.getenv('SITE')
site = os.getenv('site', SITE and SITE.lower() or None)

# -- omicron directories
HOME = os.path.expanduser('~')
# where Omicron runs
OMICRON_BASE = os.path.join(HOME, 'omicron')
# where Omicron triggers are produced
OMICRON_PROD = os.path.join(OMICRON_BASE, 'online')
# archive storage directory
OMICRON_ARCHIVE = os.path.join(HOME, 'triggers')
# tag Omicron itself places on XML files
OMICRON_FILETAG = 'Omicron'

# omicron production version
OMICRON_VERSION = 'v2r1'

# omicron channel files
if ifo is not None:
    OMICRON_GROUP_FILE = os.path.join(OMICRON_PROD, '%s-groups.txt' % ifo)
    OMICRON_CHANNELS_FILE = os.path.join(OMICRON_PROD, '%s-channels.txt' % ifo)
else:
    OMICRON_GROUP_FILE = None
    OMICRON_CHANNELS_FILE = None

# epochs
EPOCH = {
    "VSR1": Segment(863557214, 875250014),
    "VSR2": Segment(931035615, 947100000),
    "S6c": Segment(947100001, 965599214),
    "VSR3": Segment(965599215, 971686015),
    "VSR4": Segment(991170015, 999061215),
    "ER2": Segment(1026086416, 1028332816),
    "ER3": Segment(1042088795, 1046510000),
    "POSTER3": Segment(1046510000, 1057795216),
    "ER4": Segment(1057795216, 1063000000),
    "POSTER4": Segment(1063000000, 1073779216),
    "ER5": Segment(1073779216, 1079049616),
    "POSTER5": Segment(1073779216, 1101700000),
    "ER6": Segment(1101700000, 1103700000),
    "POSTER6": Segment(1103700000, 1116930000),
    "ER7": Segment(1116930000, 1118700000),
    "POSTER7": Segment(1118700000, 1123804817),
    "ER8": Segment(1123804817, 1126137617),
    "O1": Segment(1126137617, 1134604817),
    "POSTO1": Segment(1134604817, 1500000000),
}


def epoch_at_gps(gps):
    """Return the named epoch that contains the given GPS time

    Parameters
    ----------
    gps : `int`
        the GPS time in question

    Returns
    -------
    epoch : `str`
        the name of the containing epoch

    Examples
    --------
    >>> epoch_at_gps(1126259462)
    'O1'

    Raises
    ------
    ValueError
        if the given `gps` isn't covered by any known epoch
    """
    for epoch in EPOCH:
        if gps in EPOCH[epoch]:
            return epoch
    raise ValueError("GPS time %d not covered by any known epoch" % gps)
