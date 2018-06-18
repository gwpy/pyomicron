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

"""Segment utilities for Omicron
"""

from __future__ import print_function

import shutil
import json
import re
from math import (floor, ceil)
from tempfile import mkdtemp
from functools import wraps

from glue.lal import Cache
from glue.segmentsUtils import fromsegwizard
from glue.segments import (segmentlist as SegmentList, segment as Segment)

from dqsegdb.urifunctions import getDataUrllib2 as dqsegdb_uri_query

from gwpy.segments import DataQualityFlag
from gwpy.timeseries import StateVector

from . import (const, data, utils)

STATE_CHANNEL = {
    'H1:DMT-GRD_ISC_LOCK_NOMINAL:1': ('H1:GRD-ISC_LOCK_OK', [0], 'H1_R'),
    'L1:DMT-GRD_ISC_LOCK_NOMINAL:1': ('L1:GRD-ISC_LOCK_OK', [0], 'L1_R'),
    'H1:DMT-UP:1': ('H1:GDS-CALIB_STATE_VECTOR', [2], 'H1_HOFT_C00'),
    'L1:DMT-UP:1': ('L1:GDS-CALIB_STATE_VECTOR', [2], 'L1_HOFT_C00'),
    'H1:DMT-CALIBRATED:1': ('H1:GDS-CALIB_STATE_VECTOR', [0], 'H1_HOFT_C00'),
    'L1:DMT-CALIBRATED:1': ('L1:GDS-CALIB_STATE_VECTOR', [0], 'L1_HOFT_C00'),
    'H1:DMT-ANALYSIS_READY:1': ('H1:GDS-CALIB_STATE_VECTOR', [0, 1, 2],
                                'H1_HOFT_C00'),
    'L1:DMT-ANALYSIS_READY:1': ('L1:GDS-CALIB_STATE_VECTOR', [0, 1, 2],
                                'L1_HOFT_C00'),
    'V1:ITF_LOCKED:1': ('V1:DQ_ANALYSIS_STATE_VECTOR', [2], 'V1_llhoft'),
    'V1:ITF_SCIENCE:1': ('V1:DQ_ANALYSIS_STATE_VECTOR', [0, 1, 2], 'V1_llhoft'),
}
RAW_TYPE_REGEX = re.compile('[A-Z]1_R')


def integer_segments(f):
    @wraps(f)
    def decorated_method(*args, **kwargs):
        segs = f(*args, **kwargs)
        return type(segs)(type(s)(int(s[0]), int(s[1])) for s in segs)
    return decorated_method


def read_segments(filename, coltype=int):
   with open(filename, 'r') as fp:
        return fromsegwizard(fp, coltype=coltype)


def get_last_run_segment(segfile):
    return read_segments(segfile, coltype=int)[-1]


def write_segments(segmentlist, outfile, coltype=int):
    with open(outfile, 'w') as fp:
       for seg in segmentlist:
           print('%d %d' % seg, file=fp)


@integer_segments
def query_state_segments(flag, start, end, url='https://segments.ligo.org',
                         pad=(0, 0)):
    """Query a segment database for active segments associated with a flag
    """
    segs = DataQualityFlag.query(flag, start-pad[0], end+pad[1], url=url).pad(
        pad[0], -pad[1])  # DQF.pad pads forward in time at end
    segs.coalesce()
    return segs.active


@integer_segments
def get_state_segments(channel, frametype, start, end, bits=[0], nproc=1,
                       pad=(0, 0)):
    """Read state segments from a state-vector channel in the frames
    """
    ifo = channel[:2]
    pstart = start - pad[0]
    pend = end + pad[1]

    # find frame cache
    cache = data.find_frames(ifo, frametype, pstart, pend)

    # optimise I/O based on type and library
    io_kw = {}
    try:
        from LDAStools import frameCPP
    except ImportError:
        if RAW_TYPE_REGEX.match(frametype):
            io_kw.update({'type': 'adc', 'format': 'gwf.framecpp'})

    bits = map(str, bits)
    # FIXME: need to read from cache with single segment but doesn't match
    # [start, end)

    # read data segments
    span = SegmentList([Segment(pstart, pend)])
    segs = SegmentList()
    try:
        csegs = cache.to_segmentlistdict()[ifo[0]]
    except KeyError:
        return segs
    for seg in csegs & span:
        scache = cache.sieve(segment=seg)
        s, e = seg
        sv = StateVector.read(scache, channel, nproc=nproc, start=s, end=e,
                              bits=bits, gap='pad', pad=0,
                              **io_kw).astype('uint32')
        segs += sv.to_dqflags().intersection().active

    # truncate to integers, and apply padding
    for i, seg in enumerate(segs):
        segs[i] = type(seg)(int(ceil(seg[0])) + pad[0],
                            int(floor(seg[1])) - pad[1])
    segs.coalesce()

    # clean up and return
    if data.re_ll.match(frametype):
        shutil.rmtree(tmpdir)
    return segs.coalesce()


@integer_segments
def get_frame_segments(obs, frametype, start, end):
    cache = data.find_frames(obs, frametype, start, end)
    span = SegmentList([Segment(start, end)])
    return cache_segments(cache) & span


@integer_segments
def cache_segments(cache, span=None):
    segmentlist = SegmentList(e.segment for e in
                              cache.checkfilesexist(on_missing='warn')[0])
    return segmentlist.coalesce()


def segmentlist_from_tree(tree, coalesce=False):
    """Read a `~glue.segments.segmentlist` from a 'segments' `ROOT.Tree`
    """
    segs = SegmentList()
    for i in range(tree.GetEntries()):
        tree.GetEntry(i)
        segs.append(Segment(tree.start, tree.end))
    return segs


def get_flag_coverage(flag, url='https://segments.ligo.org'):
    """Return the coverage data for the given flag
    """
    ifo, name, version = flag.rsplit(':', 2)
    flagu = '/dq/%s/%s/%s' % (ifo, name, version)
    raw = dqsegdb_uri_query('%s/report/coverage' % url)
    return json.loads(raw)['results'][flagu]


def get_latest_active_gps(flag, url='https://segments.ligo.org'):
    """Return the end time of the latest active segment for this flag
    """
    return get_flag_coverage(flag, url=url)['latest_active_segment']


def get_latest_known_gps(flag, url='https://segments.ligo.org'):
    """Return the end time of the latest known segment for this flag
    """
    return get_flag_coverage(flag, url=url)['latest_known_segment']


@integer_segments
def cache_overlaps(*caches):
    """Find segments of overlap in the given cache sets
    """
    cache = Cache(e for c in caches for e in c)
    cache.sort(key=lambda e: e.segment[0])
    overlap = SegmentList()
    segments = SegmentList()
    for e in cache:
        ol = SegmentList([e.segment]) & segments
        if abs(ol):
            overlap.extend(ol)
        segments.append(e.segment)
    return overlap
