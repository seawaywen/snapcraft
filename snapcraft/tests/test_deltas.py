# -*- mode:python; indent-tabs-mode:nil; tab-width:4 -*-
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

import os
import fixtures

from testtools import TestCase
from testtools import matchers as m

from snapcraft.internal.deltas._deltas import (
    BaseDeltasGenerator,
    executable_exists,
    DeltaFormatIsNoneError,
    DeltaToolPathIsNoneError,
    DeltaFormatOptionError
)


class ExecutableExistsTestCase(TestCase):

    def test_file_does_not_exist(self):
        workdir = self.useFixture(fixtures.TempDir()).path
        self.assertFalse(
            executable_exists(os.path.join(workdir, "doesnotexist"))
        )

    def test_file_exists_but_not_readable(self):
        workdir = self.useFixture(fixtures.TempDir()).path
        path = os.path.join(workdir, "notreadable")
        with open(path, 'wb'):
            pass
        os.chmod(path, 0)

        self.assertFalse(
            executable_exists(path)
        )

    def test_file_exists_but_not_executable(self):
        workdir = self.useFixture(fixtures.TempDir()).path
        path = os.path.join(workdir, "notexecutable")
        with open(path, 'wb'):
            pass
        os.chmod(path, 0o444)

        self.assertFalse(
            executable_exists(path)
        )

    def test_executable_exists_and_executable(self):
        workdir = self.useFixture(fixtures.TempDir()).path
        path = os.path.join(workdir, "notexecutable")
        with open(path, 'wb'):
            pass
        os.chmod(path, 0o555)

        self.assertTrue(
            executable_exists(path)
        )


class BaseDeltaGenerationTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.workdir = self.useFixture(fixtures.TempDir()).path
        self.source_file = os.path.join(self.workdir, 'source.snap')
        self.target_file = os.path.join(self.workdir, 'target.snap')

        with open(self.source_file, 'wb') as f:
            f.write(b'This is the source file.')
        with open(self.target_file, 'wb') as f:
            f.write(b'This is the target file.')

    def test_find_unique_file_name(self):
        class Tmpdelta(BaseDeltasGenerator):
            delta_format = 'xdelta'
            delta_tool_path = 'delta-gen-tool-path'
        tmp_delta = Tmpdelta(self.source_file, self.target_file)

        unique_file_name = tmp_delta.find_unique_file_name(
            tmp_delta.source_path)
        self.assertEqual(
            unique_file_name, tmp_delta.source_path + '-0'
        )
        with open(unique_file_name, 'wb') as f:
            f.write(b'tmp file.')

        self.assertEqual(
            tmp_delta.find_unique_file_name(tmp_delta.source_path),
            tmp_delta.source_path + '-1'
        )

    def test_not_set_delta_property_correctly(self):
        class Xdelta(BaseDeltasGenerator):
            delta_tool_path = 'delta-gen-tool-path'

        self.assertThat(
            lambda: Xdelta(self.source_file, self.target_file),
            m.raises(DeltaFormatIsNoneError)
        )

        class Ydelta(BaseDeltasGenerator):
            delta_format = 'xdelta'

        self.assertThat(
            lambda: Ydelta(self.source_file, self.target_file),
            m.raises(DeltaToolPathIsNoneError)
        )

        class Zdelta(BaseDeltasGenerator):
            delta_format = 'invalid-delta-format'
            delta_tool_path = 'delta-gen-tool-path'

        self.assertThat(
            lambda: Zdelta(self.source_file, self.target_file),
            m.raises(DeltaFormatOptionError)
        )

    def test_file_existence_failed(self):
        class Tmpdelta(BaseDeltasGenerator):
            delta_format = 'xdelta'
            delta_tool_path = 'delta-gen-tool-path'

        self.assertThat(
            lambda: Tmpdelta('invalid-source-file', self.target_file),
            m.raises(ValueError)
        )
        self.assertThat(
            lambda: Tmpdelta(self.source_file, 'invalid-target-file'),
            m.raises(ValueError)
        )

    def test_subclass_not_implement_get_delta_cmd(self):
        class Tmpdelta(BaseDeltasGenerator):
            delta_format = 'xdelta'
            delta_tool_path = 'delta-gen-tool-path'

        tmp_delta = Tmpdelta(self.source_file, self.target_file)
        self.assertThat(
            lambda: tmp_delta.make_delta(),
            m.raises(NotImplementedError)
        )
