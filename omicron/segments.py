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

import json
import re
from functools import wraps
from math import (floor, ceil)

from dqsegdb2.query import DEFAULT_SEGMENT_SERVER
from dqsegdb2.http import request as dqsegdb2_request

from gwpy.io.cache import (cache_segments as _cache_segments, file_segment)
from gwpy.io.gwf import data_segments as gwf_data_segments
from gwpy.segments import (DataQualityFlag, Segment, SegmentList)
from gwpy.timeseries import (StateTimeSeries, StateVector, TimeSeriesDict)

from . import data

STATE_CHANNEL = {
    # each value of this dict is a 3-tuple:
    #     channel name or guardian node prefix
    #     state bits (or 'guardian')
    #     state frametype

    # GEO600
    "G1:GEO-UP:1": (
        "G1:DER_DATA_QUALITY",
        [0],
        "G1_RDS_C01_L3",
    ),
    "G1:GEO-SCIENCE:1": (
        "G1:DER_DATA_QUALITY",
        [0, 1, 2, 3],
        "G1_RDS_C01_L3",
    ),
    # KAGRA
    "K1:GRD-LSC_LOCK_STATE_N_EQ_1000:1": (
        "K1:DET-DQ_STATE_VECTOR",
        [1],
        "K1_llhoft",
    ),
    # LIGO-Hanford
    "H1:DMT-GRD_ISC_LOCK_NOMINAL:1": (
        "H1:GRD-ISC_LOCK",
        "guardian",
        "H1_R",
    ),
    "H1:DMT-UP:1": (
        "H1:GDS-CALIB_STATE_VECTOR",
        [2],
        "H1_HOFT_C00",
    ),
    "H1:DMT-CALIBRATED:1": (
        "H1:GDS-CALIB_STATE_VECTOR",
        [0],
        "H1_HOFT_C00",
    ),
    "H1:DMT-ANALYSIS_READY:1": (
        "H1:GDS-CALIB_STATE_VECTOR",
        [0, 1, 2],
        "H1_HOFT_C00",
    ),
    # LIGO-Livingston
    "L1:DMT-GRD_ISC_LOCK_NOMINAL:1": (
        "L1:GRD-ISC_LOCK",
        "guardian",
        "L1_R",
    ),
    "L1:DMT-UP:1": (
        "L1:GDS-CALIB_STATE_VECTOR",
        [2],
        "L1_HOFT_C00",
    ),
    "L1:DMT-CALIBRATED:1": (
        "L1:GDS-CALIB_STATE_VECTOR",
        [0],
        "L1_HOFT_C00",
    ),
    "L1:DMT-ANALYSIS_READY:1": (
        "L1:GDS-CALIB_STATE_VECTOR",
        [0, 1, 2],
        "L1_HOFT_C00",
    ),
    # Virgo
    "V1:ITF_NOMINAL_LOCK:1": (
        "V1:DQ_ANALYSIS_STATE_VECTOR",
        [11],
        "V1Online",
    ),
    "V1:ITF_SCIENCE:1": (
        "V1:DQ_ANALYSIS_STATE_VECTOR",
        [0, 1, 2],
        "V1Online",
    ),
}
RAW_TYPE_REGEX = re.compile(r'[A-Z]1_R')


def integer_segments(f):
    @wraps(f)
    def decorated_method(*args, **kwargs):
        segs = f(*args, **kwargs)
        return type(segs)(type(s)(int(s[0]), int(s[1])) for s in segs)
    return decorated_method


def read_segments(source, coltype=int):
    return SegmentList.read(
        source,
        gpstype=coltype,
        format="segwizard",
    )


def get_last_run_segment(segfile):
    return read_segments(segfile, coltype=int)[-1]


def write_segments(segmentlist, outfile, coltype=int):
    return SegmentList(segmentlist).write(
        outfile,
        coltype=coltype,
        format="segwizard",
    )


