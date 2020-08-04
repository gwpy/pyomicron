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
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from .. import utils


@mock.patch("os.path.isfile", side_effect=(False, True))
@mock.patch("os.access", return_value=True)
@mock.patch.dict("os.environ")
def test_find_omicron_path(*mocks):
    os.environ["PATH"] = "/test/path"
    assert str(utils.find_omicron()) == "/test/path/omicron"


@mock.patch("os.access", return_value=True)
@mock.patch.dict("os.environ")
def test_find_omicron_relative(_):
    os.environ.pop('PATH')
    assert utils.find_omicron() == Path(sys.executable).parent / "omicron"


@mock.patch("os.access", return_value=False)
def test_find_omicron_error(_):
    with pytest.raises(RuntimeError):
        utils.find_omicron()


@mock.patch("subprocess.check_output", return_value=b"Omicron 1.2.3")
def test_get_omicron_version(mocker):
    v = utils.get_omicron_version("omicron")
    assert v == "1.2.3"


@mock.patch(
    "subprocess.check_output",
    side_effect=subprocess.CalledProcessError(1, "test"),
)
def test_get_omicron_version_subprocess_error(mocker):
    with pytest.raises(RuntimeError):
        utils.get_omicron_version("omicron")


@mock.patch.dict(os.environ, clear=True)
def test_astropy_config_path(tmp_path):
    confpath = utils.astropy_config_path(tmp_path, update_environ=True)
    assert confpath == tmp_path / ".config"
    assert os.environ["XDG_CONFIG_HOME"] == str(confpath)
    assert (confpath / "astropy").is_dir()


@mock.patch.dict(os.environ, clear=True)
def test_astropy_config_path_no_environ(tmp_path):
    utils.astropy_config_path(tmp_path, update_environ=False)
    assert "XDG_CONFIG_HOME" not in os.environ
