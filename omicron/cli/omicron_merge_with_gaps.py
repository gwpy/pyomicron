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
"""Handle merging different trigger file types detecting any gaps"""
import time
from logging.handlers import RotatingFileHandler

prog_start_time = time.time()
import argparse
import glob
import logging
from pathlib import Path
import re
import shutil
import subprocess
import sys

__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'
__version__ = '0.0.1'
__process_name__ = 'omicron_merge_with_gaps'

# global logger
logging.basicConfig()
logger = logging.getLogger(__process_name__)
logger.setLevel(logging.DEBUG)


def get_merge_cmd(ext):
    """
    Determine the command used to coalescew individual trigger files
    :param str ext:  file extension: xml, h5 or root
    """
    if ext == 'root':
        ret = 'omicron-root-merge'
    elif ext == 'h5':
        ret = 'omicron-hdf5-merge'
    elif 'xml' in ext:
        ret = 'ligolw_add'
    else:
        raise AttributeError(f'Unknown trigger file typr {ext}')
    ret_path = shutil.which(ret)
    if not ret_path:
        raise AttributeError(f'{ext} files require {ret} which is not in out path')
    return ret


def do_merge(opath, curfiles, chan, stime, etime, ext, skip_gzip, uint_bug):
    """
    Given the list of trigger files merge them all into a single file
    :param Path opath: output directory
    :param list curfiles: the pathes to files to merge
    :param str chan: channel name use in output filename
    :param int stime: Start GPS time for file list
    :param int etime: End GPS time
    :param str ext: trigger file extension, identifying file type
    :param boolean skip_gzip: if type is xml do not compress merged file
    :param boolean uint_bug: if type is xml fix an old Omicron bug
    """
    outfile_path = opath / f'{chan}-{stime}-{etime - stime}.{ext}'
    ret = None
    returncode = -1

    if curfiles:
        if len(curfiles) == 1:
            infile = curfiles[0]
            if infile != outfile_path:
                shutil.copy(infile, outfile_path)
                logger.info(f'Copied singleton trigger file to {outfile_path}')
                returncode = 0
        else:
            cmd = [get_merge_cmd(ext)]
            if ext == 'xml':
                cmd.append(f'--output={outfile_path}')
            cmd.extend(curfiles)
            if ext != 'xml':
                cmd.append(outfile_path)
            else:
                if uint_bug:
                    for f in curfiles:
                        if Path(f).exists():
                            sed_cmd = ['sed', '-ie', 's/uint_8s/int_8u/g', f]
                            subprocess.run(sed_cmd)
            logger.info(f'Merging {len(curfiles)} {ext} files into {outfile_path}')
            logger.debug('Merge command: {cmd}')
            result = subprocess.run(cmd, capture_output=True)
            returncode = result.returncode
            err_old_fmt = b"invalid type 'ilwd:char'"
            if returncode == 1 and ext == 'xml' and err_old_fmt in result.stderr:
                # old ligolw format seems to be the problem
                cmd = [get_merge_cmd(ext), '--ilwdchar-compat', f'--output={outfile_path}']
                cmd.extend(curfiles)
                logger.info(f'Retry merging {len(curfiles)} into {outfile_path} using old xml format')
                result = subprocess.run(cmd, capture_output=True)
                returncode = result.returncode

            if returncode == 0:
                logger.debug(f'Merge of {ext} files succeeded')
            else:
                logger.error(f'Return code:{returncode}, stderr:\n{str(result.stderr)}')

        if ext == 'xml' and returncode == 0 and not skip_gzip:
            logger.info(f'Compressing {outfile_path} with gzip')
            res2 = subprocess.run(['gzip', '-9',  '--force', outfile_path], capture_output=True)
            if res2.returncode == 0:
                ret = str(outfile_path.absolute()) + '.gz'
            else:
                logger.error(f'gzip error on {outfile_path}:\n {str(res2.stderr)}')
        else:
            ret = str(outfile_path.absolute())

    return ret


