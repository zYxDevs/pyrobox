"""Account, permission bit, password, and cookie auth tests."""

from http.cookies import SimpleCookie

import pytest

from _helpers import StubRequest

from user_mgmt import (
	User,
	UserPermission,
	clear_user_cookie,
	create_user_cookie,
	permits,
)


class TestPermissionPacking:
	def test_pack_unpack_roundtrip(self):
		flags = [permits.VIEW, permits.DOWNLOAD, permits.MEMBER]
		packed = User.pack_permission_from_list(flags)
		unpacked = User.unpack_permission_to_list(packed)
		assert set(unpacked) == set(flags)

	def test_bit_list_roundtrip(self):
		bits = User.unpack_permission(0b10000011)  # VIEW, DOWNLOAD, MEMBER (bit 7)
		packed = User.pack_permission(bits)
		assert packed == 0b10000011

	def test_empty_get_permissions_is_nopermission(self, user_handler):
		user = user_handler.create_user('noperm', 'x')
		user.revoke_all()
		assert UserPermission.NOPERMISSION in user.get_permissions()
		assert user.NOPERMISSION is True
		assert user.VIEW is False


class TestUserPermissions:
	def test_member_has_expected_flags(self, member_user):
		assert member_user.MEMBER is True
		assert member_user.VIEW is True
		assert member_user.UPLOAD is True
		assert member_user.ADMIN is False
		assert member_user.is_admin() is False

	def test_guest_is_not_member(self, guest_user):
		assert guest_user.username == 'Guest'
		assert guest_user.MEMBER is False
		assert guest_user.VIEW is True
		assert guest_user.ADMIN is False

	def test_admin_has_admin_bit(self, admin_user):
		assert admin_user.is_admin() is True
		assert admin_user.ADMIN is True
		assert admin_user.MEMBER is True
		assert admin_user.DELETE is True

	def test_permit_and_revoke(self, member_user):
		member_user.revoke(permits.UPLOAD)
		assert member_user.UPLOAD is False
		member_user.permit(permits.UPLOAD)
		assert member_user.UPLOAD is True

	def test_permit_nopermission_clears_all(self, member_user):
		member_user.permit(permits.NOPERMISSION)
		assert member_user.VIEW is False
		assert member_user.UPLOAD is False
		assert member_user.NOPERMISSION is True

	def test_revoke_all(self, member_user):
		member_user.revoke_all()
		assert member_user.NOPERMISSION is True


class TestPasswordAndToken:
	def test_check_password_ok(self, member_user):
		assert member_user.check_password('secret123') is True

	def test_check_password_wrong(self, member_user):
		assert member_user.check_password('wrong') is False
		assert member_user.check_password('') is False

	def test_password_change_rotates_token(self, member_user):
		old_token = member_user.token_hex
		member_user.set_password('newpass')
		assert member_user.check_password('newpass') is True
		assert member_user.check_password('secret123') is False
		assert member_user.token_hex != old_token
		assert member_user.check_token(old_token) is False
		assert member_user.check_token(member_user.token_hex) is True


class TestAccountsApi:
	def test_signup_and_login(self, user_handler):
		created = user_handler.server_signup('bob', 'hunter2')
		assert created['status'] == 'success'

		dup = user_handler.server_signup('bob', 'other')
		assert dup['status'] == 'error'

		ok = user_handler.server_login('bob', 'hunter2')
		assert ok['status'] == 'success'

		bad = user_handler.server_login('bob', 'nope')
		assert bad['status'] == 'error'
		assert 'password' in bad['message'].lower() or 'Wrong' in bad['message']

		missing = user_handler.server_login('nobody', 'x')
		assert missing['status'] == 'error'

	def test_delete_user(self, user_handler, member_user):
		assert user_handler.delete_user('alice') is True
		assert user_handler.get_user('alice') is None
		assert user_handler.delete_user('alice') is False

	def test_get_user_cache(self, user_handler, member_user):
		a = user_handler.get_user('alice')
		b = user_handler.get_user('alice')
		assert a is b


class TestCookieAuth:
	def test_create_cookie_roundtrip(self, user_handler, member_user):
		cookie = create_user_cookie(member_user)
		assert cookie['user'].value == 'alice'
		assert cookie['token'].value == member_user.token_hex

		authed = user_handler.authenticate_cookie(cookie)
		assert authed is not None
		assert authed.username == 'alice'

	def test_forged_token_rejected(self, user_handler, member_user):
		cookie = create_user_cookie(member_user)
		cookie['token'] = '0' * 64
		assert user_handler.authenticate_cookie(cookie) is None

	def test_missing_cookie(self, user_handler):
		assert user_handler.authenticate_cookie(None) is None
		assert user_handler.authenticate_cookie(SimpleCookie()) is None

	def test_clear_cookie_expires(self):
		cookie = clear_user_cookie()
		assert cookie['user'].value == ''
		assert int(cookie['user']['expires']) < 0

	def test_handler_falls_back_to_guest(self, user_handler, guest_user):
		req = StubRequest()
		user, cookie = user_handler.authenticate_handler(
			req, allow_guests=True, guest_user=guest_user)
		assert user is guest_user
		assert cookie['user'].value == 'Guest'

	def test_handler_no_guest_returns_none(self, user_handler):
		req = StubRequest()
		user, cookie = user_handler.authenticate_handler(
			req, allow_guests=False, guest_user=None)
		assert user is None
		assert cookie['user'].value == ''

	def test_handler_prefers_valid_cookie_over_guest(
			self, user_handler, member_user, guest_user):
		req = StubRequest(cookie=create_user_cookie(member_user))
		user, _ = user_handler.authenticate_handler(
			req, allow_guests=True, guest_user=guest_user)
		assert user.username == 'alice'
		assert user is not guest_user
