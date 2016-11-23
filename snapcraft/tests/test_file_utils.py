# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015, 2016 Canonical Ltd
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
import re

import fixtures

from snapcraft import file_utils
from snapcraft import tests


class ReplaceInFileTestCase(tests.TestCase):

    def test_replace_in_file(self):
        os.makedirs('bin')

        # Place a few files with bad shebangs, and some files that shouldn't be
        # changed.
        files = [
            {
                'path': os.path.join('bin', '2to3'),
                'contents': '#!/foo/bar/baz/python',
                'expected': '#!/usr/bin/env python',
            },
            {
                'path': os.path.join('bin', 'snapcraft'),
                'contents': '#!/foo/baz/python',
                'expected': '#!/usr/bin/env python',
            },
            {
                'path': os.path.join('bin', 'foo'),
                'contents': 'foo',
                'expected': 'foo',
            }
        ]

        for file_info in files:
            with self.subTest(key=file_info['path']):
                with open(file_info['path'], 'w') as f:
                    f.write(file_info['contents'])

                file_utils.replace_in_file('bin', re.compile(r''),
                                           re.compile(r'#!.*python'),
                                           r'#!/usr/bin/env python')

                with open(file_info['path'], 'r') as f:
                    self.assertEqual(f.read(), file_info['expected'])


class TestLinkOrCopyTree(tests.TestCase):

    def setUp(self):
        super().setUp()

        os.makedirs('foo/bar/baz')
        open('1', 'w').close()
        open(os.path.join('foo', '2'), 'w').close()
        open(os.path.join('foo', 'bar', '3'), 'w').close()
        open(os.path.join('foo', 'bar', 'baz', '4'), 'w').close()

    def test_link_file_to_file_raises(self):
        with self.assertRaises(NotADirectoryError) as raised:
            file_utils.link_or_copy_tree('1', 'qux')

        self.assertEqual(str(raised.exception), "'1' is not a directory")

    def test_link_file_into_directory(self):
        os.mkdir('qux')
        with self.assertRaises(NotADirectoryError) as raised:
            file_utils.link_or_copy_tree('1', 'qux')

        self.assertEqual(str(raised.exception), "'1' is not a directory")

    def test_link_directory_to_directory(self):
        file_utils.link_or_copy_tree('foo', 'qux')
        self.assertTrue(os.path.isfile(os.path.join('qux', '2')))
        self.assertTrue(os.path.isfile(os.path.join('qux', 'bar', '3')))
        self.assertTrue(os.path.isfile(os.path.join('qux', 'bar', 'baz', '4')))

    def test_link_directory_overwrite_file_raises(self):
        open('qux', 'w').close()
        with self.assertRaises(NotADirectoryError) as raised:
            file_utils.link_or_copy_tree('foo', 'qux')

        self.assertEqual(
            str(raised.exception),
            "Cannot overwrite non-directory 'qux' with directory 'foo'")

    def test_link_subtree(self):
        file_utils.link_or_copy_tree('foo/bar', 'qux')
        self.assertTrue(os.path.isfile(os.path.join('qux', '3')))
        self.assertTrue(os.path.isfile(os.path.join('qux', 'baz', '4')))


class TestLinkOrCopy(tests.TestCase):

    def setUp(self):
        super().setUp()

        os.makedirs('foo/bar/baz')
        open('1', 'w').close()
        open(os.path.join('foo', '2'), 'w').close()
        open(os.path.join('foo', 'bar', '3'), 'w').close()
        open(os.path.join('foo', 'bar', 'baz', '4'), 'w').close()

    def test_copy_nested_file(self):
        file_utils.link_or_copy('foo/bar/baz/4', 'foo2/bar/baz/4')
        self.assertTrue(os.path.isfile('foo2/bar/baz/4'))


class ExecutableExistsTestCase(tests.TestCase):

    def test_file_does_not_exist(self):
        workdir = self.useFixture(fixtures.TempDir()).path
        self.assertFalse(
            file_utils.executable_exists(
                os.path.join(workdir, 'doesnotexist'))
        )

    def test_file_exists_but_not_readable(self):
        workdir = self.useFixture(fixtures.TempDir()).path
        path = os.path.join(workdir, 'notreadable')
        with open(path, 'wb'):
            pass
        os.chmod(path, 0)

        self.assertFalse(file_utils.executable_exists(path))

    def test_file_exists_but_not_executable(self):
        workdir = self.useFixture(fixtures.TempDir()).path
        path = os.path.join(workdir, 'notexecutable')
        with open(path, 'wb'):
            pass
        os.chmod(path, 0o444)

        self.assertFalse(file_utils.executable_exists(path))

    def test_executable_exists_and_executable(self):
        workdir = self.useFixture(fixtures.TempDir()).path
        path = os.path.join(workdir, 'notexecutable')
        with open(path, 'wb'):
            pass
        os.chmod(path, 0o555)

        self.assertTrue(file_utils.executable_exists(path))
