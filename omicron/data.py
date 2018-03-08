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

"""Data utilities for Omicron
"""

import os
import glob
import re
import shutil
import warnings
from functools import wraps

from glue import datafind
from glue.lal import (Cache, CacheEntry)
from glue.segments import (segment as Segment, segmentlist as SegmentList)

re_ll = re.compile('\A[HL]1_ll')
re_gwf_gps_epoch = re.compile('[-\/](?P<gpsepoch>\d+)$')


def connect(host=None, port=None):
    """Open a connection to the datafind server

    Parameters
    ----------
    host : `str`
        the IP/hostname of the server to connect to
    port : `int`
        the port on the server to connect

    Returns
    -------
    connection : `datafind.GWDataFindHTTPConnection`
        an open connection to the server
    """
    if host is None:
        try:
            host = os.environ['LIGO_DATAFIND_SERVER']
        except KeyError:
            host = None
            port = None
        else:
            try:
                host, port = host.rsplit(':', 1)
            except ValueError:
                port = None
            else:
                port = int(port)
    if port == 80:
        cert = None
        key = None
    else:
        cert, key = datafind.find_credential()
    if cert is None:
        return datafind.GWDataFindHTTPConnection(host=host, port=port)
    else:
        return datafind.GWDataFindHTTPSConnection(host=host, port=port,
                                                  cert_file=cert, key_file=key)


def with_datafind_connection(f):
    """Decorate a method to ensure an open connection to the datafind server
    """
    @wraps(f)
    def decorated_method(*args, **kwargs):
        if kwargs.get('connection', None) is None:
            kwargs['connection'] = connect()
        return f(*args, **kwargs)
    return decorated_method


@with_datafind_connection
def get_latest_data_gps(obs, frametype, connection=None):
    """Get the end GPS time of the latest available frame file

    Parameters
    ----------
    obs : `str`
        the initial for the observatory
    frametype : `str`
        the name of the frame type for which to search
    connection : `datafind.GWDataFindHTTPConnection`
        the connection to the datafind server

    Returns
    -------
    gpstime : `int`
        the GPS time marking the end of the latest frame
    """
    if re_ll.match(frametype):
        latest = _find_ll_frames(obs, frametype)[-1]
    try:
        latest = connection.find_latest(obs[0], frametype, urltype='file',
                                        on_missing='error')[0]
        try:
            ngps = len(re_gwf_gps_epoch.search(
                os.path.dirname(latest.path)).groupdict()['gpsepoch'])
        except AttributeError:
            pass
        else:
            while True:
                s, e = latest.segment
                new = latest.path.replace('-%d-' % s, '-%d-' % e)
                new = new.replace('%s/' % str(s)[:ngps], '%s/' % str(e)[:ngps])
                if os.path.isfile(new):
                    latest = CacheEntry.from_T050017(new)
                else:
                    break
    except IndexError as e:
        e.args = ('No %s-%s frames found' % (obs[0], frametype),)
        raise
    return int(latest.segment[1])


def ligo_low_latency_hoft_type(ifo, use_devshm=False):
    """Return the low-latency _h(t)_ frame type for the given interferometer

    Parameters
    ----------
    ifo : `str`
        prefix of IFO to use, e.g. 'L1'
    use_devshm : `bool`, optional
        use type in /dev/shm, default: `False`

    Returns
    -------
    frametype : `str`
        frametype to use for low-latency h(t)
    """
    if use_devshm:
        return '%s_llhoft' % ifo.upper()
    else:
        return '%s_DMT_C00' % ifo.upper()


@with_datafind_connection
def check_data_availability(obs, frametype, start, end, connection=None):
    """Check for the full data availability for this frame type

    Parameters
    ----------
    obs : `str`
        the initial for the observatory
    frametype : `str`
        the name of the frame type for which to search
    start : `int`
        the GPS start time of this search
    end : `int`
        the GPS end time of this search
    connection : `datafind.GWDataFindHTTPConnection`
        the connection to the datafind server

    Raises
    ------
    ValueError
        if gaps are found in the frame archive for the given frame type
    """
    connection.find_frame_urls(obs[0], frametype, start, end, on_gaps='error')