def main():
    global logger
    logging.basicConfig()
    logger = logging.getLogger(__process_name__)
    logger.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(description=__doc__,
                                     prog=__process_name__)
    parser.add_argument('-v', '--verbose', action='count', default=1,
                        help='increase verbose output')
    parser.add_argument('-V', '--version', action='version',
                        version=__version__)
    parser.add_argument('-q', '--quiet', default=False, action='store_true',
                        help='show only fatal errors')
    parser.add_argument('-l', '--log-file', help='Save log messages to this file')
    parser.add_argument('-o', '--out-dir', help='Path to output directory for merged diles')
    parser.add_argument('-n', '--no-merge', action='store_true', default=False,
                        help='Do not merge files, onpy copy to output dir')
    parser.add_argument('--no-gzip', action='store_true', default=False,
                        help='Do not compress the ligolw xml files')
    parser.add_argument('--uint-bug', default=False, action='store_true',
                        help='Deal with old version of Omicron that had a bug writing xml files')
    parser.add_argument('infiles', nargs='+', help='List of paths to files to merge or copy')

    args = parser.parse_args()

    verbosity = 0 if args.quiet else args.verbose

    if verbosity < 1:
        log_level = logging.CRITICAL
    elif verbosity < 2:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    log_file_format = "%(asctime)s - %(levelname)s: %(message)s"
    log_file_date_format = '%m-%d %H:%M:%S'
    logging.basicConfig(format=log_file_format, datefmt=log_file_date_format)
    logger = logging.getLogger(__process_name__)
    logger.setLevel(log_level)

    if args.log_file:
        log_formatter = logging.Formatter(fmt=log_file_format,
                                          datefmt=log_file_date_format)
        log_file_handler = RotatingFileHandler(args.log_file, maxBytes=10 ** 7,
                                               backupCount=5)
        log_file_handler.setFormatter(log_formatter)
        logger.addHandler(log_file_handler)

    fpat = '^(.+)-(\\d+)-(\\d+).(.+)$'
    fmatch = re.compile(fpat)

    infiles = list()
    for infile in args.infiles:
        files = glob.glob(infile)
        infiles.extend(files)
    infiles.sort()
    logger.info(f'{len(args.infiles)} requested {len(infiles)} were found.')
    curfiles = list()
    start_time = None
    end_time = None
    name = None
    ext = None
    error_cnt = 0
    out_dir = Path(args.out_dir)
    out_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    outfiles = list()

    for infile in infiles:
        inpath = Path(infile)
        if not inpath.exists():
            logger.error(f'input file {infile} does not exist')
            continue
        fnam = inpath.name
        m = fmatch.match(fnam)
        if m is None:
            logger.error(f'Skipping {inpath.absolute()} parse error')
            continue

        if args.no_merge:
            shutil.copy(infile, out_dir)
            continue

        cname = m.group(1)
        stime = int(m.group(2))
        cdur = int(m.group(3))
        cext = m.group(4)

        if name is None:
            name = cname
        elif name != cname:
            logger.error(f'Looks like multiple channels in file list[{name}] and [{cname}]')
            logger.error(f'Skipping {inpath.absolute()}')
            continue
        if ext is None:
            ext = cext
        elif ext != cext:
            logger.error(f'Looks like multiple file types in file list [{ext}] and [{cext}]')
            logger.error(f'Skipping {inpath.absolute()}')
            continue

        etime = stime + cdur
        if start_time is None:
            # first file in this time interval
            start_time = stime
            end_time = etime
            curfiles.append(inpath)
        elif stime == end_time:
            # this file is contiguous with previous, so it can be concatenated
            end_time = etime
            curfiles.append(inpath)
        else:
            # break in continuity
            outfile = do_merge(out_dir, curfiles, name, start_time, etime, ext, args.no_gzip, args.uint_bug)
            if outfile:
                outfiles.append(outfile)
            else:
                error_cnt += 1

            start_time = None
            end_time = None
            curfiles = [inpath]
    if curfiles:
        outfile = do_merge(out_dir, curfiles, name, start_time, end_time, ext, args.no_gzip, args.uint_bug)
        if outfile:
            outfiles.append(outfile)
        else:
            error_cnt += 1

    elap = time.time() - prog_start_time
    logger.info('run time {:.1f} s'.format(elap))

    if error_cnt > 0:
        logger.error(f'{error_cnt} errors detected.')
        sys.exit(1)
    else:
        # STDOUT should have only the list of output files
        print(' '.join(outfiles))
        sys.exit(0)


if __name__ == "__main__":
    main()
