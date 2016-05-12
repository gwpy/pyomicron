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

"""Condor interaction utilities
"""

import os.path
import re
import datetime
import time
from time import sleep
from os import stat
from glob import glob
from getpass import getuser

import htcondor

import numpy

from glue import pipeline

from .utils import (shell, which)

re_dagman_cluster = re.compile('(?<=submitted\sto\scluster )[0-9]+')

JOB_STATUS = [
    'Unexpanded',
    'Idle',
    'Running',
    'Removed',
    'Completed',
    'Held',
    'Submission error',
]
JOB_STATUS_MAP = dict((v.lower(), k) for k, v in enumerate(JOB_STATUS))


JOB_UNIVERSE = [
    'Min',
    'Standard',
    'Pipe',
    'Linda',
    'PVM',
    'Vanilla',
    'PVMD',
    'Scheduler',
    'MPI',
    'Grid',
    'Java',
    'Parallel',
    'Local',
    'Max',
]


def submit_dag(dagfile, *arguments, **options):
    """Submit a DAG to condor and return the cluster ID

    Parameters
    ----------
    dagfile : `str`
        path to DAG file for submission
    *arguments
        other command-line arguments to pass directly to condor_submit_dag
    **options
        other `(key, value)` pairs to append to the condor_submit_dag
        command

    Returns
    -------
    cluster : `int`
        the cluster ID for the newly submitted DAG

    Raises
    ------
    subprocess.CalledProcessError
        if the call to `condor_submit_dag` fails for some reason
    """
    cmd = [which('condor_submit_dag')] + list(arguments)
    for opt, val in options.iteritems():
        cmd.extend([opt, val])
    cmd.append(dagfile)
    print("$ %s"  % ' '.join(cmd))
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
    while True:
        try:
            status = get_dag_status(clusterid, schedd=schedd, detailed=True)
        except IOError as e:
            try:
                status = get_dag_status(clusterid, schedd=schedd,
                                        detailed=True)
            except IOError:
                raise e
        yield status
        if 'exitcode' in status:
            break
        sleep(interval)


def get_dag_status(dagmanid, schedd=None, detailed=True):
    """Return the status of a given DAG

    Parameters
    ----------
    dagmanid : `int`
        the ClusterId of the DAG
    schedd : `htcondor.Schedd`, optional
        the open connection to the scheduler
    detailed : `bool`, optional
        check jobs as held

    Returns
    -------
    status : `dict`
        a `dict` summarising the DAG status with the following keys

        - 'total': the total number of jobs
        - 'done': the number of completed jobs
        - 'queued': the number of queued jobs (excluding held if `held=True`)
        - 'ready': the number of jobs ready to be submitted
        - 'unready': the number of jobs not ready to be submitted
        - 'failed': the number of failed jobs
        - 'held': the number of failed jobs (only non-zero if `held=True`)

        Iff the DAG is completed, the 'exitcode' of the DAG will be included
        in the returned status `dict`
    """
    # connect to scheduler
    if schedd is None:
        schedd = htcondor.Schedd()
    # find running DAG job
    states = ['total', 'done', 'queued', 'ready', 'unready', 'failed']
    classads = ['DAG_Nodes%s' % s.title() for s in states]
    try:
        job = schedd.query('ClusterId == %d' % dagmanid, classads)[0]
    # DAG has exited
    except IndexError:
        sleep(1)
        try:
            job = list(schedd.history('ClusterId == %d' % dagmanid,
                                      classads+['ExitCode'], 1))[0]
        except IOError:  # try again
            job = list(schedd.history('ClusterId == %d' % dagmanid,
                                      classads+['ExitCode'], 1))[0]
        except KeyError:  # condor_rm not finished yet (probably)
            sleep(10)
            job = list(schedd.history('ClusterId == %d' % dagmanid,
                                      classads+['ExitCode'], 1))[0]
        except RuntimeError as e:
            if 'timeout' in str(e).lower() or 'cowardly' in str(e).lower()
                job = get_condor_history_shell(
                    'ClusterId == %d' % dagmanid,
                    classads+['ExitCode'], 1)[0]
                job = dict((k, int(v)) for k, v in job.iteritems())
            else:
                raise
        history = dict((s, job[c]) for s, c in zip(states, classads))
        history['exitcode'] = job['ExitCode']
        history['held'] = history['running'] = history['idle'] = 0
        return history
    # DAG is running, get status
    else:
        status = dict((s, job[c]) for s, c in zip(states, classads))
        # find node status details
        if detailed:
            status['held'] = 0
            status['running'] = 0
            status['idle'] = 0
            nodes = schedd.query('DAGManJobId == %d' % dagmanid)
            for node in nodes:
                if dict(node)['JobStatus'] == JOB_STATUS_MAP['held']:
                    status['held'] += 1
                elif dict(node)['JobStatus'] == JOB_STATUS_MAP['running']:
                    status['running'] += 1
                elif dict(node)['JobStatus'] == JOB_STATUS_MAP['idle']:
                    status['idle'] += 1
        return status


