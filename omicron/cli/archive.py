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

from gwpy.segments import Segment, SegmentList

start_time = time.time()
import argparse
import glob
import logging
import os
import re

from .. import __version__

__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'
__process_name__ = 'archive'

# example channel indir: L1:SUS-PR3_M1_DAMP_T_IN1_DQ
chpat = re.compile(".*/?([A-Z][1-2]):(.+)$")
# example trigger file: L1-SUS_PR3_M1_DAMP_T_IN1_DQ_OMICRON-1336799058-8064.h5
tfpat = re.compile("([A-Z][0-9])[-_:](.+)-(\\d+)-(\\d+)\\.(.*)$")


def scandir(otrigdir):
    """
    Scan the directory for any trigger files and return coverage as a segment list
    @param Path otrigdir: directory to scan
    @return SegmentList: covering all files
    """
    seg_set = set()
    trig_files = otrigdir.glob('*')
    for tfile in trig_files:
        tf = Path(tfile)
        m = tfpat.match(tf.name)
        if m:
            strt = int(m.group(3))
            dur = int(m.group(4))
            tspan = Segment(strt, strt + dur)
            seg_set.add(tspan)
    segs = list(seg_set)
    segs.sort()
    seg_list = SegmentList(segs)
    return seg_list


def process_dir(dir_path, outdir, logger, keep_files):
    """
    Copy all trigget files to appropriate directory
    @param logger: program's logger
    @param Path dir_path: input directory
    @param Path outdir: top level output directory eg ${HOME}/triggers
    @param boolean keep_files: Do not delete files after copying to archive
    @return: boolean True if successful
    """
    trig_files = glob.glob(str(dir_path.absolute()) + '/*')
    good = 0
    bad = 0
    dest_segs = dict()

    for tfile in trig_files:
        tfile_path = Path(tfile)
        m = tfpat.match(tfile_path.name)
        if not m:
            logger.warn(f'Non trigger file {tfile_path.name} found in {tfile_path.parent.name}')
            bad += 1
        else:
            ifo = m.group(1)
            chan = m.group(2)
            strt = int(m.group(3))
            dur = int(m.group(4))
            ext = m.group(5)
            tspan = Segment(strt, strt + dur)

            otrigdir = outdir / ifo / chan / str(int(strt / 1e5))

            logger.debug(f'Trigger file:\n'
                         f'    {tfile_path.name}\n'
                         f'    ifo: [{ifo}], chan: [{chan}], strt: {strt}, duration: {dur} ext: [{ext}]\n'
                         f'    outdir: {str(otrigdir.absolute())}')

            if str(otrigdir.absolute()) not in dest_segs.keys():
                dest_segs[str(otrigdir.absolute())] = scandir(otrigdir)

            if dest_segs[str(otrigdir.absolute())].intersects_segment(tspan):
                logger.warning(f'{tfile_path.name} ignored because it would overlap')
            else:
                otrigdir.mkdir(mode=0o755, parents=True, exist_ok=True)
                shutil.copy(tfile, str(otrigdir.absolute()))
                if not keep_files:
                    os.remove(tfile_path)
                good += 1
    return good > 0


def main():
    # global logger
    log_file_format = "%(asctime)s - %(levelname)s - %(funcName)s %(lineno)d: %(message)s"
    log_file_date_format = '%m-%d %H:%M:%S'
    logging.basicConfig(format=log_file_format, datefmt=log_file_date_format)
    logger = logging.getLogger(__process_name__)
    logger.setLevel(logging.DEBUG)

    home = Path.home()
    outdir_default = os.getenv('OMICRON_HOME', f'{home}/triggers')
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
                        default=outdir_default)
    parser.add_argument('-k', '--keep-files', default=False, action='store_true',
                        help='Do not delete files after copying them to the archive')

    args = parser.parse_args()

    verbosity = 0 if args.quiet else args.verbose

    if verbosity < 1:
        logger.setLevel(logging.CRITICAL)
    elif verbosity < 2:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    logger.debug("Command line args:")
    for arg in vars(args):
        logger.debug(f'    {arg} = {str(getattr(args, arg))}')

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
        process_dir(dir_path, outdir, logger, args.keep_files)
    # ================================
    elap = time.time() - start_time
    logger.info('run time {:.1f} s'.format(elap))


if __name__ == "__main__":
    main()
