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

"""Nagios utilities for PyOmicron
"""

import json as jsonlib
import sys
from getpass import getuser

import htcondor

from gwpy.io.cache import file_segment
from gwpy.time import to_gps

from . import (const, condor)
from .io import find_latest_omicron_file
from .data import get_latest_data_gps
from .segments import get_latest_active_gps

__author__ = "Duncan Macleod <duncan.macleod@ligo.org>"


def nagios_exit_factory(name, author=None, json=False, **kwargs):
    """Create a `nagios_exit` method for a given nagios monitor

    The `nagios_exit` method takes an exitcode (`int`), and a message and
    displays a reponse that is parseable by nagios, either via ntpe or
    the LIGO nagios JSON parser.
    """
    def nagios_exit(exitcode, message, timeout=1800):
        """Exit this program in a nagios-compatible manner

        Parameters
        ----------
        exitcode : `int`
            the exitcode for the nagios message, an integer between 0--3
            (inclusive)
        message : `str`
            the message to print to the screen
        """
        if json:
            out = {
                'created_gps': int(to_gps('now')),
                'status_intervals': [
                    {'start_sec': 0,
                     'end_sec': timeout,
                     'num_status': exitcode,
                     'txt_status': message},
                    {'start_sec': timeout,
                     'num_status': 3,
                     'txt_status': '%s not running' % name},
                ],
            }
            for key in kwargs:
                out[key] = kwargs[key]
            if author is not None:
                author_, email = author.rsplit(' ', 1)
                email = email.strip('<').rstrip('>')
                out['author'] = {'name': author_, 'email': email}
            if isinstance(json, str):
                with open(json, 'w') as f:
                    print(jsonlib.dumps(out), file=f)
            else:
                print(jsonlib.dumps(out))
        else:
            print(message)
        sys.exit(exitcode)
    return nagios_exit


def monitor_condor_status(group, user=getuser()):
    """Check the status of an Omicron Online group process
    """
    schedd = htcondor.Schedd()
    jobs = schedd.query('Owner == "%s" && OmicronManager == "%s"'
                        % (user, group))
    if len(jobs) == 0:
        raise IndexError(
            'No condor processes associated with group %r' % group,)
    elif len(jobs) > 1:
        raise IndexError(
            'Multiple OmicronOnline managers found matching Owner == %r && '
            'OmicronManager == %r' % (user, group))
    try:
        job = dict(jobs[0])
    except ValueError as e:
        e.args = ('Failed to parse condor classads for group %r as dict'
                  % group,)
        raise
    # get status
    try:
        return condor.JOB_STATUS[job['JobStatus']]
    except IndexError as e:
        e.args = ('JobStatus for %d unrecognised' % job['ClusterId'],)


def monitor_dag_status(group, user=getuser()):
    """Check the status of a DAG of Omicron processes

    Parameters
    ----------
    group : `str`
        the name of Omicron channel group to use

    Returns
    -------
    nagios_status : (`int`, `str`)
        an `(exitcode, message)` `tuple` to use as the nagios service status
        for this Omicron DAG
    """
    # find DAGMan process
    schedd = htcondor.Schedd()
    jobs = schedd.query('Owner == "%s" && OmicronDAGMan == "%s"'
                        % (user, group))
    if not len(jobs) == 1:
        return (2, "Not exactly one jobs matching OmicronProcess "
                   "== %r found (%d found)" % (group, len(jobs)))
    # get DAG id and get status
    dagman = dict(jobs[0])
    dagmanid = dagman['ClusterId']
    status = condor.get_dag_status(dagmanid, schedd=schedd, detailed=True)
    if status.get('exitcode', None) == 0:
        return (0, "DAG has completed successfully")
    elif status.get('exitcode', 0) > 0:
        return (2, "DAG has completed with exitcode %d" % status['exitcode'])
    elif status.get('held', 0) > 0:
        return (1, "DAG has %d held jobs" % status['held'])
    elif status['failed'] > 0:
        return (1, "DAG has %d failed jobs" % status['failed'])
    return (0, 'DAG is running [%d/%d complete]'
               % (status['done'], status['total']))


def find_archive_latency(channel, padding, frametype=None, state=None,
                         base=const.OMICRON_ARCHIVE):
    """Find the latency of Omicron file archival for the given channel

    Parameters
    ----------
    channel : `str`
        name of channel
    padding : `int`
        padding parameter for Omicron processing
    frametype : `str`, optional
        frame type ID for data frame files
    state : `str`, optional
        name of DQSegDB flag defining operational state for this channel
    base : `str`, optional
        base directory for Omicron archive

    Returns
    -------
    latency : `dict`
        a `dict` of `(ext, latency)` pairs for each file extension stored in
        the archive ('root', 'xml.gz')
    """
    ifo = channel[:2]
    obs = ifo[0]
    # find latest GPS time
    if state is None and frametype is None:
        raise ValueError("Please give one of `state` or `frametype`")
    if state is None:
        target = get_latest_data_gps(obs, frametype)
    else:
        target = get_latest_active_gps(state)
    target -= padding
    # find latest file
    latency = {}
    for ext in ['root', 'xml.gz']:
        f = find_latest_omicron_file(channel, base, ext=ext)
        end = file_segment(f)[1]
        latency[ext] = (int(target - end), f)
    return latency
