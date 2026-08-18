"""Shared test helpers (importable without relying on conftest module path)."""

import argparse
from http.cookies import SimpleCookie


class StubRequest:
	"""Minimal request object for authenticate_handler / authorize_user."""

	def __init__(self, cookie=None, path='/'):
		self.cookie = cookie if cookie is not None else SimpleCookie()
		self.path = path


def make_cli_args(**overrides):
	"""Build argparse.Namespace matching pyrobox CLI defaults for ServerConfig."""
	base = dict(
		server_name=None,
		admin_id=None,
		admin_pass=None,
		no_guest_allowed=False,
		guest_allowed=True,
		no_upload=False,
		no_modify=False,
		no_delete=False,
		no_download=False,
		no_zip=False,
		read_only=False,
		view_only=False,
		zip_limit='6GB',
		no_signup=False,
	)
	base.update(overrides)
	return argparse.Namespace(**base)
