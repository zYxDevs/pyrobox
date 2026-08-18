"""Unit tests for path-security helpers embedded in pyroboxCore."""

import os

import pytest

from pyroboxCore import (
	directory_url_has_trailing_slash,
	path_is_under_directory,
	validate_client_relpath,
)


class TestValidateClientRelpath:
	@pytest.mark.parametrize(
		'name,expected',
		[
			('file.txt', 'file.txt'),
			('sub/dir/file.txt', 'sub/dir/file.txt'),
			('  nested/a.txt  ', 'nested/a.txt'),
			('folder/file.txt/', 'folder/file.txt'),  # trailing slash trimmed
		],
	)
	def test_accepts_relative(self, name, expected):
		assert validate_client_relpath(name, allow_leading_slash=False) == expected

	@pytest.mark.parametrize(
		'name',
		[
			'/etc/passwd',
			'/home/kali/pwned.txt',
			'//unc/share/x',
			'C:/Windows/evil.txt',
			'C:\\Windows\\evil.txt',
			'../etc/passwd',
			'foo/../bar',
			'foo/./bar',
			'foo//bar',
			'',
			'   ',
			'.',
			'..',
			None,
		],
	)
	def test_rejects_dangerous_upload_names(self, name):
		assert validate_client_relpath(name, allow_leading_slash=False) is None

	def test_url_leading_slash_allowed_when_requested(self):
		assert validate_client_relpath('/folder/file.txt', allow_leading_slash=True) == 'folder/file.txt'

	def test_url_leading_slash_rejected_for_uploads(self):
		assert validate_client_relpath('/folder/file.txt', allow_leading_slash=False) is None

	def test_rejects_illegal_chars(self):
		assert validate_client_relpath('foo:bar.txt') is None
		assert validate_client_relpath('a|b') is None


class TestPathIsUnderDirectory:
	def test_inside(self, tmp_path):
		base = tmp_path / 'served'
		base.mkdir()
		child = base / 'a' / 'b.txt'
		assert path_is_under_directory(str(base), str(child)) is True

	def test_prefix_bypass_rejected(self, tmp_path):
		base = tmp_path / 'served'
		base.mkdir()
		evil = tmp_path / 'served_evil' / 'x'
		# Classic startswith footgun: '.../served_evil' starts with '.../served'
		assert str(evil).startswith(str(base))
		assert path_is_under_directory(str(base), str(evil)) is False

	def test_outside_sibling(self, tmp_path):
		base = tmp_path / 'served'
		base.mkdir()
		other = tmp_path / 'other' / 'x.txt'
		assert path_is_under_directory(str(base), str(other)) is False

	def test_same_dir(self, tmp_path):
		base = tmp_path / 'served'
		base.mkdir()
		assert path_is_under_directory(str(base), str(base)) is True


class TestDirectoryTrailingSlash:
	@pytest.mark.parametrize(
		'path,expected',
		[
			('/dir/', True),
			('/dir', False),
			('/dir%2f', True),
			('/dir%2F', True),
			('', False),
		],
	)
	def test_trailing(self, path, expected):
		assert directory_url_has_trailing_slash(path) is expected


class TestJoinAbsoluteDiscard:
	"""Document the os.path.join footgun the upload fix avoids."""

	def test_join_discards_base_on_absolute(self, tmp_path):
		base = str(tmp_path / 'served')
		absolute = os.path.abspath(str(tmp_path / 'outside.txt'))
		joined = os.path.join(base, absolute)
		# On all platforms, absolute second arg wins
		assert os.path.normpath(joined) == os.path.normpath(absolute)
		assert not path_is_under_directory(base, joined) or joined == absolute
