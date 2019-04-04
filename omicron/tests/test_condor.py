# -*- coding: utf-8 -*-
# Copyright (C) Duncan Macleod (2017)
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

import sys
import os.path
import tempfile
from unittest import mock

import pytest

# mock up condor modules for testing purposes
# (so we don't need to have htcondor installed)
from . import (mock_htcondor, mock_classad)
sys.modules['htcondor'] = mock_htcondor  # noqa
sys.modules['classad'] = mock_classad  # noqa

from .. import condor


# -- mock utilities -----------------------------------------------------------

def mock_schedd_factory(jobs):
    class Schedd(mock_htcondor.Schedd):
        _jobs = jobs
    return Schedd


# -- tests --------------------------------------------------------------------

@mock.patch('omicron.condor.find_executable', return_value=sys.executable)
@mock.patch('omicron.condor.check_output',
            return_value=b'1 job(s) submitted to cluster 12345')
def test_submit_dag(shell, which):
    dagid = condor.submit_dag('test.dag')
    assert dagid == 12345


@mock.patch('omicron.condor.find_executable', return_value=sys.executable)
@mock.patch('omicron.condor.check_output',
            return_value=b'1 job(s) submitted to cluster 12345')
def test_submit_dag_append(shell, which):
    condor.submit_dag('test.dag', '-append', '+OmicronDAGMan="GW"')
    assert shell.called_with([sys.executable, '-append',
                              '+OmicronDAGMan="GW"', 'test.dag'])


@mock.patch('omicron.condor.find_executable', return_value=sys.executable)
@mock.patch('omicron.condor.check_output', return_value=b'Something else')
def test_submit_dag_error(shell, which):
    with pytest.raises(AttributeError) as exc:
        condor.submit_dag('test.dag')
    assert str(exc.value).startswith('Failed to extract DAG cluster ID')


@mock.patch('htcondor.Schedd',
            mock_schedd_factory([{'ClusterId': 1}, {'ClusterId': 2}]))
@pytest.mark.parametrize('kwargs, output', [
    ({}, [{'ClusterId': 1}, {'ClusterId': 2}]),
    ({'ClusterId': 1}, [{'ClusterId': 1}]),
    ({'ClusterId': 3}, []),
])
def test_find_jobs(kwargs, output):
    print('kwargs', kwargs)
    print('jobs', condor.find_jobs(**kwargs))
    print('output', output)
    assert condor.find_jobs(**kwargs) == output


@mock.patch('htcondor.Schedd',
            mock_schedd_factory([{'ClusterId': 1}, {'ClusterId': 2}]))
def test_find_job():
    job = condor.find_job(ClusterId=1)
    assert job == {'ClusterId': 1}

    # check 0 jobs returned throws the right error
    with pytest.raises(RuntimeError) as exc:
        condor.find_job(ClusterId=3)
    assert str(exc.value).startswith('No jobs found')

    # check multiple jobs returned throws the right error
    with pytest.raises(RuntimeError) as exc:
        condor.find_job()
    assert str(exc.value).startswith('Multiple jobs found')


@mock.patch('htcondor.Schedd',
            mock_schedd_factory([{'ClusterId': 1, 'JobStatus': 4}]))
def test_get_job_status():
    assert condor.get_job_status(1) == 4


@mock.patch('pathlib.Path.is_file', side_effect=(False, True))
def test_dag_is_running(isfile):
    assert not condor.dag_is_running('test.dag')
    assert condor.dag_is_running('test.dag')


def test_find_rescue_dag():
    with tempfile.NamedTemporaryFile(suffix='.dag.rescue001') as f:
        dagf = os.path.splitext(f.name)[0]
        assert condor.find_rescue_dag(dagf) == f.name
    with pytest.raises(IndexError) as exc:
        assert condor.find_rescue_dag(dagf)
    assert 'No rescue DAG files found' in str(exc.value)
