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

from compat import unittest

from omicron.parameters import validate_parameters


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
