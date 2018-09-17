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

"""Test parameter handling for Omicron
"""

import os
import tempfile
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

import pytest

from compat import unittest

from omicron.parameters import OmicronParameters

TEST_PARAMETERS = b"""
OUTPUT DIRECTORY /tmp/omicron-test
OUTPUT VERBOSTIY 1
DATA CHANNELS L1:CAL-DELTAL_EXTERNAL_DQ
DATA CHANNELS L1:CAL-DARM_CTRL_WHITEN_OUT_DBL_DQ
DATA CHANNELS L1:CAL-DARM_ERR_WHITEN_OUT_DBL_DQ
"""


class ParametersTestCase(unittest.TestCase):

    def create(self, *args, **kwargs):
        return OmicronParameters(*args, **kwargs)

    def test_validate_parameters(self):
        pars = self.create(version='v2r2')
        # test zero overlap
        pars.set('PARAMETER', 'PSDLENGTH', '8')
        pars.set('PARAMETER', 'TIMING', '4 0')
        with pytest.raises(AssertionError) as excinfo:
            pars.validate()
        assert 'cannot run with zero overlap' in str(excinfo)
        # test odd-valued overlap
        pars.set('PARAMETER', 'TIMING', '4 1')
        with pytest.raises(AssertionError) as excinfo:
            pars.validate()
        assert 'Padding (overlap/2) is non-integer' in str(excinfo)
        # test odd-valued overlap
        pars.set('PARAMETER', 'TIMING', '8 6')
        with pytest.raises(AssertionError) as excinfo:
            pars.validate()
        assert 'Overlap is too large, cannot be more than 50%' in str(excinfo)
        # test odd-valued overlap
        pars.set('PARAMETER', 'TIMING', '4 5')
        with pytest.raises(AssertionError) as excinfo:
            pars.validate()
        assert 'Overlap length is greater than segment length' in str(excinfo)
        # test segment duration too long
        pars.set('PARAMETER', 'TIMING', '9 3')
        with pytest.raises(AssertionError) as excinfo:
            pars.validate()
        assert 'Segment length is greater than chunk length' in str(excinfo)

        # tests ahoy
        pars.set('PARAMETER', 'PSDLENGTH', '64')
        pars.set('PARAMETER', 'TIMING', '64 8')
        pars.validate()

        pars.set('PARAMETER', 'PSDLENGTH', '232')
        pars.validate()

        # test chunks and segments match
        pars.set('PARAMETER', 'PSDLENGTH', '128')
        pars.set('PARAMETER', 'TIMING', '65 8')
        with pytest.raises(AssertionError) as excinfo:
            pars.validate()
        assert 'Chunk duration doesn\'t allow an integer' in str(excinfo)

    def test_from_channel_list_config(self):
        cp = ConfigParser()
        section = 'test'
        cp.add_section(section)
        cp.set(section, 'channels', 'X1:TEST-CHANNEL\nX1:TEST-CHANNEL_2')
        cp.set(section, 'flow', '10')
        cp.set(section, 'fhigh', '100')
        with tempfile.NamedTemporaryFile(suffix='.ini', mode='w') as f:
            cp.write(f)
            pars = OmicronParameters.from_channel_list_config(cp, section)
        self.assertListEqual(pars.getlist('DATA', 'CHANNELS'),
                             ['X1:TEST-CHANNEL', 'X1:TEST-CHANNEL_2'])
        self.assertTupleEqual(
            tuple(pars.getfloats('PARAMETER', 'FREQUENCYRANGE')), (10., 100.))

    def test_read_ini(self):
        cp = ConfigParser()
        section = 'DATA'
        cp.add_section(section)
        cp.set(section, 'channels', 'X1:TEST-CHANNEL')
        with tempfile.NamedTemporaryFile(suffix='.ini', mode='w') as f:
            cp.write(f)
            f.seek(0)
            pars = self.create()
            pars.read(f.name)
        self.assertListEqual(pars.getlist('DATA', 'CHANNELS'),
                             ['X1:TEST-CHANNEL'])

    def test_read_txt(self):
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            f.write(TEST_PARAMETERS)
            f.seek(0)
            pars = self.create()
            pars.readfp(f)
        self.assertListEqual(pars.getlist('DATA', 'CHANNELS'),
                             ['L1:CAL-DELTAL_EXTERNAL_DQ',
                              'L1:CAL-DARM_CTRL_WHITEN_OUT_DBL_DQ',
                              'L1:CAL-DARM_ERR_WHITEN_OUT_DBL_DQ'])

    def _test_write(self, suffix):
        pars = self.create()
        pars.set('DATA', 'CHANNELS',
                 'L1:CAL-DELTAL_EXTERNAL_DQ '
                 'L1:CAL-DARM_CTRL_WHITEN_OUT_DBL_DQ')
        pars.set('PARAMETER', 'PSDLENGTH', '124')
        pars.set('PARAMETER', 'TIMING', '64 4')
        with tempfile.NamedTemporaryFile(suffix=suffix, mode='w') as f:
            pars.write(f)
            f.seek(0)
            p2 = self.create()
            p2.read(f.name)
        self.assertEqual(pars.get('DATA', 'CHANNELS'),
                         p2.get('DATA', 'CHANNELS'))
        self.assertTupleEqual(tuple(p2.getfloats('PARAMETER', 'TIMING')),
                              (64.0, 4.0))

    def test_write_ini(self):
        self._test_write('.ini')

    def test_write_txt(self):
        self._test_write('.txt')

    def test_write_distributed(self):
        pars = self.create()
        stub = 'X1:TEST_CHANNEL_%d'
        channels = [stub % i for i in range(50)]
        pars.set('PARAMETER', 'PSDLENGTH', '100')
        pars.set('DATA', 'CHANNELS', ' '.join(channels))
        tmpdir = tempfile.gettempdir()
        _, files = pars.write_distributed(tmpdir, nchannels=10)
        for i, f in enumerate(files):
            cset = channels[i*10: (i+1)*10]
            p2 = self.create()
            p2.read(f)
            self.assertListEqual(cset, p2.getlist('DATA', 'CHANNELS'))
            self.assertEqual(p2.getfloat('PARAMETER', 'PSDLENGTH'), 100)
            os.remove(f)

    def test_output_segments(self):
        pars = self.create(version='v2r2')
        pars.set('PARAMETER', 'TIMING', '64 4')
        segs = pars.output_segments(0, 100)
        self.assertListEqual(segs, [(2, 62), (62, 98)])

    def test_distribute_segments(self):
        pars = self.create(version='v2r2')
        pars.set('PARAMETER', 'TIMING', '64 4')
        pars.set('PARAMETER', 'PSDLENGTH', '124')
        segs = pars.distribute_segment(0, 1000, nperjob=4)
        self.assertListEqual(segs, [(0, 604), (600, 1000)])

    def test_output_files(self):
        pars = self.create(version='v2r2')
        pars.set('PARAMETER', 'TIMING', '64 4')
        pars.set('DATA', 'CHANNELS', 'X1:TEST-CHANNEL')
        files = pars.output_files(0, 100)
        self.assertDictEqual(
            files,
            {'X1:TEST-CHANNEL': {
                 'root': [
                     './X1:TEST-CHANNEL/X1-TEST_CHANNEL_OMICRON-2-60.root',
                     './X1:TEST-CHANNEL/X1-TEST_CHANNEL_OMICRON-62-36.root',
                 ],
                 'xml': [
                     './X1:TEST-CHANNEL/X1-TEST_CHANNEL_OMICRON-2-60.xml',
                     './X1:TEST-CHANNEL/X1-TEST_CHANNEL_OMICRON-62-36.xml',
                 ],
            }},
        )