@with_datafind_connection
def find_frames(obs, frametype, start, end, connection=None, **kwargs):
    """Find all frames for the given frametype in the GPS interval

    Parameters
    ----------
    obs : `str`
        the initial for the observatory
    frametype : `str`
        the name of the frame type for which to search
    start : `int`
        the GPS start time of this search
    end : `int`
        the GPS end time of this search
    connection : `datafind.GWDataFindHTTPConnection`
        the connection to the datafind server
    **kwargs
        all other keyword arguments are passed directly to
        `~glue.datafind.GWDataFindHTTPConnection.find_frame_urls`

    Returns
    -------
    cache : `~glue.lal.Cache`
        a cache of frame file locations
    """
    if re_ll.match(frametype):
        return find_ll_frames(obs, frametype, start, end, **kwargs)
    else:
        kwargs.setdefault('urltype', 'file')
        cache = connection.find_frame_urls(obs[0], frametype, start, end,
                                           **kwargs)
        # use latest frame to find more recent frames that aren't in
        # datafind yet, this is quite hacky, and isn't guaranteed to
        # work at any point, but it shouldn't break anything
        try:
            latest = cache[-1]
        except IndexError:  # no frames
            return cache
        try:
            ngps = len(re_gwf_gps_epoch.search(
                os.path.dirname(latest.path)).groupdict()['gpsepoch'])
        except AttributeError:  # no match
            pass
        else:
            while True:
                s, e = latest.segment
                if s >= end:  # dont' go beyond requested times
                    break
                new = latest.path.replace('-%d-' % s, '-%d-' % e)
                new = new.replace('%s/' % str(s)[:ngps], '%s/' % str(e)[:ngps])
                if os.path.isfile(new):
                    latest = CacheEntry.from_T050017(new)
                    cache.append(latest)
                else:
                    break
            return cache


def write_cache(cache, outfile):
    with open(outfile, 'w') as fp:
        cache.tofile(fp)


def find_ll_frames(ifo, frametype, start, end, root='/dev/shm',
                   on_gaps='warn', tmpdir=None):
    """Find all buffered low-latency frames in the given interval

    Parameters
    ----------
    ifo : `str`
        the IFO prefix, e.g. 'L1'
    frametype : `str`
        the frame type identifier, e.g. 'llhoft'
    start : `int`
        the GPS start time of this search
    end : `int`
        the GPS end time of this search
    root : `str`, optional
        the base root for the buffer, defaults to `/dev/shm`
    on_gaps : `str`, optional
        what to do when the found frames don't cover the full span, one of
        'warn', 'raise', or 'ignore'
    tmpdir : `str`, optional
        temporary directory into which to copy files from /dev/shm

        ..note::

           Caller is reponsible for deleting the direcotyr and its
           contents when done with it.

    Returns
    -------
    cache : `~glue.lal.Cache`
        a cache of frame file locations

    .. warning::

       This method is not safe, given that the frames may disappear from
       the buffer before you have had a chance to read them

    """
    seg = Segment(start, end)
    cache = _find_ll_frames(ifo, frametype, root=root).sieve(segment=seg)
    if on_gaps != 'ignore':
        seglist = SegmentList(e.segment for e in cache).coalesce()
        missing = (SegmentList([seg]) - seglist).coalesce()
        msg = "Missing segments:\n%s" % '\n'.join(map(str, missing))
        if missing and on_gaps == 'warn':
            warnings.warn(msg)
        elif missing:
            raise RuntimeError(msg)
    if tmpdir:
        out = []
        if not os.path.isdir(tmpdir):
            os.makedirs(tmpdir)
        for e in cache:
            f = e.path
            new = os.path.join(tmpdir, os.path.basename(e.path))
            shutil.copyfile(e.path, new)
            out.append(new)
        cache = Cache.from_urls(out)
    return cache


def _find_ll_frames(ifo, frametype, root='/dev/shm'):
    if frametype.startswith('%s_' % ifo):
        frametype = frametype.split('_', 1)[1]
    obs = ifo[0]
    globstr = os.path.join(root, frametype, ifo,
                           '%s-%s_%s-*-*.gwf' % (obs, ifo, frametype))
    # don't return the last file, as it might not have been fully written yet
    return Cache.from_urls(sorted(glob.glob(globstr)[:-1]))
