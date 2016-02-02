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

"""Constants and variables for Omicron processing
"""

import os

# generic parameters
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
ifo = os.getenv('ifo', IFO.lower())
SITE = os.getenv('SITE')
site = os.getenv('site', SITE.lower())

# omicron directories
HOME = os.path.expanduser('~')
OMICRON_BASE = os.path.join(HOME, 'Omicron')
OMICRON_PROD = os.path.join(OMICRON_BASE, 'Prod')
OMICRON_ARCHIVE = os.path.join(HOME, 'triggers')

# omicron channel files
if ifo is not None:
    OMICRON_GROUP_FILE = os.path.join(OMICRON_PROD, '%s-groups.txt' % ifo)
    OMICRON_CHANNELS_FILE = os.path.join(OMICRON_PROD, '%s-channels.txt' % ifo)
else:
    OMICRON_GROUP_FILE = None
    OMICRON_CHANNELS_FILE = None