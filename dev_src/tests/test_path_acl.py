"""Per-user URL path ACL (allowed_paths) tests."""

import pytest

from user_mgmt import normalize


class TestNormalize:
	def test_basic(self):
		assert normalize('/docs') == '/docs'
		assert normalize('/docs/') == '/docs'
		assert normalize('docs') == '/docs'

	def test_dotdot(self):
		assert normalize('/a/../b') == '/b'
		assert normalize('/a/b/../c') == '/a/c'

	def test_encoded_dotdot(self):
		# %2e%2e decoded then normalized
		assert normalize('/%2e%2e/secret') == '/secret'

	def test_backslashes(self):
		assert normalize('\\docs\\a') == '/docs/a'

	def test_root(self):
		assert normalize('/') == '/'
		assert normalize('') == '/'


class TestPathAclEmptyMeansAllow:
	def test_unrestricted(self, member_user):
		assert member_user.allowed_paths == []
		assert member_user.is_path_allowed('/') is True
		assert member_user.is_path_allowed('/anything/deep') is True


class TestPathAclAllowDeny:
	def test_allow_recursive(self, member_user):
		member_user.set_allowed_paths([
			{'path': '/docs', 'subdirs': True, 'type': 'allow'},
		])
		assert member_user.is_path_allowed('/docs') is True
		assert member_user.is_path_allowed('/docs/a') is True
		assert member_user.is_path_allowed('/docs/a/b.txt') is True
		assert member_user.is_path_allowed('/other') is False

	def test_deny_more_specific_wins(self, member_user):
		member_user.set_allowed_paths([
			{'path': '/docs', 'subdirs': True, 'type': 'allow'},
			{'path': '/docs/secret', 'subdirs': True, 'type': 'deny'},
		])
		assert member_user.is_path_allowed('/docs/readme') is True
		assert member_user.is_path_allowed('/docs/secret') is False
		assert member_user.is_path_allowed('/docs/secret/x') is False

	def test_subdirs_false_only_direct_children(self, member_user):
		member_user.set_allowed_paths([
			{'path': '/docs', 'subdirs': False, 'type': 'allow'},
		])
		assert member_user.is_path_allowed('/docs') is True
		assert member_user.is_path_allowed('/docs/file.txt') is True
		assert member_user.is_path_allowed('/docs/sub/file.txt') is False

	def test_ancestor_navigation_to_allowed_child(self, member_user):
		member_user.set_allowed_paths([
			{'path': '/projects/alpha', 'subdirs': True, 'type': 'allow'},
		])
		# Must be able to walk down from root / projects
		assert member_user.is_path_allowed('/') is True
		assert member_user.is_path_allowed('/projects') is True
		assert member_user.is_path_allowed('/projects/alpha') is True
		assert member_user.is_path_allowed('/projects/alpha/src') is True
		assert member_user.is_path_allowed('/projects/beta') is False
		assert member_user.is_path_allowed('/other') is False

	def test_deny_only_rule_blocks(self, member_user):
		member_user.set_allowed_paths([
			{'path': '/private', 'subdirs': True, 'type': 'deny'},
		])
		assert member_user.is_path_allowed('/private') is False
		assert member_user.is_path_allowed('/private/x') is False
		# No allow rules → unrelated paths denied
		assert member_user.is_path_allowed('/public') is False

	def test_json_string_allowed_paths(self, member_user):
		import json
		member_user.update('allowed_paths', json.dumps([
			{'path': '/ok', 'subdirs': True, 'type': 'allow'},
		]))
		assert member_user.is_path_allowed('/ok/file') is True
		assert member_user.is_path_allowed('/nope') is False

	def test_longest_match_allow_over_shorter_deny(self, member_user):
		member_user.set_allowed_paths([
			{'path': '/data', 'subdirs': True, 'type': 'deny'},
			{'path': '/data/public', 'subdirs': True, 'type': 'allow'},
		])
		assert member_user.is_path_allowed('/data/private') is False
		assert member_user.is_path_allowed('/data/public') is True
		assert member_user.is_path_allowed('/data/public/x') is True


class TestEndpointAclEnforcement:
	def test_path_allowed_for_file_mutation_and_query_endpoints(self, member_user):
		member_user.set_allowed_paths([
			{'path': '/allowed', 'subdirs': True, 'type': 'allow'},
		])
		# Allowed path operations
		assert member_user.is_path_allowed('/allowed/file.txt') is True
		assert member_user.is_path_allowed('/allowed/sub/dir') is True

		# Disallowed operations (must fail ACL check for upload, delete, rename, edit, size, etc.)
		assert member_user.is_path_allowed('/forbidden') is False
		assert member_user.is_path_allowed('/forbidden/target.txt') is False
		assert member_user.is_path_allowed('/etc/passwd') is False

	def test_rename_both_source_and_destination_must_be_allowed(self, member_user):
		member_user.set_allowed_paths([
			{'path': '/sandbox', 'subdirs': True, 'type': 'allow'},
		])
		# Both inside sandbox: permitted
		assert member_user.is_path_allowed('/sandbox/old.txt') and member_user.is_path_allowed('/sandbox/new.txt')
		# Source outside: forbidden
		assert not (member_user.is_path_allowed('/secret/old.txt') and member_user.is_path_allowed('/sandbox/new.txt'))
		# Destination outside: forbidden
		assert not (member_user.is_path_allowed('/sandbox/old.txt') and member_user.is_path_allowed('/secret/new.txt'))

