#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: nu:ai:ts=4:sw=4

#
#  Copyright (C) 2022 Joseph Areeda <joseph.areeda@ligo.org>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Online Omicron produces a lot of files, this program goes through all channels for
a metric day: int(GPS/100000) to merge any contiguous files into a new indir"""

import shutil
import sys
import time
import socket
from pathlib import Path

from gwpy.time import to_gps

start_time = time.time()
import argparse
import glob
import logging
import os
import htcondor  # for submitting jobs, querying HTCondor daemons, etc.


__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'
__version__ = '0.0.1'
__process_name__ = 'metric_day_merge'

exts = ['h5', 'root', 'xml.gz']
omicron_merge_with_gaps = shutil.which('omicron-merge-with-gaps')


def process_dir(indir, outdir, logger):
    """

    @param Path indir: directory to scan: <base>/<chan>/<day>
    @param Path outdir: new basdir for merged files
    @return:
    """
    thedir = Path(indir)
    chan_tag = thedir.parent.name
    day = thedir.name
    outpath = outdir / chan_tag / day
    layers = list()
    for ext in exts:
        trg_files = glob.glob(f'{str(thedir)}/*.{ext}')
        logger.info(f'{len(trg_files)} for merge in {chan_tag}')
        if len(trg_files) > 0:
            layer = {'cmd': 'omicron-merge-with-gaps',
                     'outdir': outpath,
                     'trg_files': trg_files}
            layers.append(layer)
    return layers


def main():
    logging.basicConfig()
    logger = logging.getLogger(__process_name__)
    logger.setLevel(logging.DEBUG)

    host = socket.gethostname()
    if 'ligo-la' in host:
        ifo = 'L1'
    elif 'ligo-wa' in host:
        ifo = 'H1'
    else:
        ifo = None

    def_dir = f'/home/detchar/triggers/{ifo}' if ifo else None

    parser = argparse.ArgumentParser(description=__doc__,
                                     prog=__process_name__)
    parser.add_argument('-v', '--verbose', action='count', default=1,
                        help='increase verbose output')
    parser.add_argument('-V', '--version', action='version',
                        version=__version__)
    parser.add_argument('-q', '--quiet', default=False, action='store_true',
                        help='show only fatal errors')
    parser.add_argument('-i', '--ifo', default=ifo, )
    parser.add_argument('-t', '--trig-dir', default=def_dir,
                        help='Base directory for search (default: %(default)s)')
    parser.add_argument('-o', '--outdir', help='path for output files and directories')
    parser.add_argument('-d', '--day', type=to_gps, help='metric day, gps, or date')
    parser.add_argument('--njobs', type=int, default=8, help='Number of parallel condor jobs. Default: %(default)s')
    parser.add_argument('--submit', action='store_true', help='Submit the condor job')

    args = parser.parse_args()

    verbosity = 0 if args.quiet else args.verbose

    if verbosity < 1:
        logger.setLevel(logging.CRITICAL)
    elif verbosity < 2:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    trig_dir = None
    err = list()
    if args.trig_dir:
        trig_dir = args.trig_dir
    elif args.ifo:
        trig_dir = f'/home/detchar/triggers/{args.ifo}'
    if trig_dir:
        trig_dir = Path(trig_dir)
        if not trig_dir.is_dir():
            err.append(f'Trigger directory ({trig_dir.absolute()} does not exist or is not a directory')
    else:
        err.append('trigger directory (--trig-indir) or IFO (--ifo) must be '
                   'specified if not running in an IFO cluster')

    if args.day:
        day = args.day if args.day < 1e6 else int(args.day / 1e5)
    else:
        err.append('Metric day to scan must be specified')

    if not args.outdir:
        err.append('Output directory must be specified')
    outdir = Path(args.outdir)
    condor_dir = outdir / 'condor'
    condor_dir.mkdir(mode=0o755, parents=True, exist_ok=True)

    if err:
        print('\n'.join(err), file=sys.stderr)
        parser.print_help(file=sys.stderr)
        sys.exit(2)

    dir_cmds = list()
    dir_pat = f'{str(trig_dir.absolute())}/*/{day}'
    dirs = glob.glob(dir_pat)
    logger.info(f'{len(dirs)} channels found.')
    for idir in dirs:
        cmds = process_dir(idir, outdir, logger)
        dir_cmds.extend(cmds)

    scripts = list()
    script_paths = list()
    njobs = args.njobs
    for n in range(0, njobs):
        scripts.append(list())
        script_path = condor_dir / f'merge_{n+1:02d}.sh'
        script_paths.append(script_path)
    n = 0
    # distribute commands into the multiple scripts
    for cmd in dir_cmds:
        c = f'{cmd["cmd"]} -vvv --out-dir {cmd["outdir"]} {" ".join(cmd["trg_files"])}'
        scripts[n].append(c)
        n = n + 1 if n < njobs - 1 else 0

    # Write the script files
    for n in range(0, njobs):
        with script_paths[n].open(mode='w') as out:
            for c in scripts[n]:
                print(f'{c}\n', file=out)

    # Write condor submit file
    user = os.getlogin()
    submit = {'executable': shutil.which('bash'),
              'arguments': '$(script)',
              'accounting_group': 'ligo.prod.o3.detchar.transient.omicron',
              'accounting_group_user': 'joseph.areeda' if user == 'detchar' or user == 'root' else user,
              'request_disk': '1G',
              'request_memory': '1G',
              'getenv': 'True',
              'environment': '"HDF5_USE_FILE_LOCKING=FALSE"',
              'log': f'{str(condor_dir.absolute())}/merge.log',
              'error': '$(script).err',
              'output': '$(script).out',
              'notification': 'never',
              }

    with (condor_dir / 'merge.sub').open(mode='w') as subfile:
        for k, v in submit.items():
            print(f'{k} = {v}', file=subfile)
        print(f'queue script matching files {str((condor_dir / "merge_*.sh").absolute())}', file=subfile)

    if args.submit:
        sub_obj = htcondor.Submit(submit)
        item_data = [{'script': str(path.absolute())} for path in script_paths]
        schedd = htcondor.Schedd()
        submit_result = schedd.submit(sub_obj, itemdata=iter(item_data))
        logger.info(str(submit_result))

    elap = time.time() - start_time
    logger.info('run time {:.1f} s'.format(elap))


if __name__ == "__main__":
    main()
