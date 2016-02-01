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

"""Miscellaneous utilities
"""

from __future__ import print_function

import os
import sys
from subprocess import Popen, PIPE, CalledProcessError

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
    proc = Popen(cmd, stdout=stdout, **kwargs)
    out, err = proc.communicate()
    if proc.returncode:
        raise CalledProcessError(proc.returncode, ' '.join(cmd))
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
