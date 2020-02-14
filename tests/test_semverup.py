#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>..
#
# Authors:
#     Santiago Dueñas <sduenas@bitergia.com>
#

import os
import re
import unittest
import unittest.mock

import click.testing

from release_tools import semverup
from release_tools.entry import CategoryChange


VERSION_FILE_NOT_FOUND = (
    "Error: version file not found"
)
VERSION_FILE_NOT_EXISTS = (
    r"Error: version file .+_version\.py does not exist"
)
VERSION_NUMBER_NOT_FOUND = (
    r"Error: version number not found"
)
VERSION_NOT_UPDATED = (
    "Error: no changes found; version number not updated"
)
INVALID_VERSION_NUMBER = (
    r"Error: version number 'invalid format' in .+_version\.py is not a valid semver string"
)
CHANGELOG_DIR_NOT_FOUND = (
    r"Error: changelog entries directory .+ does not exist"
)
CHANGELOG_INVALID_ENTRY_ERROR = (
    r"Error: invalid format for .+; 'title' attribute not found"
)


class TestSemVerUp(unittest.TestCase):
    """Unit tests for semverup script"""

    @staticmethod
    def setup_version_file(filepath, version):
        """Set up an initial version file with the given version number"""

        with open(filepath, mode='w') as fd:
            fd.write("__version__ = \"{}\"".format(version))

    @staticmethod
    def setup_unreleased_entries(dirpath, only_fixed=False):
        """Set up a set of unreleased entry files"""

        titles = ['first change', 'next change', 'last change']

        if only_fixed:
            categories = [
                CategoryChange.FIXED,
                CategoryChange.FIXED,
                CategoryChange.FIXED
            ]
        else:
            categories = [
                CategoryChange.ADDED,
                CategoryChange.FIXED,
                CategoryChange.DEPRECATED
            ]

        authors = ['jsmith', 'jdoe', 'jsmith']

        os.makedirs(dirpath)

        # Create some entries
        for x in range(0, 3):
            filepath = os.path.join(dirpath, str(x) + '.yml')

            with open(filepath, mode='w') as fd:
                msg = "---\ntitle: {}\ncategory: {}\n"
                msg += "author: {}\npull_request: '{}'\nnotes: null\n"
                msg = msg.format(titles[x], categories[x].category, authors[x], x)
                fd.write(msg)

    @staticmethod
    def read_version_number(filepath):
        """Returns the version number stored in a file"""

        # Check version number
        with open(filepath, mode='r') as fd:
            version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                                fd.read(), re.MULTILINE).group(1)
        return version

    @unittest.mock.patch('release_tools.project.Project.unreleased_changes_path',
                         new_callable=unittest.mock.PropertyMock)
    @unittest.mock.patch('release_tools.project.Project.version_file',
                         new_callable=unittest.mock.PropertyMock)
    def test_version_is_updated(self, mock_verfile, mock_dirpath):
        """Check whether the version is updated"""

        runner = click.testing.CliRunner()

        with runner.isolated_filesystem() as fs:
            version_file = os.path.join(fs, '_version.py')
            mock_verfile.return_value = version_file

            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_dirpath.return_value = dirpath

            self.setup_version_file(version_file, "0.1.0")
            self.setup_unreleased_entries(dirpath)

            # Run the script command
            result = runner.invoke(semverup.semverup)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.stdout, "0.2.0\n")

            version = self.read_version_number(version_file)
            self.assertEqual(version, "0.2.0")

    @unittest.mock.patch('release_tools.project.Project.unreleased_changes_path',
                         new_callable=unittest.mock.PropertyMock)
    @unittest.mock.patch('release_tools.project.Project.version_file',
                         new_callable=unittest.mock.PropertyMock)
    def test_dry_run(self, mock_verfile, mock_dirpath):
        """Check whether the version file is not updated in dry mode"""

        runner = click.testing.CliRunner()

        with runner.isolated_filesystem() as fs:
            version_file = os.path.join(fs, '_version.py')
            mock_verfile.return_value = version_file

            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_dirpath.return_value = dirpath

            self.setup_version_file(version_file, "0.8.10")
            self.setup_unreleased_entries(dirpath)

            # Run the script command
            result = runner.invoke(semverup.semverup, ['--dry-run'])
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.stdout, "0.9.0\n")

            # Version number file did not change
            version = self.read_version_number(version_file)
            self.assertEqual(version, "0.8.10")

    @unittest.mock.patch('release_tools.project.Project.unreleased_changes_path',
                         new_callable=unittest.mock.PropertyMock)
    @unittest.mock.patch('release_tools.project.Project.version_file',
                         new_callable=unittest.mock.PropertyMock)
    def test_patch_number_is_bumped(self, mock_verfile, mock_dirpath):
        """Check whether the patch number is bumped when there are only fixing changes"""

        runner = click.testing.CliRunner()

        with runner.isolated_filesystem() as fs:
            version_file = os.path.join(fs, '_version.py')
            mock_verfile.return_value = version_file

            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_dirpath.return_value = dirpath

            self.setup_version_file(version_file, "0.8.10")
            self.setup_unreleased_entries(dirpath, only_fixed=True)

            # Run the script command
            result = runner.invoke(semverup.semverup)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.stdout, "0.8.11\n")

            version = self.read_version_number(version_file)
            self.assertEqual(version, "0.8.11")

    @unittest.mock.patch('release_tools.project.Project.unreleased_changes_path',
                         new_callable=unittest.mock.PropertyMock)
    @unittest.mock.patch('release_tools.project.Project.version_file',
                         new_callable=unittest.mock.PropertyMock)
    def test_minor_number_is_bumped(self, mock_verfile, mock_dirpath):
        """Check whether the patch number is bumped when there are mixed changes"""

        runner = click.testing.CliRunner()

        with runner.isolated_filesystem() as fs:
            version_file = os.path.join(fs, '_version.py')
            mock_verfile.return_value = version_file

            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_dirpath.return_value = dirpath

            self.setup_version_file(version_file, "0.8.10")
            self.setup_unreleased_entries(dirpath)

            # Run the script command
            result = runner.invoke(semverup.semverup)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.stdout, "0.9.0\n")

            # Check version number
            version = self.read_version_number(version_file)
            self.assertEqual(version, "0.9.0")

    @unittest.mock.patch('release_tools.project.Project.unreleased_changes_path',
                         new_callable=unittest.mock.PropertyMock)
    @unittest.mock.patch('release_tools.project.Project.version_file',
                         new_callable=unittest.mock.PropertyMock)
    def test_version_number_not_bumped_when_empty_changelog_dir(self,
                                                                mock_verfile,
                                                                mock_dirpath):
        """Check if the version does not change when no changes are available"""

        runner = click.testing.CliRunner(mix_stderr=False)

        with runner.isolated_filesystem() as fs:
            version_file = os.path.join(fs, '_version.py')
            mock_verfile.return_value = version_file

            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_dirpath.return_value = dirpath

            self.setup_version_file(version_file, "0.8.10")

            # Create an empty dir
            os.makedirs(dirpath)

            # Run the script command
            result = runner.invoke(semverup.semverup)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertEqual(lines[-2], VERSION_NOT_UPDATED)

            # Check if the version number did not change
            version = self.read_version_number(version_file)
            self.assertEqual(version, "0.8.10")

    @unittest.mock.patch('release_tools.project.Project.unreleased_changes_path',
                         new_callable=unittest.mock.PropertyMock)
    @unittest.mock.patch('release_tools.project.Project.version_file',
                         new_callable=unittest.mock.PropertyMock)
    def test_changelog_dir_not_exists_error(self, mock_verfile, mock_dirpath):
        """Check if it returns an error when the changelog dir does not exist"""

        runner = click.testing.CliRunner(mix_stderr=False)

        with runner.isolated_filesystem() as fs:
            version_file = os.path.join(fs, '_version.py')
            mock_verfile.return_value = version_file

            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_dirpath.return_value = dirpath

            self.setup_version_file(version_file, "0.8.10")

            # Run the script command
            result = runner.invoke(semverup.semverup)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertRegex(lines[-2], CHANGELOG_DIR_NOT_FOUND)

            # Check if the version number did not change
            version = self.read_version_number(version_file)
            self.assertEqual(version, "0.8.10")

    @unittest.mock.patch('release_tools.project.Project.unreleased_changes_path',
                         new_callable=unittest.mock.PropertyMock)
    @unittest.mock.patch('release_tools.project.Project.version_file',
                         new_callable=unittest.mock.PropertyMock)
    def test_changelog_invalid_entry_error(self, mock_verfile, mock_dirpath):
        """Check if it returns an error when a changelog entry is invalid"""

        runner = click.testing.CliRunner(mix_stderr=False)

        with runner.isolated_filesystem() as fs:
            version_file = os.path.join(fs, '_version.py')
            mock_verfile.return_value = version_file

            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_dirpath.return_value = dirpath

            self.setup_version_file(version_file, "0.8.10")
            self.setup_unreleased_entries(dirpath)

            # Create an invalid entry
            entry_fp = os.path.join(dirpath, 'invalid.yml')

            with open(entry_fp, mode='w') as fd:
                msg = "---category: added\n"
                msg += "author: jsmith\npull_request: '42'\nnotes: 'some notes go here'\n"
                fd.write(msg)

            # Run the script command
            result = runner.invoke(semverup.semverup)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertRegex(lines[-2], CHANGELOG_INVALID_ENTRY_ERROR)

            # Check if the version number did not change
            version = self.read_version_number(version_file)
            self.assertEqual(version, "0.8.10")

    @unittest.mock.patch('release_tools.project.Project.unreleased_changes_path',
                         new_callable=unittest.mock.PropertyMock)
    @unittest.mock.patch('release_tools.project.Project.version_file',
                         new_callable=unittest.mock.PropertyMock)
    def test_version_file_not_found(self, mock_verfile, mock_dirpath):
        """Check whether it fails when the version file is not found"""

        runner = click.testing.CliRunner(mix_stderr=False)

        with runner.isolated_filesystem() as fs:
            mock_verfile.return_value = None

            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_dirpath.return_value = dirpath

            self.setup_unreleased_entries(dirpath)

            # Run the script command
            result = runner.invoke(semverup.semverup)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertEqual(lines[-2], VERSION_FILE_NOT_FOUND)

    @unittest.mock.patch('release_tools.project.Project.unreleased_changes_path',
                         new_callable=unittest.mock.PropertyMock)
    @unittest.mock.patch('release_tools.project.Project.version_file',
                         new_callable=unittest.mock.PropertyMock)
    def test_version_file_not_exists(self, mock_verfile, mock_dirpath):
        """Check whether it fails when the version file does not exist"""

        runner = click.testing.CliRunner(mix_stderr=False)

        with runner.isolated_filesystem() as fs:
            version_file = os.path.join(fs, '_version.py')
            mock_verfile.return_value = version_file

            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_dirpath.return_value = dirpath

            self.setup_unreleased_entries(dirpath)

            # Run the script command
            result = runner.invoke(semverup.semverup)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertRegex(lines[-2], VERSION_FILE_NOT_EXISTS)

    @unittest.mock.patch('release_tools.project.Project.unreleased_changes_path',
                         new_callable=unittest.mock.PropertyMock)
    @unittest.mock.patch('release_tools.project.Project.version_file',
                         new_callable=unittest.mock.PropertyMock)
    def test_version_not_found(self, mock_verfile, mock_dirpath):
        """Check whether it fails when the version string is not found in the file"""

        runner = click.testing.CliRunner(mix_stderr=False)

        with runner.isolated_filesystem() as fs:
            version_file = os.path.join(fs, '_version.py')
            mock_verfile.return_value = version_file

            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_dirpath.return_value = dirpath

            # Write an invalid format
            with open(version_file, mode='w') as fd:
                fd.write("invalid format")

            self.setup_unreleased_entries(dirpath)

            # Run the script command
            result = runner.invoke(semverup.semverup)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertRegex(lines[-2], VERSION_NUMBER_NOT_FOUND)

    @unittest.mock.patch('release_tools.project.Project.unreleased_changes_path',
                         new_callable=unittest.mock.PropertyMock)
    @unittest.mock.patch('release_tools.project.Project.version_file',
                         new_callable=unittest.mock.PropertyMock)
    def test_version_invalid_format(self, mock_verfile, mock_dirpath):
        """Check whether it fails when the version file has an invalid format"""

        runner = click.testing.CliRunner(mix_stderr=False)

        with runner.isolated_filesystem() as fs:
            version_file = os.path.join(fs, '_version.py')
            mock_verfile.return_value = version_file

            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_dirpath.return_value = dirpath

            self.setup_version_file(version_file, "invalid format")
            self.setup_unreleased_entries(dirpath)

            # Run the script command
            result = runner.invoke(semverup.semverup)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertRegex(lines[-2], INVALID_VERSION_NUMBER)


if __name__ == '__main__':
    unittest.main()