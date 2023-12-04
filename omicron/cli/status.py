#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) Louisiana State University (2016, 2017)
#               Cardiff University (2017-2020)
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

"""Check the status of Omicron trigger generation
"""
import time
prog_start = time.time()

import argparse
import configparser
import json
import logging
import operator
import sys
import warnings
from collections import OrderedDict
from functools import reduce
from getpass import getuser
from os import linesep
from pathlib import Path
from textwrap import indent
from time import sleep

import htcondor

import numpy

from matplotlib import (rcParams, use)
from matplotlib.gridspec import GridSpec

import h5py

from MarkupPy import markup

from gwpy.io.cache import sieve as sieve_cache
from gwpy.time import to_gps
from gwpy.segments import (Segment, SegmentList)
from gwpy.plot import Plot
from gwpy.plot.segments import SegmentRectangle

from .. import (condor, const, io, log, segments, __version__)
from ..utils import get_omicron_version

__author__ = "Duncan Macleod <duncan.macleod@ligo.org>"

NOW = int(to_gps('now'))
logger = None


def create_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version=__version__,
    )
    parser.add_argument(
        'group',
        help='name of channel group to check',
    )
    parser.add_argument(
        '-f',
        '--config-file', default=const.OMICRON_CHANNELS_FILE,
        help='path to a channel list configuration file',
    )
    parser.add_argument(
        '-i',
        '--ifo',
        default=const.IFO,
        help='IFO prefix to process',
    )
    parser.add_argument(
        '-s',
        '--gps-start-time',
        type=to_gps,
        default=NOW - 7 * 86400,
        help='GPS start time of check or date/time',
    )
    parser.add_argument(
        '-e',
        '--gps-end-time',
        type=to_gps,
        default=NOW,
        help='GPS end time of check or date/time',
    )
    parser.add_argument(
        '-c',
        '--channel',
        action='append',
        help='name of channel to process, can be given multiple '
             'times, default: all channels in group',
    )
    parser.add_argument(
        '-b',
        '--state-flag',
        help='name of data-quality flag to use in defining state, '
             'default is taken from --config-file',
    )
    parser.add_argument(
        '-p',
        '--state-pad',
        metavar='X,Y',
        default='0,0',
        help='inward padding for start,end of each '
             '--state-flag segment',
    )
    parser.add_argument(
        '-u',
        '--user',
        default=getuser(),
        help='name of user running condor jobs',
    )
    parser.add_argument(
        '-a',
        '--archive-directory',
        default=const.OMICRON_ARCHIVE,
        help='path of archive',
    )
    parser.add_argument(
        '-d',
        '--production-directory',
        default=const.OMICRON_PROD / "{group}",
        type=Path,
        help='path of production directory',
    )
    parser.add_argument(
        '-A',
        '--skip-condor',
        action='store_true',
        default=False,
        help="don't check condor status",
    )
    parser.add_argument(
        '-B',
        '--skip-file-checks',
        action='store_true',
        default=False,
        help="don't check file status",
    )
    parser.add_argument(
        '-C',
        '--skip-job-duration',
        action='store_true',
        default=False,
        help="don't query and plot job durations",
    )

    pout = parser.add_argument_group('Output options')
    pout.add_argument(
        '--json',
        const=True,
        nargs='?',
        default=False,
        help='print output in dashboard.ligo.org nagios JSON format',
    )
    pout.add_argument(
        '-o',
        '--output-directory',
        default=Path.cwd(),
        type=Path,
        help='path to write output',
    )
    pout.add_argument(
        '-l',
        '--latency-archive-tag',
        default='{group}',
        help='file tag for latency archive',
    )
    pout.add_argument(
        '-m',
        '--html',
        default=False,
        action='store_true',
        help='write HTML summary to index.html in output dir',
    )

    pnag = parser.add_argument_group('Monitoring options')
    pnag.add_argument(
        '-U',
        '--unknown',
        type=int,
        default=7200,
        help='time (seconds) after which nagios output should be '
             'considered stable and \'unknown\'',
    )
    pnag.add_argument(
        '-W',
        '--warning',
        type=int,
        default=3600,
        help='how much latency to consider as a warning',
    )
    pnag.add_argument(
        '-X',
        '--error',
        type=int,
        default=3600 * 2,
        help='how much latency to consider as an error',
    )
    return parser


