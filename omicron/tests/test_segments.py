# -*- coding: utf-8 -*-
# Copyright (C) Duncan Macleod (2019)
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

"""Tests for omicron.segments
"""

import tempfile

import pytest

from gwpy.segments import (Segment, SegmentList)

from .. import segments


@pytest.fixture
def seglist():
    return SegmentList([
        Segment(0, 1),
        Segment(1, 2),
        Segment(3, 4),
    ])


def test_read_write_segments(seglist):
    with tempfile.NamedTemporaryFile() as tmp:
        segments.write_segments(seglist, tmp)
        tmp.seek(0)
        segs = segments.read_segments(tmp.name)
        assert segs == seglist
