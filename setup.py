#!/usr/bin/env python
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
# Copyright (C) Gabriele Vajente (2016)

"""Setup the PyOmicron package
"""

import glob
import os.path

from setuptools import (setup, find_packages)

import versioneer
__version__ = versioneer.get_version()
cmdclass = versioneer.get_cmdclass()

# set basic metadata
PACKAGENAME = 'omicron'
DISTNAME = 'omicron'
AUTHOR = 'Duncan Macleod'
AUTHOR_EMAIL = 'duncan.macleod@ligo.org'
LICENSE = 'GPLv3'

# Use the find_packages tool to locate all packages and modules
packagenames = find_packages()

# glob for all scripts
scripts = glob.glob(os.path.join('bin', '*'))

# -- run setup ----------------------------------------------------------------

setup(name=DISTNAME,
      provides=[PACKAGENAME],
      version=__version__,
      description=None,
      long_description=None,
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      license=LICENSE,
      packages=packagenames,
      cmdclass=cmdclass,
      include_package_data=True,
      scripts=scripts,
      setup_requires=[
          'pytest-runner',
          'setuptools',
      ],
      requires=[
          'numpy',
          'glue',
          'htcondor',
          'lal',
          'gwpy',
          'ROOT',
      ],
      install_requires=[
      ],
      tests_require=['pytest'],
      extras_require={
          'doc': ['sphinx', 'numpydoc', 'sphinxcontrib-programoutput',
                  'sphinxcontrib-epydoc'],
      },
      dependency_links=[
          'http://software.ligo.org/lscsoft/source/glue-1.49.1.tar.gz',
      ],
      use_2to3=True,
      classifiers=[
          'Programming Language :: Python',
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Science/Research',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: Developers',
          'Natural Language :: English',
          'Topic :: Scientific/Engineering',
          'Topic :: Scientific/Engineering :: Astronomy',
          'Topic :: Scientific/Engineering :: Physics',
          'Operating System :: POSIX',
          'Operating System :: Unix',
          'Operating System :: MacOS',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
      ],
)
