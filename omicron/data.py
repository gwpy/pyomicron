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
from pathlib import Path
from urllib.parse import urlparse

import gwdatafind
from gwdatafind.utils import (filename_metadata, file_segment)

from ligo.segments import (segment as Segment, segmentlist as SegmentList)

re_ll = re.compile(r'_(llhoft|lldetchar)\Z')
re_gwf_gps_epoch = re.compile(r'[-\/](?P<gpsepoch>\d+)$')

AGGREGATED_HOFT = {  # map aggregated h(t) type to short h(t) type
    'H1_HOFT_C00': 'H1_DMT_C00',
    'L1_HOFT_C00': 'L1_DMT_C00',
    'V1Online': 'V1_llhoft',
}


# -- utilities ----------------------------------------------------------------

def path_from_file_url(url):
    """Return the path of a `file://` URL
    """
    return urlparse(url).path


def _find_more_files(path):
    """Find more files similar to ``path`` by incrementing the GPS times

    This is mainly to find more files for a given (ifo, type) that aren't (yet)
    in the datafind server cache.

    Parameters
    ----------
    path : `str`
        the path of a file to use as the base, must conform to LIGO-T050017

    Returns
    -------
    morepaths : `list` of `str`
        the list of all files found by walking forward in time
    """
    # parse the GPS epoch from the path
    try:
        ngps = len(re_gwf_gps_epoch.search(
            os.path.dirname(path)).groupdict()['gpsepoch'])
    except AttributeError:
        # this failed, so we can't do anything
        return []
    else:
        found = []
        while True:
            s, e = file_segment(path)
            # replace start time with end time in filename
            new = path.replace('-{start}-'.format(start=s),
                               '-{end}-'.format(end=e))
            # and 5-digit GPS path in directory
            new = new.replace('{start5}/'.format(start5=str(s)[:ngps]),
                              '{end5}/'.format(end5=str(e)[:ngps]))
            # if this file doesn't exist, the previous file is what we want
            if not os.path.isfile(new):
                return found
            # otherwise keep going
            found.append(new)
            path = new


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


def check_data_availability(obs, frametype, start, end):
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

    Raises
    ------
    ValueError
        if gaps are found in the frame archive for the given frame type
    """
    return gwdatafind.find_urls(obs[0], frametype, start, end, on_gaps='error')


def write_cache(cache, outfile):
    if isinstance(outfile, (str, Path)):
        with open(outfile, 'w') as fp:
            return write_cache(cache, fp).name

    for path in cache:
        obs, tag, seg = filename_metadata(path)
        print(
            '{0} {1} {2} {3} {4}'.format(obs, tag, seg[0], abs(seg), path),
            file=outfile)
    return outfile


# -- find files ---------------------------------------------------------------

def find_frames(obs, frametype, start, end, on_gaps='warn', **kwargs):
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
    **kwargs
        all other keyword arguments are passed directly to
        :func:`~gwdatafind.find_urls`

    Returns
    -------
    paths : `list` of `str`
        a list of GWF file pths
    """
    ll_kw = {key: kwargs.pop(key) for key in ('tmpdir', 'root',) if
             key in kwargs}

    cache = _find_frames_datafind(obs, frametype, start, end, on_gaps='ignore',
                                  **kwargs)

    # find more files for low-latency under /dev/shm (or similar)
    if re_ll.search(frametype):
        try:
            latest = file_segment(cache[-1])[1]
        except IndexError:
            latest = start
        if latest < end:
            cache.extend(find_ll_frames(obs, frametype, latest, end, **ll_kw))

    # handle missing files
    if on_gaps != 'ignore':
        seglist = SegmentList(map(file_segment, cache)).coalesce()
        missing = (SegmentList([Segment(start, end)]) - seglist).coalesce()
        msg = "Missing segments:\n%s" % '\n'.join(map(str, missing))
        if missing and on_gaps == 'warn':
            warnings.warn(msg)
        elif missing:
            raise RuntimeError(msg)

    return cache


def _find_frames_datafind(obs, frametype, start, end, **kwargs):
    kwargs.setdefault('urltype', 'file')
    cache = list(map(
        path_from_file_url,
        gwdatafind.find_urls(obs[0], frametype, start, end, **kwargs),
    ))

    # use latest frame to find more recent frames that aren't in
    # datafind yet, this is quite hacky, and isn't guaranteed to
    # work at any point, but it shouldn't break anything
    try:
        latest = cache[-1]
    except IndexError:  # no frames, `cache` is list()
        latestgps = start
    else:
        cache.extend(_find_more_files(latest))
        latestgps = file_segment(cache[-1])[1]

    # if we're searching for aggregated h(t), find more files
    # for the equivalent short h(t) type:
    if frametype in AGGREGATED_HOFT and latestgps < end:
        cache.extend(_find_frames_datafind(
            obs,
            AGGREGATED_HOFT[frametype],
            latestgps,
            end,
            **kwargs
        ))

    return cache


def find_ll_frames(ifo, frametype, start, end, root='/dev/shm', tmpdir=None):
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
    paths : `list` of `str`
        a list of GWF file pths

    .. warning::

       This method is not safe, given that the frames may disappear from
       the buffer before you have had a chance to read them

    """
    seg = Segment(start, end)
    cache = list(filter(lambda x: file_segment(x).intersects(seg),
                        _find_ll_frames(ifo, frametype, root=root)))
    if tmpdir:
        out = []
        if not os.path.isdir(tmpdir):
            os.makedirs(tmpdir)
        for path in cache:
            new = os.path.join(tmpdir, os.path.basename(path))
            shutil.copyfile(path, new)
            out.append(new)
        return out
    return cache


def _find_ll_frames(ifo, frametype, root='/dev/shm', ext='gwf'):
    obs = ifo[0]
    bits = frametype.rsplit('_', 1)
    basedir = os.path.join(root, *bits[::-1])
    globstr = os.path.join(basedir, '{obs}-{frametype}-*-*.{ext}'.format(
        obs=obs, frametype=frametype, ext=ext))
    # don't return the last file, as it might not have been fully written yet
    return sorted(glob.glob(globstr)[:-1])


# -- find latest file ---------------------------------------------------------

def get_latest_data_gps(obs, frametype):
    """Get the end GPS time of the latest available frame file

    Parameters
    ----------
    obs : `str`
        the initial for the observatory
    frametype : `str`
        the name of the frame type for which to search

    Returns
    -------
    gpstime : `int`
        the GPS time marking the end of the latest frame
    """
    try:
        latest = _find_latest_file(obs, frametype)
    except IndexError as e:
        e.args = ('No {0[0]}-{1} frames found'.format(obs, frametype),)
        raise
    # return end time of file as indicated by filename
    return int(file_segment(latest)[1])


def _find_latest_file(obs, frametype):
    # find latest low-latency file using glob
    if re_ll.search(frametype):
        return _find_ll_frames(obs, frametype)[-1]

    # find latest file for short h(t) type preferrably
    if frametype in AGGREGATED_HOFT:
        return _find_latest_file(obs, AGGREGATED_HOFT[frametype])

    # otherwise use gwdatafind to find the latest file it knows about
    latest = gwdatafind.find_latest(obs[0], frametype, urltype='file',
                                    on_missing='error')[-1]

    # and then find more
    try:
        return _find_more_files(latest)[-1]
    except IndexError:
        return latest
