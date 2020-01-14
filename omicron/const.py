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
import re
from pathlib import Path

IFO_FQDN_REGEX = {
    "G1": re.compile(r"\.uni-hannover"),
    "H1": re.compile(r"\.ligo-wa"),
    "K1": re.compile(r"\.kagra"),
    "L1": re.compile(r"\.ligo-la"),
    "V1": re.compile(r"\.(virgo|ego-gw)"),
}


# -- generic parameters
try:
    IFO = os.environ['IFO']
except KeyError:
    from socket import getfqdn
    fqdn = getfqdn()
    for _key, _regex in IFO_FQDN_REGEX.items():
        if _regex.search(fqdn):
            IFO = _key.upper()
            break
    else:
        IFO = None
    ifo = os.getenv('ifo', IFO.lower() if IFO else None)
else:
    ifo = os.getenv('ifo', IFO.lower())
SITE = os.getenv('SITE')
site = os.getenv('site', SITE and SITE.lower() or None)

# -- omicron directories
HOME = Path.home()
# where Omicron runs
OMICRON_BASE = HOME / "omicron"
# where Omicron triggers are produced
OMICRON_PROD = OMICRON_BASE / "online"
# archive storage directory
OMICRON_ARCHIVE = HOME / "triggers"
# tag Omicron itself places on XML files
OMICRON_FILETAG = 'OMICRON'

# omicron channel files
if ifo is not None:
    OMICRON_GROUP_FILE = OMICRON_PROD / "{}-groups.txt".format(ifo)
    OMICRON_CHANNELS_FILE = OMICRON_PROD, "{}-channels.txt".format(ifo)
else:
    OMICRON_GROUP_FILE = None
    OMICRON_CHANNELS_FILE = None
