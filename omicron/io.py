# -*- coding: utf-8 -*-
# Copyright (C) Duncan Macleod (2013)
#
# This file is part of LIGO-Omicron.
#
# LIGO-Omicron is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LIGO-Omicron is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LIGO-Omicron.  If not, see <http://www.gnu.org/licenses/>.

"""Input/Output utilities for Omicron ROOT and LIGO_LW XML files
"""

import warnings
import os.path
import glob

from glue.lal import Cache

from .segments import (Segment, segmentlist_from_tree)


def merge_root_files(inputfiles, outputfile,
                     trees=['segments', 'triggers', 'metadata'],
                     all_metadata=False, strict=True, on_missing='raise'):
    """Merge several ROOT files into a single file

    Parameters
    ----------
    inputfile : `list` of `str`
        the paths of the input ROOT files to merge
    outputfile : `str`
        the path of the output ROOT file to write
    tree : `list` of `str`
        the names of the ROOT Trees to include
    all_metadata : `bool`, default: `False`
        whether to include metadata from all files, or just the first one
        (default)
    strict : `bool`, default: `True`
        only combine contiguous files (as described by the contained segmenets)
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
        if tree == 'metadata' and not all_metadata:
            try:
                chains[tree].Add(inputfiles[0])
            except IndexError:
                pass
        else:
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


def _find_files_in_gps_directory(channel, basepath, gps5, ext, filetag=None):
    """Internal method to glob Omicron files from a directory structure
    """
    ifo, name = channel.split(':', 1)
    n = name.replace('-', '_')
    if filetag and not filetag.startswith('_'):
        filetag = '_%s' % filetag
    elif not filetag:
        filetag = ''
    out = Cache()
    for etgtag in ['Omicron', 'OMICRON']:
        dg = os.path.join(basepath, ifo, '%s_%s' % (n, etgtag), str(gps5))
        for d in glob.iglob(dg):
            g = os.path.join(
                d, '%s-%s%s_%s-*.%s' % (ifo, n, filetag, etgtag, ext))
            out.extend(Cache.from_urls(glob.iglob(g)))
    return out


def find_omicron_files(channel, start, end, basepath, ext='xml.gz',
                       filetag=None):
    """Find Omicron files under a given starting directory
    """
    gps5 = int(str(start)[:5])
    cache = Cache()
    while gps5 <= int(str(end)[:5]):
        cache.extend(_find_files_in_gps_directory(channel, basepath, gps5,
                                                  ext, filetag=filetag))
        gps5 += 1
    return cache.sieve(segment=Segment(start, end))


def find_latest_omicron_file(channel, basepath, ext='xml.gz', filetag=None,
                             gps=None):
    """Find the most recent Omicron file for a given channel
    """
    from gwpy.time import tconvert
    if gps is None:
        gps = tconvert('now').seconds
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
    g = os.path.join(proddir, 'triggers', channel, '*.%s' % ext)
    return Cache.from_urls(glob.iglob(g))
