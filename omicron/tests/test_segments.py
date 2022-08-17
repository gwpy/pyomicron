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
from copy import deepcopy
from io import StringIO
from unittest import mock

import pytest

from gwpy.segments import (DataQualityFlag, Segment, SegmentList)

from .. import segments


@pytest.fixture
def seglist():
    return SegmentList([
        Segment(0, 1),
        Segment(1, 2),
        Segment(3, 4),
    ])


def test_read_write_segments(seglist):
    with tempfile.NamedTemporaryFile(mode="w") as tmp:
        segments.write_segments(seglist, tmp)
        tmp.seek(0)
        segs = segments.read_segments(tmp.name)
        assert segs == seglist


def test_get_last_run_segment(seglist):
    tmp = StringIO()
    segments.write_segments(seglist, tmp)
    tmp.seek(0)
    assert segments.get_last_run_segment(tmp) == seglist[-1]


def test_query_state_segments(seglist):
    with mock.patch(
        "omicron.segments.DataQualityFlag.query",
        return_value=DataQualityFlag(active=deepcopy(seglist),
                                     known=[seglist.extent()]),
    ):
        coal = deepcopy(seglist).coalesce()
        assert segments.query_state_segments('X', 0, 10) == coal
        assert segments.query_state_segments(
            'X', 0, 10,
            pad=(1, 1),
        ) == DataQualityFlag(active=coal,
                             known=[coal.extent()]).pad(1, -1).active


@mock.patch(
    "omicron.data.find_frames",
    return_value=["/path/to/A-B-0-10.gwf", "/path/to/C-D-20-10.gwf"],
)
def test_get_frame_segments(find):
    assert segments.get_frame_segments(
        "X",
        "X1_R",
        0,
        100
    ) == SegmentList([Segment(0, 10), Segment(20, 30)])
    assert segments.get_frame_segments(
        "X",
        "X1_R",
        25,
        100,
    ) == SegmentList([Segment(25, 30)])


@pytest.fixture
def mock_coverage_report_request(requests_mock):
    requests_mock.get(
        "https://segments.example.com/report/coverage",
        json={
            'query_information': 'stuff',
            'results': {
                '/dq/X1/TEST-FLAG/1': {
                    'total_known_segments': 1,
                    'total_active_segments': 0,
                    'earliest_known_segment': 0.,
                    'latest_active_segment': 100.,
                    'latest_known_segment': 90.,
                    'earliest_active_segment': 10.,
                },
                '/dq/Y1/TEST-FLAG/1': {
                    'total_known_segments': 2388,
                    'total_active_segments': 2388,
                },
            },
        },
    )
    return requests_mock


def test_get_flag_coverage(mock_coverage_report_request):
    assert segments.get_flag_coverage(
        "X1:TEST-FLAG:1",
        url="https://segments.example.com",
    ) == {
        'total_known_segments': 1,
        'total_active_segments': 0,
        'earliest_known_segment': 0.,
        'latest_active_segment': 100.,
        'latest_known_segment': 90.,
        'earliest_active_segment': 10.,
    }