@integer_segments
def query_state_segments(flag, start, end, url=DEFAULT_SEGMENT_SERVER,
                         pad=(0, 0)):
    """Query a segment database for active segments associated with a flag
    """
    # NOTE: DQF.pad pads forward in time at end
    return DataQualityFlag.query(
        flag, start-pad[0], end+pad[1], url=url,
    ).coalesce().pad(pad[0], -pad[1]).active


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
        from LDAStools import frameCPP  # noqa: F401
    except ImportError:
        pass
    else:
        io_kw['format'] = 'gwf.framecpp'
        if RAW_TYPE_REGEX.match(frametype):
            io_kw['type'] = 'adc'
        elif channel.endswith('GDS-CALIB_STATE_VECTOR'):
            io_kw['type'] = 'proc'

    bits = list(map(str, bits))
    # FIXME: need to read from cache with single segment but doesn't match
    # [start, end)

    # Virgo drops the state vector regularly, so need to sieve the files
    if channel == "V1:DQ_ANALYSIS_STATE_VECTOR":
        span = gwf_data_segments(cache, channel)
    else:
        span = SegmentList([Segment(pstart, pend)])

    # read data segments
    segs = SegmentList()
    try:
        csegs = cache_segments(cache)
    except KeyError:
        return segs
    for seg in csegs & span:
        sv = StateVector.read(cache, channel, nproc=nproc, start=seg[0],
                              end=seg[1], bits=bits, gap='pad', pad=0,
                              **io_kw).astype('uint32')
        segs += sv.to_dqflags().intersection().active

    # truncate to integers, and apply padding
    for i, seg in enumerate(segs):
        segs[i] = type(seg)(int(ceil(seg[0])) + pad[0],
                            int(floor(seg[1])) - pad[1])
    segs.coalesce()

    return segs.coalesce()


@integer_segments
def get_frame_segments(obs, frametype, start, end):
    cache = data.find_frames(obs, frametype, start, end)
    span = SegmentList([Segment(start, end)])
    return cache_segments(cache) & span


@integer_segments
def get_guardian_segments(node, frametype, start, end, nproc=1, pad=(0, 0),
                          strict=False):
    """Determine state segments for a given guardian node
    """
    ifo, node = node.split(':', 1)
    if node.startswith('GRD-'):
        node = node[4:]
    pstart = start - pad[0]
    pend = end + pad[1]

    # find frame cache
    cache = data.find_frames(ifo, frametype, pstart, pend)

    # pre-format data segments
    span = SegmentList([Segment(pstart, pend)])
    segs = SegmentList()
    csegs = cache_segments(cache)
    if not csegs:
        return csegs

    # read data
    stub = "{}:GRD-{}".format(ifo, node)
    if strict:
        channels = ["{}_OK".format(stub)]
    else:
        state = "{}_STATE_N".format(stub)
        nominal = "{}_NOMINAL_N".format(stub)
        active = "{}_ACTIVE".format(stub)
        channels = [state, nominal, active]
    for seg in csegs & span:
        if strict:
            sv = StateVector.read(
                cache, channels[0], nproc=nproc, start=seg[0], end=seg[1],
                bits=[0], gap='pad', pad=0,).astype('uint32')
            segs += sv.to_dqflags().intersection().active
        else:
            gdata = TimeSeriesDict.read(
                cache, channels, nproc=nproc, start=seg[0], end=seg[1],
                gap='pad', pad=0)
            ok = ((gdata[state].value == gdata[nominal].value) &
                  (gdata[active].value == 1)).view(StateTimeSeries)
            ok.t0 = gdata[state].t0
            ok.dt = gdata[state].dt
            segs += ok.to_dqflag().active

    # truncate to integers, and apply padding
    for i, seg in enumerate(segs):
        segs[i] = type(seg)(int(ceil(seg[0])) + pad[0],
                            int(floor(seg[1])) - pad[1])
    segs.coalesce()

    return segs.coalesce()


@integer_segments
def cache_segments(cache):
    return _cache_segments(cache).coalesce()


def segmentlist_from_tree(tree, coalesce=False):
    """Read a `~ligo.segments.segmentlist` from a 'segments' `ROOT.Tree`
    """
    segs = SegmentList()
    for i in range(tree.GetEntries()):
        tree.GetEntry(i)
        segs.append(Segment(tree.start, tree.end))
    return segs


def get_flag_coverage(flag, url=DEFAULT_SEGMENT_SERVER):
    """Return the coverage data for the given flag
    """
    ifo, name, version = flag.rsplit(':', 2)
    flagu = '/dq/%s/%s/%s' % (ifo, name, version)
    raw = dqsegdb2_request('%s/report/coverage' % url)
    return json.loads(raw.read().decode('utf-8'))['results'][flagu]


def get_latest_active_gps(flag, url=DEFAULT_SEGMENT_SERVER):
    """Return the end time of the latest active segment for this flag
    """
    return get_flag_coverage(flag, url=url)['latest_active_segment']


def get_latest_known_gps(flag, url=DEFAULT_SEGMENT_SERVER):
    """Return the end time of the latest known segment for this flag
    """
    return get_flag_coverage(flag, url=url)['latest_known_segment']


@integer_segments
def cache_overlaps(*caches):
    """Find segments of overlap in the given cache sets
    """
    cache = [e for c in caches for e in c]
    cache.sort(key=lambda e: file_segment(e)[0])
    overlap = SegmentList()
    segments = SegmentList()
    for e in cache:
        seg = file_segment(e)
        ol = SegmentList([seg]) & segments
        if abs(ol):
            overlap.extend(ol)
        segments.append(seg)
    return overlap
