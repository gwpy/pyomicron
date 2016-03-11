# PyOmicron
Python utilities and extensions for the Omicron (C++) GW event trigger generator.

This package augments the core functionality of the Omicron ETG by providing utilities for building an HTCondor workflow (DAG) to parallelise processing.

All credit the actual Omicron code goes to Florent Robinet, see [here](http://virgo.in2p3.fr/GWOLLUM/v2r2/index.html?Main) for more details.

## Requirements
This package is dependent upon the following packages

- [`numpy`](//numpy.org)
- [`gwpy`](//gwpy.github.io)
- [`glue`](//www.lsc-group.phys.uwm.edu/daswg/projects/glue.html)
- [`htcondor`](//research.cs.wisc.edu/htcondor/manual/v8.1/6_7Python_Bindings.html)
- [`PyROOT`](//root.cern.ch/pyroot)
