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
from tempfile import gettempdir
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

from compat import unittest

from omicron.parameters import (validate_parameters, generate_parameters_files)


class ParametersTestCase(unittest.TestCase):
    def test_validate_parameters(self):
        # test non-zero overlap
        self.assertRaises(AssertionError, validate_parameters, 4, 4, 0)
        # test even-numbered overlap
        self.assertRaises(AssertionError, validate_parameters, 4, 4, 1)
        # test maximum 50% overlap
        self.assertRaises(AssertionError, validate_parameters, 4, 4, 3)
        # test chunk duration >= segment duration
        self.assertRaises(AssertionError, validate_parameters, 4, 5, 2)
        # tests ahoy
        validate_parameters(64, 64, 8)
        validate_parameters(232, 64, 8)
        self.assertRaises(AssertionError, validate_parameters, 128, 65, 8)

    def test_generate_parameters_files(self):
        remove = []
        cp = ConfigParser()
        section = 'test'
        cp.add_section(section)
        cp.set(section, 'channels', 'X1:TEST-CHANNEL')
        # test simple generation
        remove.extend(
            generate_parameters_files(cp, section, 'cache.lcf', gettempdir()))
        # test q-range
        qrange = (10., 20.)
        cp.set(section, 'qlow', str(qrange[0]))
        cp.set(section, 'qhigh', str(qrange[1]))
        remove.extend(
            generate_parameters_files(cp, section, 'cache.lcf', gettempdir()))
        self.assertEqual(cp.get(section, 'q-range'), '%s %s' % qrange)
        # test multiple channels
        channels = ['X1:TEST-CHANNEL_%d' % i for i in range(100)]
        cp.set(section, 'channels', '\n'.join(channels))
        pars = generate_parameters_files(
            cp, section, 'cache.lcf', gettempdir())
        self.assertEqual(len(pars), len(channels) / 10.)
        pardir = os.path.join(gettempdir(), 'parameters')
        for i, (f, clist) in enumerate(pars):
            fpred = os.path.join(pardir, 'parameters_%d.txt' % i)
            self.assertTrue(os.path.samefile(f, fpred))
            self.assertListEqual(clist, channels[i*10:(i+1)*10])
        # clean up
        rmfiles = set(x[0] for x in remove)
        for f in rmfiles:
            if os.path.isfile(f):
                os.remove(f)
