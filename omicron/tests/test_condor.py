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

# mock up condor modules for testing purposes
# (so we don't need to have htcondor installed)
import sys
import mock_htcondor
import mock_classad
sys.modules['htcondor'] = mock_htcondor
sys.modules['classad'] = mock_classad

import utils
from compat import (unittest, mock)

from omicron import condor


# -- mock utilities -----------------------------------------------------------

def mock_which(exe):
    return '/path/to/executable'


def mock_shell_factory(output):
    def shell(*args, **kwargs):
        return output
    return shell


def mock_schedd_factory(jobs):
    Schedd = mock_htcondor.Schedd
    Schedd._jobs = jobs
    return Schedd


# -- tests --------------------------------------------------------------------

class CondorTests(unittest.TestCase):

    def test_submit_dag(self):
        shell_ = mock_shell_factory('1 job(s) submitted to cluster 12345')
        with mock.patch('omicron.condor.which', mock_which):
            with mock.patch('omicron.condor.shell', shell_):
                dagid = condor.submit_dag('test.dag')
                with utils.capture(condor.submit_dag, 'test.dag', '-append',
                                   '+OmicronDAGMan="GW"') as output:
                    cmd = output.split('\n')[0]
                    self.assertEqual(cmd, '$ /path/to/executable -append '
                                          '+OmicronDAGMan="GW" test.dag')
        self.assertEqual(dagid, 12345)
        shell_ = mock_shell_factory('Error')
        with mock.patch('omicron.condor.which', mock_which):
            with mock.patch('omicron.condor.shell', shell_):
               self.assertRaises(AttributeError, condor.submit_dag, 'test.dag')

    def test_find_jobs(self):
        schedd_ = mock_schedd_factory([{'ClusterId': 1}, {'ClusterId': 2}])
        with mock.patch('htcondor.Schedd', schedd_):
            jobs = condor.find_jobs()
            self.assertListEqual(jobs, [{'ClusterId': 1}, {'ClusterId': 2}])
            jobs = condor.find_jobs(ClusterId=1)
            self.assertListEqual(jobs, [{'ClusterId': 1}])
            jobs = condor.find_jobs(ClusterId=3)
            self.assertListEqual(jobs, [])

    def test_find_job(self):
        schedd_ = mock_schedd_factory([{'ClusterId': 1}, {'ClusterId': 2}])
        with mock.patch('htcondor.Schedd', schedd_):
            job = condor.find_job(ClusterId=1)
            self.assertDictEqual(job, {'ClusterId': 1})
            # check 0 jobs returned throws the right error
            with self.assertRaises(RuntimeError) as e:
                condor.find_job(ClusterId=3)
            self.assertTrue(str(e.exception).startswith('No jobs found'))
            # check multiple jobs returned throws the right error
            with self.assertRaises(RuntimeError) as e:
                condor.find_job()
            self.assertTrue(str(e.exception).startswith('Multiple jobs found'))

    def test_get_job_status(self):
        schedd_ = mock_schedd_factory([{'ClusterId': 1, 'JobStatus': 4}])
        with mock.patch('htcondor.Schedd', schedd_):
            status = condor.get_job_status(1)
            self.assertEqual(status, 4)

    def test_dag_is_running(self):
        self.assertFalse(condor.dag_is_running('test.dag'))
        with mock.patch('os.path.isfile') as isfile:
            isfile.return_value = True
            self.assertTrue(condor.dag_is_running('test.dag'))
        schedd_ = mock_schedd_factory(
            [{'UserLog': 'test.dag.dagman.log'}])
        with mock.patch('htcondor.Schedd', schedd_):
            self.assertTrue(condor.dag_is_running('test.dag'))
            self.assertFalse(condor.dag_is_running('test2.dag'))
