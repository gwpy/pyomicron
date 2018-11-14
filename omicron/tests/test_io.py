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

"""Tests for omicron.io
"""

from .. import (io, const)


def test_get_archive_filename():
    assert io.get_archive_filename('L1:GDS-CALIB_STRAIN', 0, 100) == (
        '%s/L1/GDS_CALIB_STRAIN_OMICRON/00000/'
        'L1-GDS_CALIB_STRAIN_OMICRON-0-100.xml.gz' % const.OMICRON_ARCHIVE)
    assert io.get_archive_filename(
            'L1:GDS-CALIB_STRAIN', 1234567890, 123, archive='/triggers',
            filetag='TEST-TAg', ext='root') == (
        '/triggers/L1/GDS_CALIB_STRAIN_TEST_TAg/12345/'
        'L1-GDS_CALIB_STRAIN_TEST_TAg-1234567890-123.root')