def main(args=None):
    global logger
    use('agg')
    rcParams.update({
        'figure.subplot.bottom': 0.15,
        'figure.subplot.left': 0.1,
        'figure.subplot.right': 0.83,
        'figure.subplot.top': 0.93,
        'figure.subplot.hspace': 0.25,
        'axes.labelsize': 20,
        'grid.color': 'gray',
    })
    grid = GridSpec(2, 1)

    logger = log.Logger('omicron-status')
    logger.setLevel(logging.DEBUG)

    try:
        omicronversion = str(get_omicron_version())
    except KeyError:
        omicronversion = 'Unknown'
        logger.warning("Omicron version unknown")
    else:
        logger.info("Found omicron version: %s" % omicronversion)

    parser = create_parser()
    args = parser.parse_args(args=args)

    if args.ifo is None:
        parser.error("Cannot determine IFO prefix from system, "
                     "please pass --ifo on the command line")

    group = args.group

    logger.info("Checking status for %r group" % group)

    archive = args.archive_directory
    proddir = args.production_directory.with_name(
        args.production_directory.name.format(group=args.group),
    )
    outdir = args.output_directory
    outdir.mkdir(exist_ok=True, parents=True)
    tag = args.latency_archive_tag.format(group=args.group)

    filetypes = ['h5', 'xml.gz', 'root']

    logger.debug("Set output directory to %s" % outdir)
    logger.debug(
        "Will process the following filetypes: {}".format(
            ", ".join(filetypes),
        ),
    )

    # -- parse configuration file and get parameters --------------------------
    ifo = args.ifo
    if ifo is None:
        raise ValueError('IFO is unknown.')
    if args.config_file is None:
        config_file = const.OMICRON_PROD / f"{ifo}-channels.ini"
    else:
        config_file = args.config_file
    config_file = Path(config_file)
    if not config_file.exists():
        raise IOError(f'Configuration file does not exist: {str(config_file.absolute())}')
    cp = configparser.ConfigParser()
    ok = cp.read(config_file)
    if str(config_file) not in ok:
        raise IOError(f"Failed to read configuration file {str(config_file.absolute())}")
    logger.info("Configuration read")

    # validate
    if not cp.has_section(group):
        raise configparser.NoSectionError(group)

    # get parameters
    obs = args.ifo[0]
    frametype = cp.get(group, 'frametype')
    padding = cp.getint(group, 'overlap-duration') / 2.
    mingap = cp.getint(group, 'chunk-duration')

    channels = args.channel
    if not channels:
        channels = [c.split()[0] for
                    c in cp.get(group, 'channels').strip('\n').split('\n')]
    channels.sort()
    logger.debug("Found %d channels" % len(channels))

    start = args.gps_start_time
    end = args.gps_end_time
    if end == NOW:
        end -= padding

    if args.state_flag:
        stateflag = args.state_flag
        statepad = tuple(map(float, args.state_pad.split(',')))
    else:
        try:
            stateflag = cp.get(group, 'state-flag')
        except configparser.NoOptionError:
            stateflag = None
        else:
            try:
                statepad = tuple(map(
                    float,
                    cp.get(group, 'state-padding').split(','),
                ))
            except configparser.NoOptionError:
                statepad = (0, 0)
    if stateflag:
        logger.debug("Parsed state flag: %r" % stateflag)
        logger.debug("Parsed state padding: %s" % repr(statepad))
    logger.info("Processing %d-%d" % (start, end))

    # -- define nagios JSON printer -------------------------------------------

    def print_nagios_json(code, message, outfile, tag='status', **extras):
        out = {
            'created_gps': NOW,
            'status_intervals': [
                {'start_sec': 0,
                 'end_sec': args.unknown,
                 'num_status': code,
                 'txt_status': message},
                {'start_sec': args.unknown,
                 'num_status': 3,
                 'txt_status': 'Omicron %s check is not running' % tag},
            ],
            'author': {
                'name': 'Duncan Macleod',
                'email': 'duncan.macleod@ligo.org',
            },
            'omicron': {
                'version': omicronversion,
                'group': group,
                'channels': ' '.join(channels),
                'frametype': frametype,
                'state-flag': stateflag,
            },
            'pyomicron': {
                'version': __version__,
            },
        }
        out.update(extras)
        with open(outfile, 'w') as f:
            f.write(json.dumps(out, indent=3))
        logger.debug("nagios info written to %s" % outfile)

    # -- get condor status ------------------------------------------------

    if not args.skip_condor:
        # connect to scheduler
        try:
            schedd = htcondor.Schedd()
        except RuntimeError as e:
            logger.warning("Caught %s: %s" % (type(e).__name__, e))
            logger.info("Failed to connect to HTCondor scheduler, cannot "
                        "determine condor status for %s" % group)
            schedd = None

    if not args.skip_condor and schedd:
        logger.info("-- Checking condor status --")

        # get DAG status
        jsonfp = outdir / "nagios-condor-{}.json".format(group)
        okstates = ['Running', 'Idle', 'Completed']
        try:
            # check manager status
            qstr = 'OmicronManager == "{}" && Owner == "{}"'.format(
                group,
                args.user,
            )
            try:
                jobs = schedd.query(qstr, ['JobStatus'])
            except IOError as e:
                warnings.warn("Caught IOError: %s [retrying...]" % str(e))
                sleep(2)
                jobs = schedd.query(qstr, ['JobStatus'])
            logger.debug(
                "Found {} jobs for query {!r}".format(len(jobs), qstr),
            )
            if len(jobs) > 1:
                raise RuntimeError("Multiple OmicronManager jobs found for %r"
                                   % group)
            elif len(jobs) == 0:
                raise RuntimeError(
                    "No OmicronManager job found for %r" % group,
                )
            status = condor.JOB_STATUS[jobs[0]['JobStatus']]
            if status not in okstates:
                raise RuntimeError("OmicronManager status for %r: %r"
                                   % (group, status))
            logger.debug("Manager status is %r" % status)
            # check node status
            jobs = schedd.query(
                'OmicronProcess == "{}" && Owner == "{}"'.format(
                    group,
                    args.user,
                ),
                ['JobStatus', 'ClusterId'],
            )
            logger.debug(
                "Found {} jobs for query {!r}".format(len(jobs), qstr),
            )
            for job in jobs:
                status = condor.JOB_STATUS[job['JobStatus']]
                if status not in okstates:
                    raise RuntimeError("Omicron node %s (%r) is %r"
                                       % (job['ClusterId'], group, status))
        except RuntimeError as e:
            print_nagios_json(2, str(e), jsonfp, tag='condor')
            logger.warning("Failed to determine condor status: %r" % str(e))
        except IOError as e:
            logger.warning("Caught %s: %s" % (type(e).__name__, e))
            logger.info("Failed to connect to HTCondor scheduler, cannot "
                        "determine condor status for %s" % group)
        else:
            print_nagios_json(
                0,
                "Condor processing for %r is OK" % group,
                jsonfp,
                tag='condor',
            )
            logger.info("Condor processing is OK")

    if not args.skip_job_duration:
        # get job duration history
        plot = Plot(figsize=[12, 3])
        plot.subplots_adjust(bottom=.22, top=.87)
        ax = plot.gca(xscale="auto-gps")
        times, jobdur = condor.get_job_duration_history_shell(
            'OmicronProcess', group, maxjobs=5000)
        logger.debug("Recovered duration history for %d omicron.exe jobs"
                     % len(times))
        line = ax.plot([0], [1], label='Omicron.exe')[0]
        ax.plot(times, jobdur, linestyle=' ', marker='.',
                color=line.get_color())
        times, jobdur = condor.get_job_duration_history_shell(
            'OmicronPostProcess', group, maxjobs=5000)
        logger.debug("Recovered duration history for %d post-processing jobs"
                     % len(times))
        line = ax.plot([0], [1], label='Post-processing')[0]
        ax.plot(times, jobdur, linestyle=' ', marker='.',
                color=line.get_color())
        ax.legend(loc='upper left', borderaxespad=0, bbox_to_anchor=(1.01, 1),
                  handlelength=1)
        ax.set_xlim(args.gps_start_time, args.gps_end_time)
        ax.set_epoch(ax.get_xlim()[1])
        ax.set_yscale('log')
        ax.set_title('Omicron job durations for %r' % group)
        ax.set_ylabel('Job duration [seconds]')
        ax.xaxis.labelpad = 5
        png = str(outdir / "nagios-condor-{}.png".format(group))
        plot.save(png)
        plot.close()
        logger.debug("Saved condor plot to %s" % png)

    if args.skip_file_checks:
        sys.exit(0)

    # -- get file latency and archive completeness ----------------------------

    logger.info("-- Checking file archive --")

    # get frame segments
    segs = segments.get_frame_segments(obs, frametype, start, end)

    # get state segments
    if stateflag is not None:
        segs &= segments.query_state_segments(
            stateflag,
            start,
            end,
            pad=statepad,
        )

    try:
        end = segs[-1][1]
    except IndexError:
        pass

    # apply inwards padding to generate resolvable segments
    for i in range(len(segs) - 1, -1, -1):
        # if segment is shorter than padding, ignore it completely
        if abs(segs[i]) <= padding * 2:
            del segs[i]
        # otherwise apply padding to generate trigger segment
        else:
            segs[i] = segs[i].contract(padding)
    logger.debug("Found %d seconds of analysable time" % abs(segs))

    # load archive latency
    latencyfile = outdir / "nagios-latency-{}.h5".format(tag)
    times = dict((c, dict((ft, None) for ft in filetypes)) for c in channels)
    ldata = dict((c, dict((ft, None) for ft in filetypes)) for c in channels)
    try:
        with h5py.File(latencyfile, 'r') as h5file:
            for c in channels:
                for ft in filetypes:
                    try:
                        times[c][ft] = h5file[c]['time'][ft][:]
                        ldata[c][ft] = h5file[c]['latency'][ft][:]
                    except KeyError:
                        times[c][ft] = numpy.ndarray((0,))
                        ldata[c][ft] = numpy.ndarray((0,))
    except OSError as exc:  # file not found, or is corrupt
        warnings.warn("failed to load latency data from {}: {}".format(
            latencyfile,
            str(exc),
        ))
        for c in channels:
            for ft in filetypes:
                if not times[c].get(ft):
                    times[c][ft] = numpy.ndarray((0,))
                    ldata[c][ft] = numpy.ndarray((0,))
    else:
        logger.debug("Parsed latency data from %s" % latencyfile)

    # load acknowledged gaps
    acksegfile = str(outdir / "acknowledged-gaps-{}.txt".format(tag))
    try:
        acknowledged = SegmentList.read(acksegfile, gpstype=float,
                                        format="segwizard")
    except IOError:  # no file
        acknowledged = SegmentList()
    else:
        logger.debug(
            "Read %d segments from %s" % (len(acknowledged), acksegfile),
        )
        acknowledged.coalesce()

    # build legend for segments
    leg = OrderedDict()
    leg['Analysable'] = SegmentRectangle(
        [0, 1], 0, facecolor='lightgray', edgecolor='gray',
    )
    leg['Available'] = SegmentRectangle(
        [0, 1], 0, facecolor='lightgreen', edgecolor='green',
    )
    leg['Missing'] = SegmentRectangle(
        [0, 1], 0, facecolor='red', edgecolor='darkred',
    )
    leg['Unresolvable'] = SegmentRectangle(
        [0, 1], 0, facecolor='magenta', edgecolor='purple',
    )
    leg['Overlapping'] = SegmentRectangle(
        [0, 1], 0, facecolor='yellow', edgecolor='orange',
    )
    leg['Pending'] = SegmentRectangle(
        [0, 1], 0, facecolor='lightskyblue', edgecolor='blue',
    )
    leg['Acknowledged'] = SegmentRectangle(
        [0, 1], 0, facecolor='sandybrown', edgecolor='brown',
    )

    logger.debug("Checking archive for each channel...")

    # find files
    latency = {}
    gaps = {}
    overlap = {}
    pending = {}
    plots = {}
    for c in channels:
        # create data storage
        latency[c] = {}
        gaps[c] = {}
        overlap[c] = {}
        pending[c] = {}

        # create figure
        plot = Plot(figsize=[12, 5])
        lax = plot.add_subplot(grid[0, 0], xscale="auto-gps")
        sax = plot.add_subplot(grid[1, 0], sharex=lax, projection='segments')
        colors = ['lightblue', 'dodgerblue', 'black']

        for y, ft in enumerate(filetypes):
            # find files
            cache = io.find_omicron_files(c, start, end, archive, ext=ft)
            cpend = sieve_cache(io.find_pending_files(c, proddir, ext=ft),
                                segment=Segment(start, end))
            # get available segments
            avail = segments.cache_segments(cache)
            found = avail & segs
            pending[c][ft] = segments.cache_segments(cpend) & segs
            # remove gaps at the end that represent latency
            try:
                latency[c][ft] = abs(segs & type(segs)([
                    type(segs[0])(found[-1][1], segs[-1][1])])) / 3600.
            except IndexError:
                latency[c][ft] = 0
                processed = segs
            else:
                processed = segs & type(segs)(
                    [type(segs[0])(start, found[-1][1])])
            gaps[c][ft] = type(found)()
            lost = type(found)()
            for s in processed - found:
                if abs(s) < mingap and s in list(segs):
                    lost.append(s)
                else:
                    gaps[c][ft].append(s)
            # remove acknowledged gaps
            ack = gaps[c][ft] & acknowledged
            gaps[c][ft] -= acknowledged
            # print warnings
            if abs(gaps[c][ft]):
                warnings.warn(
                    f"Gaps found in {c} files for {ft}:\n{gaps[c][ft]}")
            overlap[c][ft] = segments.cache_overlaps(cache)
            if abs(overlap[c][ft]):
                warnings.warn(
                    f"Overlap found in {c} files for {ft}:\n{overlap[c][ft]}")

            # append archive
            times[c][ft] = numpy.concatenate((times[c][ft][-99999:], [NOW]))
            ldata[c][ft] = numpy.concatenate((ldata[c][ft][-99999:],
                                              [latency[c][ft]]))

            # plot
            line = lax.plot(
                times[c][ft],
                ldata[c][ft],
                label=ft,
                color=colors[y],
            )[0]
            lax.plot(times[c][ft], ldata[c][ft], marker='.', linestyle=' ',
                     color=line.get_color())
            sax.plot_segmentlist(segs, y=y, label=ft, alpha=.5,
                                 facecolor=leg['Analysable'].get_facecolor(),
                                 edgecolor=leg['Analysable'].get_edgecolor())
            sax.plot_segmentlist(pending[c][ft], y=y,
                                 facecolor=leg['Pending'].get_facecolor(),
                                 edgecolor=leg['Pending'].get_edgecolor())
            sax.plot_segmentlist(avail, y=y, label=ft, alpha=.2, height=.1,
                                 facecolor=leg['Available'].get_facecolor(),
                                 edgecolor=leg['Available'].get_edgecolor())
            sax.plot_segmentlist(found, y=y, label=ft, alpha=.5,
                                 facecolor=leg['Available'].get_facecolor(),
                                 edgecolor=leg['Available'].get_edgecolor())
            sax.plot_segmentlist(lost, y=y,
                                 facecolor=leg['Unresolvable'].get_facecolor(),
                                 edgecolor=leg['Unresolvable'].get_edgecolor())
            sax.plot_segmentlist(gaps[c][ft], y=y,
                                 facecolor=leg['Missing'].get_facecolor(),
                                 edgecolor=leg['Missing'].get_edgecolor())
            sax.plot_segmentlist(overlap[c][ft], y=y,
                                 facecolor=leg['Overlapping'].get_facecolor(),
                                 edgecolor=leg['Overlapping'].get_edgecolor())
            sax.plot_segmentlist(ack, y=y,
                                 facecolor=leg['Acknowledged'].get_facecolor(),
                                 edgecolor=leg['Acknowledged'].get_edgecolor())

        # finalise plot
        lax.axhline(args.warning / 3600., color=(1.0, 0.7, 0.0),
                    linestyle='--', linewidth=2, label='Warning', zorder=-1)
        lax.axhline(args.error / 3600., color='red', linestyle='--',
                    linewidth=2, label='Critical', zorder=-1)
        lax.set_title('Omicron status: {}'.format(c))
        lax.set_ylim(0, args.error / 1800.)
        lax.set_ylabel('Latency [hours]')
        lax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), borderaxespad=0,
                   handlelength=2, fontsize=12.4)
        lax.set_xlabel(' ')
        for ax in plot.axes:
            ax.set_xlim(args.gps_start_time, args.gps_end_time)
            ax.set_epoch(ax.get_xlim()[1])
        sax.xaxis.labelpad = 5
        sax.set_ylim(-.5, len(filetypes) - .5)
        sax.legend(leg.values(), leg.keys(), handlelength=1, fontsize=12.4,
                   loc='lower left', bbox_to_anchor=(1.01, 0), borderaxespad=0)
        plots[c] = png = outdir / "nagios-latency-{}.png".format(
            c.replace(':', '-'),
        )
        plot.save(png)
        plot.close()
        logger.debug("    %s" % c)

    # update latency and write archive
    h5file = h5py.File(latencyfile, 'w')
    for c in channels:
        g = h5file.create_group(c)
        for name, d in zip(['time', 'latency'], [times[c], ldata[c]]):
            g2 = g.create_group(name)
            for ft in filetypes:
                g2.create_dataset(ft, data=d[ft], compression='gzip')
    h5file.close()
    logger.debug("Stored latency data as HDF in %s" % latencyfile)

    # write nagios output for files
    status = []
    for segset, tag in zip([gaps, overlap], ['gaps', 'overlap']):
        chans = [(c, segset[c]) for c in segset
                 if abs(reduce(operator.or_, segset[c].values()))]
        jsonfp = outdir / "nagios-{}-{}.json".format(tag, group)
        status.append((tag, jsonfp))
        if chans:
            # format the segments nicely for Icinga 2
            lines = []
            for chan, ftsegs in chans:
                lines.append(f"{chan}:")
                for ft, segs in ftsegs.items():
                    lines.extend((
                        f"  {ft}:",
                        indent(str(segs), "    "),
                    ))
            gapstr = linesep.join(lines)
            code = 1
            message = ("%s found in Omicron files for group %r\n%s"
                       % (tag.title(), group, gapstr))
        else:
            code = 0
            message = (
                "No %s found in Omicron files for group %r" % (tag, group)
            )
        print_nagios_json(code, message, jsonfp, tag=tag, **{tag: dict(chans)})

    # write group JSON
    jsonfp = outdir / "nagios-latency-{}.json".format(group)
    status.append(('latency', jsonfp))
    code = 0
    message = 'No channels have high latency for group %r' % group
    ldict = dict((c, max(latency[c].values())) for c in latency)
    for x, dt in zip([2, 1], [args.error, args.warning]):
        dh = dt / 3600.
        chans = [c for c in ldict if ldict[c] >= dh]
        if chans:
            code = x
            message = ("%d channels found with high latency (above %s seconds)"
                       % (len(chans), dt))
            break
    print_nagios_json(code, message, jsonfp, tag='latency', latency=ldict)

    # auto-detect 'standard' JSON files
    for tag, name in zip(
        ['condor', 'omicron-online'],
        ['condor', 'processing'],
    ):
        f = outdir / "nagios-{}-{}.json".format(tag, group)
        if f.is_file():
            status.insert(0, (name, f))

    # write HTML summary
    if args.html:
        page = markup.page()
        page.init(
            title="%s Omicron Online status" % group,
            css=[
                ('//maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/'
                 'bootstrap.min.css'),
                ('//cdnjs.cloudflare.com/ajax/libs/fancybox/2.1.5/'
                 'jquery.fancybox.min.css'),
            ],
            script=[
                '//code.jquery.com/jquery-1.11.2.min.js',
                ('//maxcdn.bootstrapcdn.com/bootstrap/3.3.4/js/'
                 'bootstrap.min.js'),
                ('//cdnjs.cloudflare.com/ajax/libs/fancybox/2.1.5/'
                 'jquery.fancybox.min.js'),
            ],
        )
        page.div(class_='container')
        # write header
        page.div(class_='page-header')
        page.h1('Omicron Online status: %s' % group)
        page.div.close()  # page-header
        # write summary
        page.div(id_='json')
        page.h2("Processing status")
        for tag, f in status:
            jf = f.name
            page.a("%s status" % tag.title(), href=jf, role='button',
                   target="_blank", id_="nagios-%s" % tag,
                   class_='btn btn-default json-status')
        page.p(style="padding-top: 5px;")
        page.small(
            "Hover over button for explanation, click to open JSON file",
        )
        page.p.close()
        page.div.close()  # id=json
        # show plots
        page.div(id_='plots')
        page.h2("Channel details")
        page.div(class_='row')
        for channel in sorted(channels):
            png = plots[channel].name
            page.div(class_="col-sm-6 col-md-4")
            page.div(class_="panel panel-default")
            page.div(class_='panel-heading')
            page.h3(channel, class_='panel-title', style="font-size: 14px;")
            page.div.close()  # panel-heading
            page.div(class_='panel-body')
            page.a(href=png, target="_blank", class_="fancybox",
                   rel="channel-status-img")
            page.img(src=png, class_='img-responsive')
            page.a.close()
            page.div.close()  # panel-body
            page.div.close()  # panel
            page.div.close()  # col
        page.div.close()  # row
        page.div.close()  # id=plots

        # dump parameters
        page.div(id_="parameters")
        page.h2("Parameters")
        for key, val in cp.items(group):
            page.p()
            page.strong("%s:" % key)
            page.add(val)
            page.p.close()
        page.div.close()  # id=parameters

        # finish and close
        page.div.close()  # container
        page.script("""
        function setStatus(data, id) {
            var txt = data.status_intervals[0].txt_status.split("\\n")[0];
            $("#"+id).attr("title", txt);
            var stat = data.status_intervals[0].num_status;
            if (stat == 0) {
                $("#"+id).addClass("btn-success"); }
            else if (stat == 1) {
                $("#"+id).addClass("btn-warning"); }
            else if (stat == 2){
                $("#"+id).addClass("btn-danger"); }
        }

        $(document).ready(function() {
            $(".json-status").each(function() {
                var jsonf = $(this).attr("href");
                var id = $(this).attr("id");
                $.getJSON(jsonf, function(data) { setStatus(data, id); });
            });

            $(".fancybox").fancybox({nextEffect: 'none', prevEffect: 'none'});
        });""", type="text/javascript")
        with (outdir / "index.html").open("w") as f:
            f.write(str(page))
        logger.debug("HTML summary written to %s" % f.name)


if __name__ == "__main__":
    main()
    if logger:
        logger.info(f'Run time: {(time.time() - prog_start):.1f} seconds')
