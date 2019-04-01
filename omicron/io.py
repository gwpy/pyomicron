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
from collections import defaultdict

import numpy

from gwpy.io.cache import file_segment
from gwpy.time import tconvert

from . import const
from .segments import (Segment, segmentlist_from_tree)

re_delim = re.compile(r'[:_-]')


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
    for i, (name, chain) in enumerate(chains.items()):
        if i:
            out = ROOT.TFile(outputfile, 'update')  # reopen file
        chain.Merge(out, 0)
    return outputfile


def _parse_channel_and_filetag(channel, filetag):
    """Work out the relevant observatory and description given the inputs
    """
    cname = re_delim.sub('_', str(channel))
    obs, description = cname.split('_', 1)
    if filetag is not None:
        description += '_%s' % re_delim.sub('_', filetag).strip('_')
    return obs, description


def _iter_files_in_gps_directory(channel, basepath, gps5, ext,
                                 filetag=const.OMICRON_FILETAG.upper()):
    """Internal method to glob Omicron files from a directory structure
    """
    ifo, description = _parse_channel_and_filetag(channel, filetag)
    dg = os.path.join(basepath, ifo, description, str(gps5))
    for d in glob.iglob(dg):
        g = os.path.join(
            d, '%s-%s-*.%s' % (ifo, description, ext))
        for path in glob.iglob(g):
            yield path


def find_omicron_files(channel, start, end, basepath, ext='xml.gz',
                       filetag=const.OMICRON_FILETAG.upper()):
    """Find Omicron files under a given starting directory
    """
    gps5 = int(str(start)[:5])-1
    cache = list()
    span = Segment(start, end)
    while gps5 <= int(str(end)[:5]):
        new = _iter_files_in_gps_directory(channel, basepath, gps5,
                                           ext, filetag=filetag)
        cache.extend(path for path in new if
                     file_segment(path).intersects(span))
        gps5 += 1
    return cache


def find_latest_omicron_file(channel, basepath, ext='xml.gz',
                             filetag=const.OMICRON_FILETAG.upper(),
                             gps=None):
    """Find the most recent Omicron file for a given channel
    """
    if gps is None:
        gps = int(tconvert('now'))
    gps5 = int(str(gps)[:5])
    while gps5:
        cache = _iter_files_in_gps_directory(channel, basepath, gps5,
                                             ext, filetag=filetag)
        try:
            return list(cache)[-1]
        except IndexError:
            pass
        gps5 -= 1
    raise RuntimeError("Failed to find any Omicron files for %r" % channel)


def find_pending_files(channel, proddir, ext='xml.gz'):
    """Find files that have just been created, pending archival
    """
    ifo = channel.split(':', 1)[0]
    return glob.glob(os.path.join(
        proddir, 'triggers', channel, '%s-*.%s' % (ifo, ext)))


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

    """  # noqa: E501
    ifo, description = _parse_channel_and_filetag(channel, filetag)
    filename = '%s-%s-%d-%d.%s' % (
        ifo, description, int(start), int(duration), ext)
    if start < 10000:
        gps5 = '%.5d' % int(start)
    else:
        gps5 = str(int(start))[:5]
    return os.path.join(archive, ifo, description, gps5, filename)


def merge_hdf5_files(inputfiles, outputfile, **compression_kw):
    """Merge several HDF5 files into a single file

    Parameters
    ----------
    inputfile : `list` of `str`
        the paths of the input HDF5 files to merge
    outputfile : `str`
        the path of the output HDF5 file to write
    tree : `list` of `str`
        the names of the HDF5 Trees to include
    strict : `bool`, default: `True`
        only combine contiguous files (as described by the contained segmenets)
    on_missing : `str`, optional
        what to do when an input file is not found, one of

        - ``'ignore'``: do nothing
        - ``'warn'``: print a warning
        - ``'raise'``: raise an `IOError`

    Notes
    -----
    This method requires the `HDF5 <https://root.cern.ch/pyroot>`_ package.
    """
    import h5py

    # get list of datasets
    attributes = {}
    datasets = {}
    for path in inputfiles:
        with h5py.File(path, 'r') as h5f:
            attributes = dict(h5f.attrs)
            for dset in h5f:
                # assert datatype is the same, and append shape
                shape = h5f[dset].shape
                dtype = h5f[dset].dtype
                try:
                    shape = numpy.sum(datasets[dset][0] + shape, keepdims=True)
                except KeyError:
                    chunk = shape
                else:
                    assert dtype == datasets[dset][1], (
                        "Cannot merge {0}/{1}, does not match dtype".format(
                            path, dset))
                    if chunk != datasets[dset][2]:
                        chunk = True
                datasets[dset] = (shape, dtype, chunk)

                # use default compression options from this file
                for copt in ('compression', 'compression_opts'):
                    compression_kw.setdefault(copt, getattr(h5f[dset], copt))

    # combine sets
    position = defaultdict(int)
    with h5py.File(outputfile, 'w') as h5out:
        # copy attributes (just from last file)
        for key in attributes:
            h5out.attrs[key] = attributes[key]
        # create datasets
        for dset, (shape, dtype, chunk) in datasets.items():
            h5out.create_dataset(dset, shape=shape, dtype=dtype,
                                 chunks=chunk, **compression_kw)
        # copy dataset contents
        for path in inputfiles:
            with h5py.File(path, 'r') as h5in:
                for dset in datasets:
                    data = h5in[dset]
                    size = data.shape[0]
                    pos = position[dset]
                    h5out[dset][pos:pos+size] = data
                    position[dset] += size

    return outputfile
