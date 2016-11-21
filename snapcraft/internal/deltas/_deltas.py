# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
import os
import subprocess


logger = logging.getLogger(__name__)


delta_formats_options = [
    'xdelta'
]


class DeltaGenerationFailed(Exception):
    """A Delta failed to generate."""


class DeltaFormatIsNoneError(Exception):
    """A delta format must be set."""


class DeltaToolPathIsNoneError(Exception):
    """A delta too path must be set."""


class DeltaFormatOptionError(Exception):
    """A delta format option is not in the define list."""


class BaseDeltasGenerator:
    """Class for delta generation

    This class is responsible for the snap delta file generation
    """

    delta_format = None
    delta_file_extname = 'delta'
    delta_tool_path = None

    def __init__(self, source_path, target_path):
        self.source_path = source_path
        self.target_path = target_path
        self.pre_check()

    def pre_check(self):
        self._check_properties()
        self._check_file_existence()
        self._check_delta_gen_tool()

    def _check_properties(self):
        if self.delta_format is None:
            raise DeltaFormatIsNoneError(
                'delta_format must be set in subclass')
        if self.delta_tool_path is None:
            raise DeltaToolPathIsNoneError(
                'delta_too_path must be set in subclass')
        if self.delta_format not in delta_formats_options:
            raise DeltaFormatOptionError(
                'delta_format must be option in {}'.format(
                    delta_formats_options))

    def _check_file_existence(self):
        if not os.path.exists(self.source_path):
            raise ValueError(
                'source file {} not exist'.format(self.source_path))

        if not os.path.exists(self.target_path):
            raise ValueError(
                'target file {} not exist'.format(self.target_path))

    def _check_delta_gen_tool(self):
        """check if the delta generation tool exists"""
        if not executable_exists(self.delta_tool_path):
            delta_path = which(self.delta_format)
            if not delta_path:
                raise DeltaGenerationFailed(
                    "Could not find {} executable.".format(
                        self.delta_format))
            else:
                self.delta_tool_path = delta_path

    def find_unique_file_name(self, path_hint):
        """Return a path on disk similar to 'path_hint' that does not exist.

        This function can be used to ensure that 'path_hint' points to a file
        on disk that does not exist. The returned filename may be a modified
        version of 'path_hint' if 'path_hint' already exists.

        """
        target = path_hint
        counter = 0
        while os.path.exists(target):
            target = "{}-{}".format(path_hint, counter)
            counter += 1
        return target

    def _setup_std_output(self, source_path):
        """helper to setup the stdout and stderr for subprocess"""
        workdir = os.path.dirname(source_path)

        stdout_path = self.find_unique_file_name(
            os.path.join(workdir, '{}-out'.format(self.delta_format)))
        stdout_file = open(stdout_path, 'wb')

        stderr_path = self.find_unique_file_name(
            os.path.join(workdir, '{}-err'.format(self.delta_format)))
        stderr_file = open(stderr_path, 'wb')

        return workdir, stdout_path, stdout_file, stderr_path, stderr_file

    def make_delta(self, output_dir=None):
        """call the delta generation tool to create the delta file.

        returns: generated delta file path
        """
        logger.info('Generating {} delta for {}->{}.'.format(
                self.delta_format, self.source_path, self.target_path))

        if output_dir is not None:
            # consider creating the delta file in the specified output_dir
            # with generated filename.
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            _, _file_name = os.path.split(self.target_path)
            delta_file = self.find_unique_file_name(
                '{}{}.{}'.format(
                    output_dir, _file_name, self.delta_file_extname))
        else:
            # create the delta file under the target_path with
            # the generated filename.
            delta_file = self.find_unique_file_name(
                '{}.{}'.format(self.target_path, self.delta_file_extname))

        delta_cmd = self.get_delta_cmd(self.source_path,
                                       self.target_path,
                                       delta_file)

        workdir, stdout_path, stdout_file, \
            stderr_path, stderr_file = self._setup_std_output(self.source_path)

        process = subprocess.Popen(
            delta_cmd,
            stdout=stdout_file,
            stderr=stderr_file,
            cwd=workdir
        )

        process.wait()

        stdout_file.close()
        stderr_file.close()

        # Success is exiting with 0 or 1. Yes, really. I know.
        # https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=212189
        if process.returncode not in (0, 1):
            _stdout = _stderr = ''
            with open(stdout_path) as f:
                _stdout = f.read()
            with open(stderr_path) as f:
                _stderr = f.read()
            raise DeltaGenerationFailed(
                "Could not generate %s delta.\n"
                "stdout: {{{\n%s}}}\n"
                "stderr: {{{\n%s}}}\n"
                "returncode: %d"
                % (
                    self.delta_format,
                    _stdout, _stderr,
                    process.returncode
                )
            )

        self.log_delta_file(delta_file)

        return delta_file

    # ------------------------------------------------------
    # the methods need to be implemented in subclass
    # ------------------------------------------------------
    def get_delta_cmd(self, source_path, target_path, delta_file):
        raise NotImplementedError

    def log_delta_file(self, delta_file):
        pass


def executable_exists(path):
    """Return True if 'path' exists and is readable and executable."""
    return os.path.exists(path) and os.access(path, os.R_OK | os.X_OK)


def which(name):
    """Call 'which <name>' and return the result.

    :returns: The path, as returned from which, as a string, or None if the
    executable could not be found.
    """
    try:
        return subprocess.check_output(['which', name]).decode().strip()
    except subprocess.CalledProcessError:
        return None