def get_job_duration_history_shell(classad, value, user=getuser(),
                                   maxjobs=None):
    """Return the durations of history condor jobs

    This method calls to `condor_history` in the shell.

    Parameters
    ----------
    classad : `str`
        name of classad providing unique identifier for job type
    value :
        value of classad
    user : `str`, optional
        name of submitting user
    maxjobs : `int`, optional
        maximum number of matches to return

    Returns
    -------
    times, durations : `tuple` of `numpy.ndarray`
        two arrays with the job end time and durations of each matched
        condor process
    """
    from gwpy.time import to_gps
    if isinstance(value, str):
        value = '"%s"' % value
    cmd = ['condor_history', '-constraint',
           '\'%s==%s && Owner=="%s"\'' % (classad, value, user),
           '-autof', 'EnteredCurrentStatus',
           '-autof', 'JobStartDate']
    if maxjobs is not None:
        cmd.extend(['-match', str(maxjobs)])
    history = shell(' '.join(cmd), shell=True)
    lines = history.rstrip('\n').split('\n')
    times = numpy.zeros(len(lines))
    jobdur = numpy.zeros(times.size)
    for i, line in enumerate(lines):
        try:
            e, s = map(int, line.split())
        except ValueError:
            times = times[:i]
            jobdur = jobdur[:i]
            break
        times[i] = to_gps(datetime.datetime.fromtimestamp(e)) + time.timezone
        jobdur[i] = e - s
    return times, jobdur


def get_job_duration_history(classad, value, user=getuser(), maxjobs=0,
                             schedd=None):
    """Return the durations of history condor jobs

    This method uses the python bindings for `htcondor`, which seems
    to have network transfer limits, do not use for large job numbers
    (>2000), instead use `get_job_duration_history_shell` which calls
    to `condor_history` in the shell.

    Parameters
    ----------
    classad : `str`
        name of classad providing unique identifier for job type
    value :
        value of classad
    user : `str`, optional
        name of submitting user
    maxjobs : `int`, optional
        maximum number of matches to return

    Returns
    -------
    times, durations : `tuple` of `numpy.ndarray`
        two arrays with the job end time and durations of each matched
        condor process
    """
    from gwpy.time import to_gps
    if schedd is None:
        schedd = htcondor.Schedd()
    if isinstance(value, str):
        value = '"%s"' % value
    history = list(schedd.history(
        '%s==%s && Owner=="%s"' % (classad, value, user),
        ['EnteredCurrentStatus', 'JobStartDate'], maxjobs))
    times = numpy.zeros(len(history))
    jobdur = numpy.zeros(len(history))
    for i, h in enumerate(history):
        times[i] = (
            to_gps(datetime.datetime.fromtimestamp(h['EnteredCurrentStatus']))
            + time.timezone)
        jobdur[i] = h['EnteredCurrentStatus'] - h['JobStartDate']
    return times, jobdur


def get_condor_history_shell(constraint, classads, maxjobs=None):
    """Get condor_history from the shell

    Parameters
    ----------
    constraint : `str`
        `str` of the format 'ClassAd == "value"' defining the `-constraint`
        to pass to `condor_history`
    classads : `list` of `str`
        list of class Ad names to get back from `condor_history`
    maxjobs : `int`
        the number of matches to return

    Returns
    -------
    jobs : `list` of `dict`
        list of dicts with same keys as defined by `get_dag_status`
    """
    cmd = ['condor_history', '-constraint', constraint]
    for ad_ in classads:
        cmd.extend(['-autof', ad_])
    if maxjobs:
        cmd.extend(['-match', str(maxjobs)])
    history = shell(' '.join(cmd), shell=True)
    lines = history.rstrip('\n').split('\n')
    jobs = []
    for line in lines:
        values = line.split()
        jobs.append(dict(zip(classads, values)))
    return jobs


def get_out_err_files(dagmanid, exitcode=None, schedd=None, user=getuser(),
                      maxjobs=0):
    """Get the paths of the output and error files for nodes in a given DAG

    Parameters
    ----------
    dagmanid : `int`
        the ClusterId of the DAG
    exitcode : `int`, optional
        return only nodes with this exitcode, or return all nodes if
        `None`
    schedd : `htcondor.Schedd`, optional
        the open connection to the scheduler
    user : `str`, optional
        the name of the user who submitted the DAG, defaults to you
    maxjobs : `int`, optional
        maximum number of condor history records to return, defaults
        to `0` meaning 'all'

    Returns
    -------
    filedict : `dict`
        a `dict` of `(nodeid, [files])` pairs
    """
    if schedd is None:
        schedd = htcondor.Schedd()
    history = list(schedd.history(
        'DAGManJobId==%d && Owner=="%s"' % (dagmanid, user),
        ['ExitCode', 'Out', 'Err', 'ClusterId'], maxjobs))
    out = {}
    for node in history:
        if exitcode is not None and node['ExitCode'] != exitcode:
            continue
        out[node['ClusterId']] = [node['Out'], node['Err']]
    return out


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
