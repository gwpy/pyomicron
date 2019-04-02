# -*- coding: utf-8 -*-
# Copyright (C) Duncan Macleod (2019)
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

"""Tests for omicron.const
"""

import os
from importlib import reload
from unittest import mock

import pytest

from .. import const


@pytest.mark.parametrize("fqdn, ifo", [
    ("ldas-grid.ligo-wa.caltech.edu", "H1"),
    ("k1sum0.kagra", "K1"),
    ("test.localhost", None)
])
@mock.patch("socket.getfqdn")
def test_ifo(getfqdn, fqdn, ifo):
    getfqdn.return_value = fqdn
    reload(const)
    assert const.IFO == ifo
    assert const.ifo == (ifo.lower() if ifo else None)


def test_omicron_vars():
    assert str(const.OMICRON_BASE) == os.path.join(
        os.environ["HOME"],
        "omicron",
    )
