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
import shutil
import sys
import textwrap
import time
from pathlib import Path

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
__process_name__ = 'archive'

# example channel indir: L1:SUS-PR3_M1_DAMP_T_IN1_DQ
chpat = re.compile(".*/?([A-Z][1-2]):(.+)$")
# example trigger file: L1-SUS_PR3_M1_DAMP_T_IN1_DQ_OMICRON-1336799058-8064.h5
tfpat = re.compile("([A-Z][0-9])-(.+)-(\\d+)-(\\d+)\\.(.*)$")


def process_dir(dir_path, outdir, logger):
    """
    Copy all trigget files to appropriate directory
    @param Path dir_path: input directory
    @param Path outdir: top level output directory eg ${HOME}/triggers
    @return: boolean True if successful
    """
    trig_files = glob.glob(str(dir_path.absolute())+'/*')
    good = 0
    bad = 0

    for tfile in trig_files:
        tf = Path(tfile)
        m = tfpat.match(tf.name)
        if not m:
            logger.warn(f'Non trigger file {tf.name} found in {tf.parent.name}')
            bad += 1
        else:
            ifo = m.group(1)
            chan = m.group(2)
            strt = int(m.group(3))
            dur = int(m.group(4))
            ext = m.group(5)

            otrigdir = outdir / ifo / chan / str(int(strt/1e5))

            logger.debug(f'ifo: [{ifo}], chan: [{chan}], strt: {strt}, ext: [{ext}] -> {str(otrigdir.absolute())}')
            otrigdir.mkdir(mode=0o755, parents=True, exist_ok=True)
            shutil.copy(tfile, str(otrigdir.absolute()))
            good += 1
    return good > 0


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
    parser.add_argument('-i', '--indir', help='Input directory. expecing one or more '
                                              'subdirectories with channel names and the trigger files '
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

    indir = Path(args.indir)
    outdir = Path(args.outdir)
    if not outdir.exists():
        logger.critical(f'The output directory {str(outdir.absolute())} does not exist')
        sys.exit(1)
    possible_dirs = glob.glob(str(indir.absolute()) + '/*')
    logger.info(f'Input directory {args.indir} has {len(possible_dirs)} possible channels')
    dirs = list()
    for pdir in possible_dirs:
        m = chpat.match(pdir)
        if m:
            dir_path = Path(pdir)
            if dir_path.exists() and glob.glob(str(dir_path.absolute()) + '/*'):
                dirs.append(dir_path)
                logger.debug(f'Directory with files added: {dir_path.name}')
    logger.info(f'{len(dirs)} channel directories with files found')
    for dir_path in dirs:
        process_dir(dir_path, outdir, logger)
    # ================================
    elap = time.time() - start_time
    logger.info('run time {:.1f} s'.format(elap))


if __name__ == "__main__":
    main()
