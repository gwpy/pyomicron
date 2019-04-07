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

"""Miscellaneous utilities
"""

import os
import re
from distutils.version import StrictVersion
from pathlib import Path

from . import const


def get_output_directory(args):
    """Return the output directory as parsed from the command-line args
    """
    return str(get_output_path(args))


def get_output_path(args):
    """Return the output path as parsed from the command-line args
    """
    if args.output_dir is None:
        if args.gps is None:
            dirname = args.group
        else:
            dirname = "{0}-{1[0]}-{1[1]}".format(args.group, args.gps)
        return (const.OMICRON_PROD / dirname).resolve(strict=False)
    return args.output_dir.resolve(strict=False)


# -- version comparison utilities

class OmicronVersion(StrictVersion):
    version_re = re.compile(r'^v(\d+)r(\d+) (p(\d+))? ([ab](\d+))?$',
                            re.VERBOSE)

    def parse(self, vstring):
        match = self.version_re.match(vstring)
        if not match:
            raise ValueError("invalid version number '%s'" % vstring)

        (major, minor, patch, prerelease, prerelease_num) = \
            match.group(1, 2, 4, 5, 6)

        if patch:
            self.version = tuple(map(int, [major, minor, patch]))
        else:
            self.version = tuple(map(int, [major, minor])) + (None,)

        if prerelease:
            self.prerelease = (prerelease[0], int(prerelease_num))
        else:
            self.prerelease = None

    def __str__(self):
        if self.version[2] is None:
            return 'v%sr%s' % (self.version[0], self.version[1])
        else:
            return 'v%sr%sp%s' % (self.version[0], self.version[1],
                                  self.version[2])

    def _cmp(self, other):
        if isinstance(other, str):
            other = OmicronVersion(other)
        return StrictVersion._cmp(self, other)


def get_omicron_version(executable=None):
    """Parse the version number from the Omicron executable path

    Parameters
    ----------
    executable : `str`
        path of Omicron executable

    Returns
    -------
    version : `str`
        the Omicron-format version string, e.g. `vXrY`

    Examples
    --------
    >>> get_omicron_version("/home/detchar/opt/virgosoft/Omicron/v2r1/Linux-x86_64/omicron.exe")
    'v2r1'
    """  # noqa: E501
    if executable:
        executable = Path(executable).resolve()
        vstr = executable.parent.parent.name
    elif os.getenv('OMICRON_VERSION'):
        vstr = os.environ['OMICRON_VERSION']
    else:
        try:
            vstr = Path(os.environ['OMICRONROOT']).name
        except KeyError as e:
            e.args = ('Cannot parse Omicron version from environment, '
                      'please specify the executable path',)
            raise
    return OmicronVersion(vstr)


def astropy_config_path(parent, update_environ=True):
    """Create and return a directory for a temporary astropy config path
    """
    parent = Path(parent)
    astropath = parent / ".config" / "astropy"
    astropath.mkdir(exist_ok=True, parents=True)
    confpath = astropath.parent
    if update_environ:
        os.environ["XDG_CONFIG_HOME"] = str(confpath)
    return confpath
