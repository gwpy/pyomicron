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
from functools import wraps

from glue import datafind


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
    try:
        latest = connection.find_latest(obs[0], frametype, urltype='file',
                                        on_missing='error')[0]
    except IndexError as e:
        e.args = ('No %s-%s frames found' % (obs[0], frametype),)
        raise
    return int(latest.segment[1])


def ligo_low_latency_hoft_type(ifo):
    """Return the low-latency _h(t)_ frame type for the given interferometer
    """
    return '%s_ER_C00_L1' % ifo.upper()


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
    kwargs.setdefault('urltype', 'file')
    return connection.find_frame_urls(obs[0], frametype, start, end, **kwargs)


def write_cache(cache, outfile):
    with open(outfile, 'w') as fp:
        cache.tofile(fp)
