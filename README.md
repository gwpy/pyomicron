Python utilities and extensions for the Omicron (C++) GW event trigger generator.

This package augments the core functionality of the Omicron ETG by providing utilities for building an HTCondor workflow (DAG) to parallelise processing, including segment-selection logic, frame-file discovery, and post-processing.

All credit for the actual Omicron algorithm goes to [Florent Robinet](//github.com/FlorentRobinet/), see [here](http://virgo.in2p3.fr/GWOLLUM/v2r2/index.html?Main) for more details.

## Installation

PyOmicron can be installed using `pip`:

```shell
python -m pip install pyomicron
```

or conda:

```shell
conda install -c conda-forge pyomicron
```

## Project status

[![PyPI](https://badge.fury.io/py/pyomicron.svg)](http://badge.fury.io/py/pyomicron)
[![DOI](https://zenodo.org/badge/53675102.svg)](https://zenodo.org/badge/latestdoi/53675102)
[![License](https://img.shields.io/pypi/l/pyomicron.svg)](https://choosealicense.com/licenses/gpl-3.0/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/pyomicron.svg)](https://pypi.org/project/pyomicron/)

## Development status

[![Build Status](https://travis-ci.org/gwpy/pyomicron.svg?branch=master)](https://travis-ci.org/gwpy/pyomicron)
[![codecov](https://codecov.io/gh/gwpy/pyomicron/branch/master/graph/badge.svg)](https://codecov.io/gh/gwpy/pyomicron)

## License

PyOmicron is released under the GNU General Public License v3.0, see [here](https://choosealicense.com/licenses/gpl-3.0/) for a description of this license, or see [COPYING](https://github.com/gwpy/pyomicron/blob/master/COPYING) for the full text.
