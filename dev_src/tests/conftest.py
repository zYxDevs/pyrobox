"""Pytest config for pyrobox dev_src tests."""

import os
import sys

import pytest

# Ensure dev_src is importable as the working package root
_TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
_DEV_SRC = os.path.abspath(os.path.join(_TESTS_DIR, '..'))
for _p in (_DEV_SRC, _TESTS_DIR):
	if _p not in sys.path:
		sys.path.insert(0, _p)


@pytest.fixture
def served_dir(tmp_path):
	"""Empty directory used as the HTTP served root."""
	root = tmp_path / 'served'
	root.mkdir()
	return root


@pytest.fixture
def handler(served_dir):
	"""Minimal SimpleHTTPRequestHandler instance (no socket)."""
	from pyroboxCore import SimpleHTTPRequestHandler

	h = SimpleHTTPRequestHandler.__new__(SimpleHTTPRequestHandler)
	h.directory = os.fspath(served_dir)
	return h


@pytest.fixture
def default_member_perms():
	from user_mgmt import permits
	return [
		permits.VIEW,
		permits.DOWNLOAD,
		permits.MODIFY,
		permits.DELETE,
		permits.UPLOAD,
		permits.ZIP,
		permits.MEMBER,
	]


@pytest.fixture
def default_admin_perms(default_member_perms):
	from user_mgmt import permits
	return list(default_member_perms) + [permits.ADMIN]


@pytest.fixture
def default_guest_perms():
	from user_mgmt import permits
	return [
		permits.VIEW,
		permits.DOWNLOAD,
		permits.UPLOAD,
		permits.ZIP,
	]


@pytest.fixture
def user_handler(default_member_perms, default_admin_perms, default_guest_perms):
	"""In-memory User_handler with typical default permissions."""
	from user_mgmt import User_handler

	uh = User_handler(init_permissions={
		'member': default_member_perms,
		'admin': default_admin_perms,
		'guest': default_guest_perms,
	})
	uh.load_db('')  # in-memory
	return uh


@pytest.fixture
def member_user(user_handler):
	return user_handler.create_user('alice', 'secret123')


@pytest.fixture
def admin_user(user_handler):
	return user_handler.create_admin('admin', 'adminpass')


@pytest.fixture
def guest_user(user_handler):
	return user_handler.create_guest()
