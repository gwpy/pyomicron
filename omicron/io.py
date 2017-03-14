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

"""Input/Output utilities for Omicron ROOT and LIGO_LW XML files
"""

import warnings
import os.path
import glob
import re

from glue.lal import Cache

from . import const
from .segments import (Segment, segmentlist_from_tree)

re_delim = re.compile('[:_-]')


def merge_root_files(inputfiles, outputfile,
                     trees=['segments', 'triggers', 'metadata'],
                     strict=True, on_missing='raise'):
    """Merge several ROOT files into a single file

    Parameters
    ----------
    inputfile : `list` of `str`
        the paths of the input ROOT files to merge
    outputfile : `str`
        the path of the output ROOT file to write
    tree : `list` of `str`
        the names of the ROOT Trees to include
    strict : `bool`, default: `True`
        only combine contiguous files (as described by the contained segmenets)
    on_missing : `str`, optional
        what to do when an input file is not found, one of

        - ``'ignore'``: do nothing
        - ``'warn'``: print a warning
        - ``'raise'``: raise an `IOError`

    Notes
    -----
    This method requires the `ROOT <https://root.cern.ch/pyroot>`_ package.
    """
    import ROOT
    chains = {}

    # validate input files
    for f in inputfiles:
        missing = not os.path.isfile(f)
        msg = "No such file or directory: %r" % f
        if on_missing == 'ignore':
            pass
        elif missing and on_missing == 'warn':
            warnings.warn(msg)
        elif missing:
            raise IOError(msg)

    for tree in trees:
        chains[tree] = ROOT.TChain(tree)
        for i, f in enumerate(inputfiles):
            chains[tree].Add(f)
        if (strict and tree == 'segments' and
                len(segmentlist_from_tree(chains[tree]).coalesce()) > 1):
            raise RuntimeError("Cannot perform a 'strict' merge on files "
                               "containing discontiguous data")

    # write new file (use 'recreate' to overwrite old file)
    out = ROOT.TFile(outputfile, 'recreate')
    for i, (name, chain) in enumerate(chains.iteritems()):
        if i:
            out = ROOT.TFile(outputfile, 'update')  # reopen file
        chain.Merge(out, 0)
    return outputfile


def root_cache(rootfiles):
    """Return a `~glue.lal.Cache` containing the given ROOT file paths
    """
    out = Cache()
    append = out.append
    for f in rootfiles:
        base = os.path.basename(f)
        stub, start, duration = base[:-5].rsplit('_', 2)
        ifo, description = stub.split(':', 1)
        try:
            ce = type(out).entry_class(
                ' '.join([ifo, description, start, duration, f]))
        except ValueError as e:
            warnings.warn(str(e))
        else:
            append(ce)
    return out


def _parse_channel_and_filetag(channel, filetag):
    """Work out the relevant observatory and description given the inputs
    """
    cname = re_delim.sub('_', str(channel))
    obs, description = cname.split('_', 1)
    if filetag is not None:
        description += '_%s' % re_delim.sub('_', filetag).strip('_')
    return obs, description


def _find_files_in_gps_directory(channel, basepath, gps5, ext,
                                 filetag=const.OMICRON_FILETAG.upper()):
    """Internal method to glob Omicron files from a directory structure
    """
    ifo, description = _parse_channel_and_filetag(channel, filetag)
    out = Cache()
    dg = os.path.join(basepath, ifo, description, str(gps5))
    for d in glob.iglob(dg):
        g = os.path.join(
            d, '%s-%s-*.%s' % (ifo, description, ext))
        out.extend(Cache.from_urls(glob.iglob(g)))
    return out


def find_omicron_files(channel, start, end, basepath, ext='xml.gz',
                       filetag=const.OMICRON_FILETAG.upper()):
    """Find Omicron files under a given starting directory
    """
    gps5 = int(str(start)[:5])-1
    cache = Cache()
    while gps5 <= int(str(end)[:5]):
        cache.extend(_find_files_in_gps_directory(channel, basepath, gps5,
                                                  ext, filetag=filetag))
        gps5 += 1
    return cache.sieve(segment=Segment(start, end))


def find_latest_omicron_file(channel, basepath, ext='xml.gz',
                             filetag=const.OMICRON_FILETAG.upper(),
                             gps=None):
    """Find the most recent Omicron file for a given channel
    """
    from gwpy.time import tconvert
    if gps is None:
        gps = int(tconvert('now'))
    gps5 = int(str(gps)[:5])
    while gps5:
        cache = _find_files_in_gps_directory(channel, basepath, gps5,
                                             ext, filetag=filetag)
        try:
            return cache[-1].path
        except IndexError:
            pass
        gps5 -= 1
    raise RuntimeError("Failed to find any Omicron files for %r" % channel)


def find_pending_files(channel, proddir, ext='xml.gz'):
    """Find files that have just been created, pending archival
    """
    ifo = channel.split(':', 1)[0]
    return Cache.from_urls(glob.iglob(os.path.join(
        proddir, 'triggers', channel, '%s-*.%s' % (ifo, ext))))


def get_archive_filename(channel, start, duration, ext='xml.gz',
                         filetag=const.OMICRON_FILETAG.upper(),
                         archive=const.OMICRON_ARCHIVE):
    """Returns the full file path for this channel's triggers

    This method will design a trigger file path for you, rather than find
    a file that is already there, and so should be used to seed an archive,
    not search it.

    Parameters
    ----------
    channel : `str`
        name of channel
    start : `int`
        GPS start time of file
    duration : `int`
        duration (seconds) of file
    ext : `str`, optional
        file extension, defaults to ``xml.gz``
    filetag : `str`, optional
        filetag to be appended after the channel name, defaults to ``OMICRON``
    archive : `str`, optional
        base directory of the trigger archive, defaults to
        `const.OMICRON_ARCHIVE`

    Returns
    -------
    filepath : `str`
        the absolute path where this file should be stored

    Notes
    -----
    See `T050017 <https://dcc.ligo.org/LIGO-T050017>`_ for details of the
    file-naming convention.

    Examples
    --------
    >>> get_archive_filename('H1:GDS-CALIB_STRAIN', 1234567890, 100, archive='/triggers')
    '/triggers/H1/GDS_CALIB_STRAIN_OMICRON/12345/H1-GDS_CALIB_STRAIN_OMICRON-1234567890-100.xml.gz'

    """
    ifo, description = _parse_channel_and_filetag(channel, filetag)
    filename = '%s-%s-%d-%d.%s' % (
        ifo, description, int(start), int(duration), ext)
    if start < 10000:
        gps5 = '%.5d' % int(start)
    else:
        gps5 = str(int(start))[:5]
    return os.path.join(archive, ifo, description, gps5, filename)
