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

"""Test utilies for Omicron
"""

import os
from unittest import mock

from .. import utils


def test_get_omicron_version():
    testv = 'v2r1'
    v = utils.get_omicron_version(
        "/home/detchar/opt/virgosoft/Omicron/%s/Linux-x86_64/omicron.exe"
        % testv
    )
    assert v == testv

    os.environ['OMICRON_VERSION'] = testv
    assert utils.get_omicron_version() == testv

    os.environ.pop('OMICRON_VERSION')
    os.environ['OMICRONROOT'] = (
        "/home/detchar/opt/virgosoft/Omicron/%s" % testv)
    assert utils.get_omicron_version() == testv
    assert utils.get_omicron_version() > 'v1r2'
    assert utils.get_omicron_version() < 'v2r2'


@mock.patch.dict(os.environ, clear=True)
def test_astropy_config_path(tmp_path):
    confpath = utils.astropy_config_path(tmp_path, update_environ=True)
    assert confpath == tmp_path / ".config"
    assert os.environ["XDG_CONFIG_HOME"] == str(confpath)
    assert (confpath / "astropy").is_dir()


@mock.patch.dict(os.environ, clear=True)
def test_astropy_config_path_no_environ(tmp_path):
    confpath = utils.astropy_config_path(tmp_path, update_environ=False)
    assert "XDG_CONFIG_HOME" not in os.environ
