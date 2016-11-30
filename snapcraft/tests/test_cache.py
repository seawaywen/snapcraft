# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015 Canonical Ltd
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

import fixtures

from snapcraft import tests
from snapcraft.internal import cache
from snapcraft.internal.cache._snap import (
    _rewrite_snap_filename_with_revision,
    _rewrite_snap_filename_with_hash,
    _get_revision_from_snap_filename,
    _get_hash_from_snap_filename
)
from snapcraft.tests import fixture_setup


yaml_content = """name: cache-test
version: 0.1
summary: test cached snap
description: test cached snap
grade: devel

parts:
  my-part:
    plugin: nil
"""


class SnapCacheTestCase(tests.TestCase):

    def setUp(self):
        super().setUp()
        super().make_snapcraft_yaml(yaml_content)
        self.fake_logger = fixtures.FakeLogger(level=logging.INFO)
        self.useFixture(self.fake_logger)

    def test_rewrite_snap_filename(self):
        revision = 10
        snap_file = 'my-snap-name_0.1_amd64.snap'

        self.assertEqual(
            'my-snap-name_0.1_amd64_10.snap',
            _rewrite_snap_filename_with_revision(snap_file, revision))

    def test_rewrite_snap_filename_with_hash(self):
        file_hash = 'sdfjlajl34'
        snap_file = 'my-snap-name_0.1_amd64.snap'

        self.assertEqual(
            'my-snap-name_0.1_amd64_{}.snap'.format(file_hash),
            _rewrite_snap_filename_with_hash(snap_file, file_hash))

    def test_snap_cache(self):
        self.useFixture(fixture_setup.FakeTerminal())
        snap_cache = cache.SnapCache(project_name='my-snap-name')
        snap_file = 'my-snap-name_0.1_amd64.snap'

        # create dummy snap
        open(os.path.join(self.path, snap_file), 'a').close()
        snap_cache_hash = '0c63a75b845e4f7d01107d852e4c2485c51a50aaaa94fc61995e71bbee983a2ac3713831264adb47fb6bd1e058d5f004'

        # cache snap
        cached_snap_path = snap_cache.cache(snap_file)

        _, expected_snap = os.path.split(cached_snap_path)

        self.assertEqual('my-snap-name_0.1_amd64_{}.snap'.format(snap_cache_hash), expected_snap)
        self.assertTrue(os.path.isfile(cached_snap_path))

    def test_get_revision_from_snap_filename(self):
        revision = 10
        valid_snap_file = 'my-snap_0.1_amd64_{}.snap'.format(revision)

        self.assertEqual(
            revision,
            _get_revision_from_snap_filename(valid_snap_file))

        invalid_snap_list = [
            'cached-snap-without-revision_1.0_arm64.snap',
            'another-cached-snap-without-version_arm64.snap',
            'a-snap-with-no-number-revision_1.0_arm64_xx.snap'
        ]
        for invalid_snap_file in invalid_snap_list:
            self.assertEqual(
                None,
                _get_revision_from_snap_filename(invalid_snap_file))

    def test_get_hash_from_snap_filename(self):
        revision = '0c63a75b845e4f7d01107d852e4c2485c51a50aaaa94fc61995e71bbee98'\
                    '3a2ac3713831264adb47fb6bd1e058d5f004'
        valid_snap_file = 'my-snap_0.1_amd64_{}.snap'.format(revision)

        self.assertEqual(
            revision,
            _get_hash_from_snap_filename(valid_snap_file))

        invalid_snap_list = [
            'cached-snap-without-revision_1.0_arm64.snap',
            'another-cached-snap-without-version_arm64.snap',
            'a-snap-with-no-number-revision_1.0_arm64_xx.snap'
        ]
        for invalid_snap_file in invalid_snap_list:
            self.assertEqual(
                None,
                _get_revision_from_snap_filename(invalid_snap_file))

    def test_snap_cache_revision_once(self):
        self.useFixture(fixture_setup.FakeTerminal())

        self.assertEqual('bears', 'doorstops')


    def test_snap_cache_get_latest(self):
        self.useFixture(fixture_setup.FakeTerminal())

        snap_name = 'my-snap-name'
        snap_file = 'my-snap-name_0.1_amd64.snap'
        snap_cache = cache.SnapCache(project_name='my-snap-name')

        # create dummy cached snaps

        open(os.path.join(self.path, snap_file), 'a').close()
        #for rev in revisions:
        snap_cache.cache(snap_file)
        latest_snap = snap_cache.get_latest(snap_name)
        snap_cache_hash = '0c63a75b845e4f7d01107d852e4c2485c51a50aaaa94fc61995e71bbee983a2ac3713831264adb47fb6bd1e058d5f004'
        expected_snap = os.path.join(
            snap_cache.snap_cache_dir, 'my-snap-name_0.1_amd64_{}.snap'.format(snap_cache_hash))

        self.assertEqual(expected_snap, latest_snap)


class SnapCachedFilePruneTestCase(tests.TestCase):

    def setUp(self):
        super().setUp()
        super().make_snapcraft_yaml(yaml_content)
        self.fake_logger = fixtures.FakeLogger(level=logging.INFO)
        self.useFixture(self.fake_logger)

    def test_prune_snap_cache(self):
        self.useFixture(fixture_setup.FakeTerminal())
        snap_cache = cache.SnapCache(project_name='my-snap-name')

        snap_file = 'my-snap-name_0.1_amd64.snap'

        # create dummy snap
        open(os.path.join(self.path, snap_file), 'a').close()
        snap_cache_hash = '0c63a75b845e4f7d01107d852e4c2485c51a50aaaa94fc61995e71bbee983a2ac3713831264adb47fb6bd1e058d5f004'

        # cache snap
        snap_cache.cache(snap_file)

        # create other cached snap revisions
        to_be_deleted_files = []
        cached_snaps = ['a-cached-snap_0.3_amd64_8.snap',
                        'another-cached-snap_1.0_arm64_6.snap']

        for cached_snap in cached_snaps:
            cached_snap_path = os.path.join(snap_cache.snap_cache_dir,
                                            cached_snap)
            to_be_deleted_files.append(cached_snap_path)
            open(cached_snap_path, 'a').close()

        real_cached_snap = _rewrite_snap_filename_with_hash(snap_file, snap_cache_hash)

        # confirm expected snap cached
        self.assertEqual(3, len(os.listdir(snap_cache.snap_cache_dir)))
        self.assertTrue(
            os.path.isfile(os.path.join(snap_cache.snap_cache_dir,
                                        real_cached_snap)))

        # prune cached snaps
        purned_file_list = snap_cache.prune(keep_hash=snap_cache_hash)

        # confirm other snaps are purged
        self.assertEqual(set(purned_file_list), set(to_be_deleted_files))
        for snap in purned_file_list:
            self.assertFalse(os.path.isfile(snap))

        # confirm the expected cached file still exist
        self.assertEqual(1, len(os.listdir(snap_cache.snap_cache_dir)))
        self.assertTrue(
            os.path.isfile(os.path.join(snap_cache.snap_cache_dir,
                                        real_cached_snap)))
