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
import re
import shutil

from snapcraft.file_utils import calculate_sha3_384
from ._cache import SnapcraftProjectCache


logger = logging.getLogger(__name__)


class SnapCache(SnapcraftProjectCache):
    """Cache for snap revisions."""
    def __init__(self, *, project_name):
        super().__init__(project_name=project_name)
        self.snap_cache_dir = self._setup_snap_cache()

    def _setup_snap_cache(self):
        snap_cache_path = os.path.join(self.project_cache_root, 'revisions')
        os.makedirs(snap_cache_path, exist_ok=True)
        return snap_cache_path

    def cache(self, snap_filename):
        """Cache snap revision in XDG cache, unless exists.

        :returns: path to cached revision.
        """
        file_hash = calculate_sha3_384(snap_filename)
        cached_snap = _rewrite_snap_filename_with_hash(
            snap_filename, file_hash)
        cached_snap_path = os.path.join(self.snap_cache_dir, cached_snap)
        try:
            if not os.path.isfile(cached_snap_path):
                shutil.copy2(snap_filename, cached_snap_path)
        except OSError:
            logger.warning(
                'Unable to cache snap {}.'.format(cached_snap))

        # verify if the snap file and cached file have the same hash
        cached_snap_hash = calculate_sha3_384(cached_snap_path)
        if file_hash != cached_snap_hash:
            raise ValueError(
                'source file hash and cahced file hash are not matched!')
        return file_hash, cached_snap_path

    def prune(self, *, keep_hash):
        """Prune the snap revisions beside the keep_revision in XDG cache.

        :returns: pruned files paths list.
        """
        pruned_files_list = []

        for snap_filename in os.listdir(self.snap_cache_dir):
            cached_snap = os.path.join(self.snap_cache_dir, snap_filename)

            # get the file hash from file name
            hash_from_snap_file = _get_hash_from_snap_filename(
                snap_filename)

            if hash_from_snap_file != keep_hash:
                try:
                    os.remove(cached_snap)
                    pruned_files_list.append(cached_snap)
                except OSError:
                    logger.warning(
                        'Unable to purge snap {}.'.format(cached_snap))
        return pruned_files_list

    def get_latest(self, snap_name):
        """Get most recently cached snap."""

        cached_snaps = [
            os.path.join(self.snap_cache_dir, f) for f in os.listdir(
                self.snap_cache_dir) if f.startswith(snap_name)]
        if not cached_snaps:
            return None
        return max(cached_snaps, key=os.path.getctime)


def _rewrite_snap_filename_with_hash(snap_file, file_hash):
    """generate the unified cached filename"""
    # '{name}_{version}_{arch}_{hash}.snap'
    splitf = os.path.splitext(snap_file)
    snap_name_with_hash = '{base}_{file_hash}{ext}'.format(
        base=splitf[0],
        file_hash=file_hash,
        ext=splitf[1])
    return snap_name_with_hash


def _get_hash_from_snap_filename(snap_filename):
    """parse the filename to extract the hash info"""
    # the cached snap filename should have the format:
    # '{name}_{version}_{arch}_{hash}.snap'
    filename, extname = os.path.splitext(snap_filename)
    split_name_parts = filename.split('_')
    if len(split_name_parts) != 4:
        logger.debug('The cached snap filename {} is invalid.'.format(
            snap_filename))
        return None

    file_hash = split_name_parts[-1]
    # check if sha3_384 hexdigest str from file name is valid
    SHA3_384_REGEX = '^[0-9a-f]{96}$'
    pattern = re.compile(SHA3_384_REGEX)
    if pattern.match(file_hash) is None:
        logger.debug('The cached snap filename has an invalid sha3_384 hash.')
        return None
    return file_hash
