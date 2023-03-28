#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) Louisiana State University (2016, 2017)
#               Cardiff University (2017-2020)
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

"""Print Omicron events or file locations
"""

import argparse
import operator
import sys
from getpass import getuser

from gwpy.table import EventTable
from gwpy.table.filter import parse_column_filters
from gwpy.table.filters import in_segmentlist
from gwpy.time import to_gps

from .. import (io, const, __version__)
from omicron.data import write_cache
from omicron.segments import (Segment, SegmentList, cache_segments)

__author__ = 'Duncan Macleod <duncan.macleod@ligo.org>'

BASEPATH = str(const.OMICRON_ARCHIVE).replace(getuser(), 'detchar')

MATH_OPERATORS = {
    '<': operator.lt,
    '<=': operator.le,
    '=': operator.eq,
    '>=': operator.ge,
    '>': operator.gt,
    '==': operator.is_,
    '!=': operator.is_not,
}
MATH_OPERATORS_NOT = {
    '<': operator.ge,
    '<=': operator.gt,
    '=': operator.ne,
    '>=': operator.lt,
    '>': operator.le,
    '==': operator.is_not,
    '!=': operator.is_,
}


# -- parse command line -------------------------------------------------------

def create_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version=__version__,
    )

    parsers = parser.add_subparsers(
        dest='mode',
        title='run modes',
        description='What kind of data you want to print, run '
                    '`omicron-show {mode} --help` for detailed help',
    )

    # -- common options
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        'channel',
        help='name of channel',
    )
    shared.add_argument(
        'gpsstart',
        type=to_gps,
        help='GPS start time of search',
    )
    shared.add_argument(
        'gpsend',
        type=to_gps,
        help='GPS end time of search',
    )
    fopts = shared.add_argument_group('file discovery options')
    fopts.add_argument(
        '-b',
        '--base-directory',
        default=BASEPATH,
        help='base directory for file search',
    )
    fopts.add_argument(
        '-g',
        '--gaps',
        action='store_true',
        default=False,
        help='check for gaps in the recovered files and return '
             'exitcode as follows: 0, no gaps found; '
             '1, some files found with gaps',
    )
    fopts.add_argument(
        '-t',
        '--file-type',
        default='xml.gz',
        choices=['root', 'xml.gz', 'h5'],
        help='type of files to find',
    )

    # -- print files
    fparser = parsers.add_parser(
        'files',
        description='Print the locations of Omicron event files',
        formatter_class=parser.formatter_class,
        parents=[shared],
        help='print file paths',
    )
    fparser.add_argument(
        '-l',
        '--lal-cache',
        action='store_true',
        default=False,
        help='format output for use as a LAL cache file',
    )

    # -- print events
    eparser = parsers.add_parser(
        'events',
        description='Print Omicron events in ASCII format',
        formatter_class=parser.formatter_class,
        parents=[shared],
        help='print events in ASCII format',
    )
    eparser.add_argument(
        '-c',
        '--column',
        action='append',
        type=str,
        default=[],
        help='name of column to print (give multiple times)',
    )
    eparser.add_argument(
        '-r',
        '--rank-by',
        help='name of column by which to sort',
    )
    eparser.add_argument(
        '-x',
        '--condition',
        action='append',
        default=[],
        type=parse_column_filters,
        help='mathematical condition on a column value, e.g. '
             '"snr>5" or "100<peak_frequency<200"',
    )
    eparser.add_argument(
        '-d',
        '--delimiter',
        default=' ',
        help='delimiter for output',
    )
    eparser.add_argument(
        '-n',
        '--max-events',
        default=None,
        metavar='N',
        type=int,
        help='print at most N events',
    )
    eparser.add_argument(
        '-R',
        '--reverse-rank',
        action='store_true',
        default=False,
        help='rank events in reverse (lowest value of rank_by first)',
    )

    return parser


def main(args=None):

    # -- parse args and simplify variables
    parser = create_parser()
    args = parser.parse_args(args=args)
    start = int(args.gpsstart)
    end = int(args.gpsend)
    gaps = args.gaps

    # -- find files -----------------------------------------------------------

    # build segment list (placeholder for allowing custom states, perhaps)
    segs = SegmentList([Segment(start, end)])

    cache = []
    for seg in segs:
        cache.extend(io.find_omicron_files(
            args.channel, start, end, args.base_directory, ext=args.file_type))

    # find gaps
    known = cache_segments(cache) & segs
    if gaps:
        gaps = segs - known
    if not known:
        raise RuntimeError("No files found for required interval")
    elif gaps:
        print("Missing segments:", file=sys.stderr)
        for seg in gaps:
            print("%f %f" % seg, file=sys.stderr)

    # -- print files ----------------------------------------------------------

    if args.mode == 'files':
        if args.lal_cache:
            write_cache(cache, sys.stdout)
        else:
            for path in cache:
                print(path)
        if gaps:
            sys.exit(1)
        sys.exit(0)

    # -- read events ----------------------------------------------------------

    # set default columns
    if not args.column and args.file_type == 'xml.gz':
        args.column = ['peak', 'peak_frequency', 'snr']
    elif not args.column:
        args.column = ['time', 'frequency', 'snr']

    # read events (with simple filter on segments)
    if args.file_type == 'xml.gz':
        cname = args.channel.split(':', 1)[1]
        events = EventTable.read(
            cache,
            format='ligolw',
            tablename='sngl_burst',
            selection=[
                ('peak', in_segmentlist, segs),
                'channel == "{0}"'.format(cname),
            ],
            columns=set(args.column + ['peak', 'channel']),
        )
    elif args.file_type == 'root':
        events = EventTable.read(
            cache,
            format='root',
            treename='triggers',
            selection=('time', in_segmentlist, segs),
            columns=set(args.column + ['time']),
        )
    else:
        full = EventTable.read(cache, format='hdf5', path='triggers')
        events = full.filter(('time', in_segmentlist, segs))[args.column]

    # apply conditions
    if args.conditions:
        events = events.filter(*(x for cond in args.condition for x in cond))

    # sort events
    if args.rank_by:
        events.sort(args.rank_by)
        if not args.reverse_rank:
            events = events[::-1]

    # limit events
    if args.max_events:
        events = events[:args.max_events]

    # print events
    print("#%s" % args.delimiter.join(args.column))
    for e in events:
        print(args.delimiter.join(map(str, (e[col] for col in args.column))))


if __name__ == "__main__":
    main()
