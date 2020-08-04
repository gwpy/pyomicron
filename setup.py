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

"""Setup the PyOmicron package
"""

import glob
import os.path
import sys

from setuptools import (setup, find_packages)

import versioneer
__version__ = versioneer.get_version()
cmdclass = versioneer.get_cmdclass()

# -- metadata ---------------

# set basic metadata
PACKAGENAME = 'pyomicron'
DISTNAME = 'pyomicron'
AUTHOR = 'Alex Urban, Duncan Macleod'
AUTHOR_EMAIL = 'alexander.urban@ligo.org'
LICENSE = 'GPL-3.0-or-later'

# read description
with open('README.md', 'rb') as f:
    longdesc = f.read().decode().strip()

# -- dependencies -----------

setup_requires = [
    'setuptools',
]
install_requires = [
    'dqsegdb2',
    'gwdatafind',
    'gwpy >= 1.0.0',
    'h5py',
    'htcondor',
    'ligo-segments',
    'lscsoft-glue >= 1.60.0',
    'MarkupPy',
    'numpy',
    'pycondor',
    'python-ligo-lw >= 1.4.0',
]
tests_require = [
    'pytest >= 3.9',
]
if {'test'}.intersection(sys.argv):
    setup_requires.extend([
        'pytest_runner',
    ])

# -- content ----------------

# Use the find_packages tool to locate all packages and modules
packagenames = find_packages()

# glob for all scripts
scripts = glob.glob(os.path.join('bin', '*'))

# -- run setup --------------

setup(
    # metadata
    name=DISTNAME,
    provides=[PACKAGENAME],
    version=__version__,
    description="Python utilities and wrappers for GW Omicron",
    long_description=longdesc,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license=LICENSE,
    cmdclass=cmdclass,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        ('License :: OSI Approved :: GNU General Public '
         'License v3 or later (GPLv3+)'),
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Operating System :: MacOS',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Astronomy',
        'Topic :: Scientific/Engineering :: Physics',
    ],
    # dependencies
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=tests_require,
    # content
    packages=packagenames,
    scripts=scripts,
    include_package_data=True,
)
