#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: nu:ai:ts=4:sw=4

#
#  Copyright (C) 2024 Joseph Areeda <joseph.areeda@ligo.org>
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
The situation is that we run DAGs with many omicron jobs, some of which fail for data dependent reasons that
are valid and permanent but others are transient like network issues that could be resolved with a retry.

This program isun as a post script to allow us to retry the job but return a success code even if it fails
repeatedly so that the DAG completes.
"""
import textwrap
import time

start_time = time.time()

import argparse
import logging
from pathlib import Path
import sys
import traceback

try:
    from ._version import __version__
except ImportError:
    __version__ = '0.0.0'

__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'
__process_name__ = Path(__file__).name

logger = None


def parser_add_args(parser):
    """
    Set up command parser
    :param argparse.ArgumentParser parser:
    :return: None but parser object is updated
    """
    parser.add_argument('-v', '--verbose', action='count', default=1,
                        help='increase verbose output')
    parser.add_argument('-V', '--version', action='version',
                        version=__version__)
    parser.add_argument('-q', '--quiet', default=False, action='store_true',
                        help='show only fatal errors')
    parser.add_argument('--return-code', help='Program return code')
    parser.add_argument('--max-retry', help='condor max retry value')
    parser.add_argument('--retry', help='current try starting at 0')
    parser.add_argument('--log', help='Path for a copy of our logger output')


def main():
    global logger

    log_file_format = "%(asctime)s - %(levelname)s, %(pathname)s:%(lineno)d:  %(message)s"
    log_file_date_format = '%m-%d %H:%M:%S'
    logging.basicConfig(format=log_file_format, datefmt=log_file_date_format)
    logger = logging.getLogger(__process_name__)
    logger.setLevel(logging.DEBUG)

    epilog = textwrap.dedent("""
    This progam is designed to be run as a post script in a Condor DAG. For available arguments see:
    https://htcondor.readthedocs.io/en/latest/automated-workflows/dagman-scripts.html#special-script-argument-macros
    A typical lne in the DAG might look like:
    python omicron_post_script.py -vvv --return $(RETURN) --retry $(RETRY) --max-retry $(MAX_RETRIES) --log
    <path_to_log>
    """)

    parser = argparse.ArgumentParser(description=__doc__, prog=__process_name__, epilog=epilog,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_add_args(parser)
    args = parser.parse_args()
    verbosity = 0 if args.quiet else args.verbose

    if verbosity < 1:
        logger.setLevel(logging.CRITICAL)
    elif verbosity < 2:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    if args.log:
        log = Path(args.log)
        log.parent.mkdir(0o775, exist_ok=True, parents=True)
        file_handler = logging.FileHandler(log, mode='a')
        log_formatter = logging.Formatter(log_file_format, datefmt=log_file_date_format)
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)

    me = Path(__file__).name
    logger.info(f'--------- Running {str(me)}')
    # debugging?
    logger.debug(f'{__process_name__} version: {__version__} called with arguments:')
    for k, v in args.__dict__.items():
        logger.debug('    {} = {}'.format(k, v))

    ret = int(args.return_code)
    retry = int(args.retry)
    max_retry = int(args.max_retry)
    ret = ret if retry < max_retry or ret == 0 else 0
    logger.info(f'returning {ret}')
    return ret


if __name__ == "__main__":
    try:
        ret = main()
    except (ValueError, TypeError, OSError, NameError, ArithmeticError, RuntimeError) as ex:
        print(ex, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        ret = 21

    if logger is None:
        logging.basicConfig()
        logger = logging.getLogger(__process_name__)
        logger.setLevel(logging.DEBUG)
    # report our run time
    logger.info(f'Elapsed time: {time.time() - start_time:.1f}s')
    sys.exit(ret)
