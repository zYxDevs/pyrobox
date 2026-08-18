"""ServerConfig permission defaults from CLI flags + authorize_user."""

import pytest

from _helpers import StubRequest, make_cli_args
from user_mgmt import create_user_cookie, permits


@pytest.fixture
def anonymous_config():
	"""Nameless server: guests on, in-memory DBs (no files written)."""
	from pyrobox_ServerHost import ServerConfig
	return ServerConfig(make_cli_args())


class TestAnonymousServerPerms:
	def test_guest_created_without_member(self, anonymous_config):
		guest = anonymous_config.guest_id
		assert guest is not None
		assert guest.MEMBER is False
		assert guest.VIEW is True

	def test_member_template_keeps_member_bit(self, anonymous_config):
		# Regression: guest_perms must not alias/mutate member_perms
		assert permits.MEMBER in anonymous_config.member_perms
		assert permits.MEMBER not in anonymous_config.guest_perms

	def test_authorize_guest_without_cookie(self, anonymous_config):
		user, cookie = anonymous_config.authorize_user(StubRequest())
		assert user is not None
		assert user.username == 'Guest'
		assert cookie['user'].value == 'Guest'

	def test_guest_vs_member_password_rules(self, anonymous_config):
		"""Guests use CoreConfig.PASSWORD for uploads; members use account password."""
		from pyroboxCore import config as CoreConfig

		guest = anonymous_config.guest_id
		member = anonymous_config.user_handler.create_user('mem', 'acct-pass')

		assert not guest.MEMBER
		assert CoreConfig.PASSWORD == 'SECret'

		assert member.MEMBER
		assert member.check_password('acct-pass')
		assert not member.check_password('SECret')


class TestCliPermissionFlags:
	def _config(self, **kwargs):
		from pyrobox_ServerHost import ServerConfig
		return ServerConfig(make_cli_args(**kwargs))

	def test_no_upload(self):
		cfg = self._config(no_upload=True)
		assert permits.UPLOAD not in cfg.member_perms
		assert permits.UPLOAD not in cfg.guest_perms
		assert permits.VIEW in cfg.member_perms

	def test_read_only(self):
		cfg = self._config(read_only=True)
		for p in (permits.UPLOAD, permits.MODIFY, permits.DELETE):
			assert p not in cfg.member_perms
			assert p not in cfg.guest_perms
		assert permits.DOWNLOAD in cfg.member_perms
		assert permits.VIEW in cfg.member_perms

	def test_view_only(self):
		cfg = self._config(view_only=True)
		for p in (permits.UPLOAD, permits.MODIFY, permits.DELETE, permits.DOWNLOAD):
			assert p not in cfg.member_perms
		assert permits.VIEW in cfg.member_perms

	def test_no_guest_allowed(self):
		cfg = self._config(no_guest_allowed=True)
		assert cfg.GUESTS is False
		assert not hasattr(cfg, 'guest_id')
		user, cookie = cfg.authorize_user(StubRequest())
		assert user is None
		assert cookie['user'].value == ''


class TestNamedServerBootstrap:
	def test_creates_admin_in_tmp(self, tmp_path, monkeypatch):
		from pyroboxCore import config as CoreConfig
		from pyrobox_ServerHost import ServerConfig

		monkeypatch.setattr(CoreConfig, 'MAIN_FILE_dir', str(tmp_path))

		cfg = ServerConfig(make_cli_args(
			server_name='testsrv',
			admin_id='root',
			admin_pass='rootpass',
			guest_allowed=True,
		))
		admin = cfg.user_handler.get_user('root')
		assert admin is not None
		assert admin.is_admin()
		assert admin.check_password('rootpass')

		users = cfg.get_users()
		assert 'root' in users

		assert permits.VIEW in cfg.guest_perms
		guest = cfg.guest_id
		assert guest.VIEW is True
		assert guest.MEMBER is False

	def test_wrong_admin_password_raises(self, tmp_path, monkeypatch):
		from pyroboxCore import config as CoreConfig
		from pyrobox_ServerHost import ServerConfig

		monkeypatch.setattr(CoreConfig, 'MAIN_FILE_dir', str(tmp_path))

		ServerConfig(make_cli_args(
			server_name='srv2',
			admin_id='root',
			admin_pass='correct',
		))
		with pytest.raises(ValueError):
			ServerConfig(make_cli_args(
				server_name='srv2',
				admin_id='root',
				admin_pass='wrong',
			))


class TestAuthorizePrefersCookie:
	def test_logged_in_member(self, anonymous_config):
		member = anonymous_config.user_handler.create_user('carol', 'pw')
		req = StubRequest(cookie=create_user_cookie(member))
		user, _ = anonymous_config.authorize_user(req)
		assert user.username == 'carol'
		assert user.MEMBER is True
