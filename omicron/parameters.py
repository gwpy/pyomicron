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

"""Read/write/modify Omicron-format parameters files
"""

import configparser
import os.path
import re
from collections import OrderedDict
from datetime import datetime
from getpass import getuser
from math import (ceil, exp, floor, log)

from ligo.segments import (segmentlist as SegmentList, segment as Segment)

from . import (const, utils)
from .segments import integer_segments

CHANNEL_DELIM_REGEX = re.compile(r'[:_-]')
UNUSED_PARAMS = ['state-flag', 'frametype', 'state-channel', 'state-frametype']
OMICRON_PARAM_MAP = {
    'sample-frequency': ('DATA', 'SAMPLEFREQUENCY')
}


class OmicronParameters(configparser.ConfigParser):
    """Custom `configparser.ConfigParser` for Omicron parameters files
    """
    OMICRON_DEFAULTS = OrderedDict()
    OMICRON_DEFAULTS[None] = {
        'PARAMETER': {
            'CLUSTERING': 'TIME',
            'FFTPLAN': 'FFTW_ESTIMATE',
            'TRIGGERRATEMAX': 100000,
        },
        'OUTPUT': {
            'DIRECTORY': os.path.curdir,
            'PRODUCTS': 'triggers',
            'VERBOSITY': 1,
            'FORMAT': 'root xml hdf5',
            'NTRIGGERMAX': 1e7,
        },
        'DATA': {
        },
    }

    def __init__(self, version=None, defaults=dict(), **kwargs):
        configparser.ConfigParser.__init__(self, defaults=defaults, **kwargs)
        if version is None:
            try:
                version = utils.get_omicron_version()
            except KeyError:
                version = utils.OmicronVersion(const.OMICRON_VERSION)
        self.version = version
        self._set_defaults()

    def _set_defaults(self):
        """Set basic defaults for each config section
        """
        for version in self.OMICRON_DEFAULTS:
            if version is not None and self.version < version:
                continue
            for section, params in self.OMICRON_DEFAULTS[version].items():
                try:
                    self.add_section(section)
                except configparser.DuplicateSectionError:
                    pass
                for key, val in params.items():
                    if isinstance(val, tuple):
                        self.set(section, key, ' '.join(map(str, val)))
                    else:
                        self.set(section, key, str(val))

    # -- better option accessors ----------------

    def getlist(self, section, option):
        raw = self.get(section, option)
        return raw.split()

    def getfloats(self, section, option):
        return list(map(float, self.getlist(section, option)))

    def optionxform(self, optionstr):
        return optionstr.upper()

    # -- input/output ---------------------------

    def _read(self, fp, fpname):
        """Read a file either either using INI or Omicron formatting
        """
        if fpname.endswith('.ini'):
            return configparser.ConfigParser._read(self, fp, fpname)
        channels = []
        for line in fp:
            if isinstance(line, bytes):
                line = line.decode()
            if not line.strip() or line[0] in '#;':  # blank
                continue
            sec, key, val = line.rstrip().split(None, 2)
            if sec.lower() == 'data' and key.lower() == 'channels':
                channels.append(val)
            else:
                self.set(sec, key, val)
        if channels:
            self.set('DATA', 'CHANNELS', ' '.join(channels))

    def write(self, fp):
        # write basic
        if fp.name.endswith('.ini'):
            return configparser.ConfigParser.write(self, fp)

        # print header
        print('# Omicron %s parameter file' % self.version, file=fp)
        print('# Written using pyomicron by %s at %s'
              % (getuser(), datetime.now()), file=fp)

        # write omicron-format
        def _write_option(sec, key, val):
            print('{0: <10}'.format(sec.upper()),
                  '{0: <16}'.format(key.upper()),
                  val, file=fp, sep=' ')

        for sec in self.sections():
            print("", file=fp)
            for key, val in self.items(sec):
                if sec.lower() == 'data' and key.lower() == 'channels':
                    for chan in val.split():
                        _write_option(sec, key, chan)
                else:
                    _write_option(sec, key, val)
    write.__doc__ = configparser.ConfigParser.write.__doc__

    def write_distributed(self, directory, nchannels=10):
        """Write multiple parameters files to distribute processing

        This method separates the channels list into blocks of ``nchannels``
        and writes a parameters file for each one into ``directory``.

        Parameters
        ----------
        directory : `str`
            the output directory for the parameters files

        nchannels : `int`, optional, default: ``10``
            the number of channels to insert in each parameters file

        Returns
        -------
        paramfile : `str`
            the file path of the complete parameters.txt file, written for
            reference
        parametermap : `dict`
            a `dict` of ``(filename, channel_list)`` pairs that indicate
            which written file contains which channels
        """
        # get channels list
        channels = self.getlist('DATA', 'CHANNELS')
        with open(os.path.join(directory, 'parameters.txt'), 'w') as f:
            self.write(f)
        tmpcp = self.__class__(version=self.version)
        tmpcp.read([f.name])

        # write files
        files = OrderedDict()
        i = 0
        while i * nchannels < len(channels):
            chans = channels[i * nchannels:(i+1) * nchannels]
            pfile = os.path.join(directory, 'parameters-%d.txt' % i)
            tmpcp.set('DATA', 'CHANNELS', ' '.join(chans))
            with open(pfile, 'w') as f2:
                tmpcp.write(f2)
            files[pfile] = chans
            i += 1
        return f.name, files

    @classmethod
    def from_channel_list_config(cls, config, section, version=None):
        """Read `OmicronParameters` from a LIGO channel list file configuration

        Parameters
        ----------
        config : `configparser.ConfigParser`, `str`
            either a configuration object, or a path to a config file

        section : `str`
            the name of the section to parse

        version : `str`, optional
           the version of Omicron for which this configuration is valid

        Returns
        -------
        parameters : `OmicronParameters`
            an Omicron-format version of the parameters from the configuration
        """
        new = cls(version=version)

        # open and parse config filename
        if isinstance(config, str):
            fn = config
            config = configparser.ConfigParser()
            config.read(fn)

        # reformat from separate low, high to a tuple of values
        for (range_, low_, high_) in [('frequency-range', 'flow', 'fhigh'),
                                      ('q-range', 'qlow', 'qhigh')]:
            if (not config.has_option(section, range_) and
                    config.has_option(section, low_)):
                config.set(
                    section, range_,
                    '%s %s' % (config.getfloat(section, low_),
                               config.getfloat(section, high_)))
            for opt in (low_, high_):
                try:
                    config.remove_option(section, opt)
                except configparser.NoOptionError:
                    pass

        for key, val in config.items(section):
            if key in UNUSED_PARAMS:
                continue
            elif key == 'channels':
                new.set('DATA', 'CHANNELS', ' '.join(val.split()))
            else:
                omikey = ''.join(key.split('-')).upper()
                try:
                    group, attr = OMICRON_PARAM_MAP[key]
                except KeyError:
                    if val in [None, 'None', 'none', '']:  # unset default
                        new.remove_option('PARAMETER', omikey)
                    else:
                        new.set('PARAMETER', omikey, val)
                else:
                    new.set(group, omikey, val)

        # -- get parameters
        # rename 'CHUNKDURATION' -> 'PSDLENGTH'
        try:
            psdlength = new.get('PARAMETER', 'CHUNKDURATION')
        except configparser.NoOptionError:
            pass
        else:
            new.remove_option('PARAMETER', 'CHUNKDURATION')
            new.set('PARAMETER', 'PSDLENGTH', psdlength)
        # combine 'SEGMENTDURATION' and 'OVERLAPDURATION' into 'TIMING'
        try:
            timing = (new.get('PARAMETER', 'SEGMENTDURATION'),
                      new.get('PARAMETER', 'OVERLAPDURATION'))
        except configparser.NoOptionError:
            pass
        else:
            new.remove_option('PARAMETER', 'SEGMENTDURATION')
            new.remove_option('PARAMETER', 'OVERLAPDURATION')
            new.set('PARAMETER', 'TIMING', '%s %s' % timing)

        return new

    # -- utilities ------------------------------

    def validate(self):
        """Validate that Omicron will accept the segment parameters

        Parameters
        ----------
        chunk : `int`
            omicron CHUNKDURATION parameter
        segment : `int`
            omicron SEGMENTDURATION parameter
        overlap : `int`
            omicron OVERLAPDURATION parameter
        frange : `tuple` of `float`
            omicron FREQUENCYRANGE parameter

        Raises
        ------
        AssertionError
            if any of the parameters isn't acceptable for Omicron to process
        """
        # extract parameters (for convenience)
        try:
            sampling = self.getfloat('DATA', 'SAMPLEFREQUENCY')
        except configparser.NoOptionError:
            sampling = None
        try:
            frange = self.getfloats('PARAMETER', 'FREQUENCYRANGE')
        except configparser.NoOptionError:
            frange = None
        chunk = self.getfloat('PARAMETER', 'PSDLENGTH')
        segment, overlap = self.getfloats('PARAMETER', 'TIMING')

        # check parameters are valid
        assert segment <= chunk, (
            "Segment length is greater than chunk length")
        assert overlap <= segment, (
            "Overlap length is greater than segment length")
        assert overlap != 0, "Omicron cannot run with zero overlap"
        assert overlap % 2 == 0, "Padding (overlap/2) is non-integer"
        assert segment >= (2 * overlap), (
            "Overlap is too large, cannot be more than 50%")
        dchunk = chunk - overlap
        dseg = segment - overlap
        assert dchunk % dseg == 0, (
            "Chunk duration doesn't allow an integer number of segments, "
            "%ds too large" % (dchunk % dseg))
        if sampling is None or frange is None:
            return
        if frange[0] < 1:
            x = 10 * floor(sampling / frange[0])
            psdsize = 2 * int(2 ** ceil(log(x) / log(2.)))
        else:
            psdsize = 2 * sampling
        psdlen = psdsize / sampling
        chunkp = chunk * sampling
        overlapp = overlap * sampling
        flow = 5 * sampling / exp(log((chunk - overlap)/4., 2))
        assert (chunkp - overlapp) >= 2 * psdsize, (
            "Chunk duration not large enough to resolve lower-frequency "
            "bound, Omicron needs at least %ds. Minimum lower-frequency bound "
            "for this chunk duration is %.2gHz" % (2 * psdlen + overlap, flow))

    @integer_segments
    def output_segments(self, start, end):
        """Prints the list of processing segments for a given data segment
        """
        # get parameters
        segment, overlap = self.getfloats('PARAMETER', 'TIMING')
        fileduration = segment - overlap
        padding = overlap / 2.

        # build list of file segments
        t = start + padding
        stop = end - padding
        segments = SegmentList()
        while t < stop:
            e = min(t + fileduration, stop)
            segments.append(Segment(t, e))
            t = e
        return segments

    @integer_segments
    def distribute_segment(self, start, end, nperjob=1):
        """Determine processing segments to parallelise an Omicron job

        This function is meant to return a `segmentlist` of job [start, stop)
        times to pass to condor. Each segment will have duration
        `chunk * nperjob` *OR* `chunk * nperjob + remainder` if the remainder
        until the `end` is less than 1 chunk.

        Parameters
        ----------
        start : `int`
            the start GPS time of the Omicron segment

        end : `int`
            the end GPS time of the Omicron segment

        nperjob : `int`
            the number of chunks to put into each job

        Returns
        -------
        jobsegs : :class:`~ligo.segments.segmentlist`
            a `segmentlist` of [start, stop) times over which to distribute
            a single segment under condor
        """
        # get parameters
        chunk = self.getfloat('PARAMETER', 'PSDLENGTH')
        overlap = self.getfloats('PARAMETER', 'TIMING')[1]

        # single small segment
        if end - start <= chunk * 2:
            return SegmentList([Segment(start, end)])

        # multiple larger segments
        out = SegmentList()
        t = start
        while t < end - overlap:
            seg = Segment(t, t)
            c = chunk
            while abs(seg) < chunk * nperjob and seg[1] < end:
                seg = Segment(seg[0], min(seg[1] + c, end))
                c = chunk - overlap
            if abs(seg) < chunk:
                out[-1] += seg
            else:
                out.append(seg)
            t = seg[1] - overlap
        return out

    def output_formats(self):
        return [fmt for fmt in ('root', 'txt', 'xml', 'hdf5') if
                fmt in self.get('OUTPUT', 'FORMAT')]

    def output_files(self, start, end, flatten=False):
        """Prints the list of output files for a given processing segment

        Parameters
        ----------
        start : `int`
            GPS start time of job

        end : `int`
            GPS end time of job

        flatten : `bool`, optional, default: `False`
            return a flat list of file names, rather than the default
            `dict` structure

        Returns
        -------
        files : `dict` of `dicts`
            `dict` of ``(channel, fdict)`` pairs, where ``fdict`` is a `dict`
            of ``(fileformat, filenames)`` pairs.
        """
        segments = self.output_segments(start, end)
        fileformats = self.output_formats()
        extension = {
            'root': 'root',
            'txt': 'txt',
            'xml': 'xml',
            'hdf5': 'h5',
        }

        # build list of files
        outdir = self.get('OUTPUT', 'DIRECTORY')
        out = {}
        for channel in self.getlist('DATA', 'CHANNELS'):
            cstr = CHANNEL_DELIM_REGEX.sub('_', channel).replace('_', '-', 1)
            out[channel] = dict((form, []) for form in fileformats)
            for seg in segments:
                basename = '%s_OMICRON-%d-%d' % (cstr, seg[0], abs(seg))
                for form in fileformats:
                    out[channel][form].append(os.path.join(
                        outdir, channel,
                        '{0}.{1}'.format(basename, extension[form]),
                    ))
        if flatten:  # return a basic list of filenames
            return [f for c in out for form in out[c] for f in out[c][form]]
        return out
