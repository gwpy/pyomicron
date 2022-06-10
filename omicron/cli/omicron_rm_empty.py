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

"""remove a trigger file if no triggers"""
import time
start_time = time.time()

from pathlib import Path
import shutil
from gwpy.table import EventTable

import argparse
import glob
import h5py
import logging
import os
import re

__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'
__version__ = '0.0.1'
__process_name__ = 'omicron-rm-empty'


def main():
    logging.basicConfig()
    logger = logging.getLogger(__process_name__)
    logger.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(description=__doc__,
                                     prog=__process_name__)
    parser.add_argument('-v', '--verbose', action='count', default=1,
                        help='increase verbose output')
    parser.add_argument('-V', '--version', action='version',
                        version=__version__)
    parser.add_argument('-q', '--quiet', default=False, action='store_true',
                        help='show only fatal errors')
    parser.add_argument('-f', '--flist', help='path to list of files to check')
    parser.add_argument('infiles', nargs='*', help='One or more files to check')

    args = parser.parse_args()

    verbosity = 0 if args.quiet else args.verbose

    if verbosity < 1:
        logger.setLevel(logging.CRITICAL)
    elif verbosity < 2:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    files = list()
    if args.flist:
        with open(args.flist, 'r') as fp:
            for line in fp:
                path = Path(line.strip())
                files.append(path)
    if args.infiles:
        files.extend(args.infile)

    empty_count = 0
    file_count = 0
    cwd = Path.cwd()
    for file in files:
        path = Path(file)
        if path.exists():
            if path.name.endswith('.h5'):
                table = EventTable.read(path, path='/triggers')
            elif path.name.endswith('.xml.gz'):
                table = EventTable.read(path, tablename='sngl_burst')
            elif path.name.endswith('.root'):
                # reading root files fail if there is a : in the name
                os.chdir(path.parent)
                table = EventTable.read(str(path.name), treename='triggers;1')
                os.chdir(cwd)
            file_count += 1
            if len(table) == 0:
                logger.info(f'Empty trigger file: {str(path.absolute())}')
                os.remove(path)
                empty_count += 1

    logger.info(f'{file_count} examined, {empty_count} empty files removed.')
    elap = time.time() - start_time
    logger.info('run time {:.1f} s'.format(elap))


if __name__ == "__main__":
    main()
