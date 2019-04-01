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

"""Utilities for logging output from Omicron in python
"""

import logging
import sys

from gwpy.time import tconvert as gps_time_now

COLORS = dict((c, 30 + i) for i, c in enumerate(
    ['black', 'red', 'green', 'yellow',
     'blue', 'magenta', 'cyan', 'white']))
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"
LEVEL_COLORS = {
    'WARNING': COLORS['yellow'],
    'INFO': COLORS['white'],
    'DEBUG': COLORS['blue'],
    'CRITICAL': COLORS['red'],
    'ERROR': COLORS['red'],
}


def bold(text):
    """Format a string of text as bold for the shell

    Simply returns "\033[1m{text}\033[0m"
    """
    return ''.join([BOLD_SEQ, text, RESET_SEQ])


class ColoredFormatter(logging.Formatter):
    """A `~logging.Formatter` that supports coloured output
    """
    def __init__(self, msg, use_color=True, **kwargs):
        logging.Formatter.__init__(self, msg, **kwargs)
        self.use_color = use_color

    def format(self, record):
        record.gpstime = gps_time_now()
        levelname = record.levelname
        if self.use_color and levelname in LEVEL_COLORS:
            record.levelname = color_text(levelname, LEVEL_COLORS[levelname])
        return logging.Formatter.format(self, record)


class MaxLevelFilter(logging.Filter):
    '''Filters (lets through) all messages with level < LEVEL'''
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno < self.level


class Logger(logging.Logger):
    """`~logging.Logger` with a nice format
    """
    FORMAT = ('[{bold}%(name)s{reset} %(gpstime)d] %(levelname)+19s: '
              '%(message)s'.format(bold=BOLD_SEQ, reset=RESET_SEQ))

    def __init__(self, name, level=logging.DEBUG):
        try:
            super(Logger, self).__init__(name, level=level)
        except TypeError:
            logging.Logger.__init__(self, name, level=level)

        # set up handlers for WARNING and above to go to stderr
        colorformatter = ColoredFormatter(self.FORMAT)
        stdouthandler = logging.StreamHandler(sys.stdout)
        stdouthandler.setFormatter(colorformatter)
        stderrhandler = logging.StreamHandler(sys.stderr)
        stderrhandler.setFormatter(colorformatter)
        errfilter = MaxLevelFilter(logging.WARNING)
        stdouthandler.addFilter(errfilter)
        stdouthandler.setLevel(logging.DEBUG)
        stderrhandler.setLevel(logging.WARNING)
        self.addHandler(stdouthandler)
        self.addHandler(stderrhandler)


def color_text(text, color):
    if not isinstance(color, int):
        color = COLORS[color]
    return COLOR_SEQ % color + str(text) + RESET_SEQ
