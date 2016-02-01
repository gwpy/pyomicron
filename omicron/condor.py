# -*- coding: utf-8 -*-
# Copyright (C) Duncan Macleod (2013)
#
# This file is part of LIGO-Omicron.
#
# LIGO-Omicron is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LIGO-Omicron is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LIGO-Omicron.  If not, see <http://www.gnu.org/licenses/>.

"""Condor interaction utilities
"""

import os.path
import re
from time import sleep
from os import stat
from glob import glob

import htcondor

from glue import pipeline

from .utils import (shell, which)

re_dagman_cluster = re.compile('(?<=submitted\sto\scluster )[0-9]+')


def submit_dag(dagfile, force=False):
    """Submit a DAG to condor and return the cluster ID

    Parameters
    ----------
    dagfile : `str`
        path to DAG file for submission
    force : `bool`, default: `False`
        add `-force` to `condor_submit_dag` command

    Returns
    -------
    cluster : `int`
        the cluster ID for the newly submitted DAG

    Raises
    ------
    subprocess.CalledProcessError
        if the call to `condor_submit_dag` fails for some reason
    """
    cmd = [which('condor_submit_dag')]
    if force:
        cmd.append('-force')
    cmd.append(dagfile)
    out = shell(cmd)
    print(out)
    try:
        return int(re_dagman_cluster.search(out).group())
    except (AttributeError, IndexError, TypeError) as e:
        e.args = ('Failed to extract DAG cluster ID from '
                  'condor_submit_dag output',)
        raise


def monitor_dag(dagfile, interval=5):
    """Monitor the status of a DAG by watching the .lock file
    """
    lock = '%s.lock' % dagfile
    stat(lock)
    while True:
        sleep(interval)
        try:
            stat(lock)
        except OSError:
            break
    try:
        find_rescue(dagfile)
    except IndexError:
        return


def find_rescue_dag(dagfile):
    """Find the most recent rescue DAG related to this DAG

    Returns
    -------
    rescue : `str`
        the path to the highest-enumerated rescue DAG

    Raises
    ------
    IndexError
        if no related rescue DAG files are found
    """
    try:
        return sorted(glob('%s.rescue[0-9][0-9][0-9]'))[-1]
    except IndexError as e:
        e.args = ('No rescue DAG files found',)
        raise


def iterate_dag_status(clusterid, interval=2):
    """Monitor a DAG by querying condor for status information periodically
    """
    schedd = htcondor.Schedd()
    states = ['total', 'done', 'queued', 'ready', 'unready', 'failed']
    classads = ['DAG_Nodes%s' % s.title() for s in states]
    while True:
        try:
            job = schedd.query('ClusterId == %d' % clusterid, classads)[0]
        except IndexError:
            job = list(schedd.history('ClusterId == %d' % clusterid,
                                      classads+['ExitCode'], 1))[0]
            history = dict((s, job[c]) for s, c in zip(states, classads))
            history['exitcode'] = job['ExitCode']
            yield history
            break
        else:
            yield dict((s, job[c]) for s, c in zip(states, classads))
            sleep(interval)


# -- custom jobs --------------------------------------------------------------

class OmicronProcessJob(pipeline.CondorDAGJob):
    """`~glue.pipe.CondorJob` as part of Omicron processing
    """
    logtag = '$(cluster)-$(process)'

    def __init__(self, universe, executable, tag=None, subdir=None,
                 logdir=None, **cmds):
        pipeline.CondorDAGJob.__init__(self, universe, executable)
        if tag is None:
            tag = os.path.basename(os.path.splitext(executable)[0])
        if subdir:
            subdir = os.path.abspath(subdir)
            self.set_sub_file(os.path.join(subdir, '%s.sub' % (tag)))
        if logdir:
            logdir = os.path.abspath(logdir)
            self.set_log_file(os.path.join(
                logdir, '%s-%s.log' % (tag, self.logtag)))
            self.set_stderr_file(os.path.join(
                logdir, '%s-%s.err' % (tag, self.logtag)))
            self.set_stdout_file(os.path.join(
                logdir, '%s-%s.out' % (tag, self.logtag)))
        cmds.setdefault('getenv', 'True')
        for key, val in cmds.iteritems():
            if hasattr(self, 'set_%s' % key.lower()):
                getattr(self, 'set_%s' % key.lower())(val)
            else:
                self.add_condor_cmd(key, val)
        # add sub-command option
        self._command = None

    def add_opt(self, opt, value=''):
        pipeline.CondorDAGJob.add_opt(self, opt, str(value))
    add_opt.__doc__ = pipeline.CondorDAGJob.add_opt.__doc__

    def set_command(self, command):
        self._command = command

    def get_command(self):
        return self._command

    def write_sub_file(self):
        pipeline.CondorDAGJob.write_sub_file(self)
        if self.get_command():
            with open(self.get_sub_file(), 'r') as f:
                sub = f.read()
            sub = sub.replace('arguments = "', 'arguments = " %s'
                              % self.get_command())
            with open(self.get_sub_file(), 'w') as f:
                f.write(sub)
