#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: nu:ai:ts=4:sw=4

#
#  Copyright (C) 2022 Joseph Areeda <joseph.areeda@ligo.org>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Part of the pyomicron package this program is used to move merged, coalesced,
trigger files to the archive directory. The logic is needed to maintaain the
standard directory structure:

OUTPUT
======
    ifo
    └──  channel-trigger-type (eg: PEM_EY_TILT_VEA_FLOOR_X_DQ_OMICRON/)
        └──  metric-day (GPStime/100000)

The input directory must be in the form used by pyomicron:

INPUT
=====
    merge
    └──   channel (eg: L1:GDS-CALIB_STRAIN/)
        └──  trigger-files (eg: L1-GDS_CALIB_STRAIN_OMICRON-1323748945-1055.h5)
"""
import textwrap
import time

start_time = time.time()
import argparse
import glob
import h5py
import logging
import os
import re

__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'
__version__ = '0.0.1'
__process_name__ = 'omicron_archive'


def main():
    logging.basicConfig()
    logger = logging.getLogger(__process_name__)
    logger.setLevel(logging.DEBUG)

    home = os.getenv('HOME')
    parser = argparse.ArgumentParser(description=textwrap.dedent(__doc__),
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     prog=__process_name__)
    parser.add_argument('-v', '--verbose', action='count', default=1,
                        help='increase verbose output')
    parser.add_argument('-V', '--version', action='version',
                        version=__version__)
    parser.add_argument('-q', '--quiet', default=False, action='store_true',
                        help='show only fatal errors')
    parser.add_argument('-i', '--indir', help='Input directory. expecing one or more'
                                              'subdirectories with channel names. trigger files'
                                              'in those directories',
                        )
    parser.add_argument('-o', '--outdir', help='Top directory for storing files. default: %(default)s',
                        default=f'{home}/triggers')

    args = parser.parse_args()

    verbosity = 0 if args.quiet else args.verbose

    if verbosity < 1:
        logger.setLevel(logging.CRITICAL)
    elif verbosity < 2:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    chpat = re.compile(".*/?([A-Z][1-2]):(.+)$")


    # ================================
    elap = time.time() - start_time
    logger.info('run time {:.1f} s'.format(elap))


if __name__ == "__main__":
    main()
