"""Tests for handler path resolution used by upload / mutating POSTs."""

import os

import pytest


class TestPathSafetyCheck:
	def test_accepts_relative_and_url_paths(self, handler):
		assert handler.path_safety_check('file.txt') is True
		assert handler.path_safety_check('sub/file.txt') is True
		assert handler.path_safety_check('/folder/file.txt') is True

	def test_rejects_traversal(self, handler):
		assert handler.path_safety_check('../secret') is False
		assert handler.path_safety_check('a/../../b') is False
		assert handler.path_safety_check('/../etc/passwd') is False

	def test_rejects_absolute_fs_style(self, handler):
		# Leading slash alone is URL-style (allowed); drive / UNC are not
		assert handler.path_safety_check('C:/Windows/evil.txt') is False
		assert handler.path_safety_check('//unc/share/x') is False

	def test_rejects_empty(self, handler):
		assert handler.path_safety_check('') is False
		assert handler.path_safety_check('   ') is False


class TestResolveChildPath:
	def test_simple_file_stays_under_root(self, handler, served_dir):
		out = handler.resolve_child_path('/', 'hello.txt')
		assert out is not None
		assert os.path.abspath(out) == os.path.abspath(os.path.join(served_dir, 'hello.txt'))
		assert handler.path_is_under_directory(out)

	def test_nested_folder_upload(self, handler, served_dir):
		out = handler.resolve_child_path('/uploads', 'dir/a.txt')
		assert out is not None
		expected = os.path.abspath(os.path.join(served_dir, 'uploads', 'dir', 'a.txt'))
		assert os.path.abspath(out) == expected

	def test_absolute_unix_filename_rejected(self, handler, served_dir):
		# Classic CVE payload: absolute multipart filename
		target = os.path.abspath(os.path.join(str(served_dir), '..', 'pwned.txt'))
		out = handler.resolve_child_path('/', target.replace('\\', '/'))
		assert out is None
		# And must not create/resolve outside root via join semantics
		assert not os.path.isfile(target)

	def test_absolute_posix_style_rejected(self, handler):
		assert handler.resolve_child_path('/', '/etc/passwd') is None
		assert handler.resolve_child_path('/', '/home/kali/pyrobox_poc_pwned.txt') is None

	def test_windows_drive_rejected(self, handler):
		assert handler.resolve_child_path('/', 'C:/Windows/evil.txt') is None
		assert handler.resolve_child_path('/', 'C:\\Windows\\evil.txt') is None

	def test_dotdot_rejected(self, handler):
		assert handler.resolve_child_path('/', '../outside.txt') is None
		assert handler.resolve_child_path('/sub', 'a/../../outside.txt') is None

	def test_translate_path_does_not_follow_join_discard(self, handler, served_dir):
		"""Even if somehow joined with an absolute name, translate_path remaps under root.

		resolve_child_path must still reject absolute client names before translate.
		"""
		abs_name = os.path.abspath(os.path.join(str(served_dir), '..', 'escape.txt'))
		# Raw translate_path with a URL that includes abs-looking segments stays under root
		remapped = handler.translate_path('/' + abs_name.replace('\\', '/').lstrip('/'))
		assert handler.path_is_under_directory(remapped)
		# resolve_child_path must refuse the absolute client filename
		assert handler.resolve_child_path('/', abs_name) is None


class TestTranslatePathTrailingSlash:
	def test_preserves_trailing_slash(self, handler):
		p = handler.translate_path('/subdir/')
		assert p.endswith(('/', '\\'))

	def test_file_path_has_no_forced_trailing_slash(self, handler):
		p = handler.translate_path('/subdir')
		assert not p.endswith('/')
		assert not p.endswith('\\')
