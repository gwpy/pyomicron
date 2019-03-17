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

from __future__ import print_function

import re
import os
from subprocess import Popen, PIPE, CalledProcessError
from distutils.version import StrictVersion

from six import PY2

from . import const


def which(program):
    """Find full path of executable program
    """
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file


def shell(cmd, stdout=PIPE, **kwargs):
    """Execute a commdand in a `subprocess`

    Returns
    -------
    stdout : `str`
        the output (`stdout`) of the command

    Raises
    ------
    subprocess.CalledProcessError
        if the command returns a non-zero exit code
    """
    if isinstance(cmd, (list, tuple)):
        cmdstr = ' '.join(cmd)
    else:
        cmdstr = cmd
    proc = Popen(cmd, stdout=stdout, **kwargs)
    out, err = proc.communicate()
    if proc.returncode:
        raise CalledProcessError(proc.returncode, cmdstr)
    return out


def get_output_directory(args):
    """Return the output directory as parsed from the command-line args
    """
    if args.gps is None and not args.output_dir:
        args.output_dir = os.path.join(const.OMICRON_PROD, args.group)
    elif not args.output_dir:
        start, end = args.gps
        args.output_dir = os.path.join(
            const.OMICRON_PROD, '%s-%d-%d' % (args.group, start, end))
    return os.path.abspath(args.output_dir)


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

    if PY2:
        def __cmp__(self, other):
            if isinstance(other, str):
                other = OmicronVersion(other)
            return StrictVersion.__cmp__(self, other)
    else:
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
        executable = os.path.abspath(executable)
        distdir = os.path.dirname(executable)
        versiondir = os.path.dirname(distdir)
        vstr = os.path.basename(versiondir)
    elif os.getenv('OMICRON_VERSION'):
        vstr = os.environ['OMICRON_VERSION']
    else:
        try:
            vstr = os.path.basename(os.environ['OMICRONROOT'])
        except KeyError as e:
            e.args = ('Cannot parse Omicron version from environment, '
                      'please specify the executable path',)
            raise
    return OmicronVersion(vstr)
