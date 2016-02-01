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

from glue.lal import Cache

from .segments import segmentlist_from_tree


def merge_root_files(inputfiles, outputfile,
                     trees=['segments', 'triggers', 'metadata'],
                     all_metadata=False, strict=True):
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
