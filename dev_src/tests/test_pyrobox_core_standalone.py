"""Regression test: pyroboxCore must work as an isolated single file."""

import shutil
import subprocess
import sys
from pathlib import Path


def test_pyrobox_core_imports_without_project_files(tmp_path):
	source = Path(__file__).resolve().parents[1] / 'pyroboxCore.py'
	standalone = tmp_path / 'pyroboxCore.py'
	shutil.copy2(source, standalone)

	code = (
		"import importlib.util, pathlib; "
		"p=pathlib.Path('pyroboxCore.py').resolve(); "
		"s=importlib.util.spec_from_file_location('pyroboxCore', p); "
		"m=importlib.util.module_from_spec(s); "
		"s.loader.exec_module(m); "
		"assert m.validate_client_relpath('folder/file.txt') == 'folder/file.txt'; "
		"assert m.validate_client_relpath('/etc/passwd') is None"
	)
	result = subprocess.run(
		[sys.executable, '-I', '-c', code],
		cwd=tmp_path,
		capture_output=True,
		text=True,
		timeout=15,
	)

	assert result.returncode == 0, result.stderr


def test_deal_post_data_check_size_limit():
	import pytest
	from pyroboxCore import DealPostData, PostError

	class DummyHandler:
		headers = {'content-type': 'application/json', 'content-length': '500'}

	dpd = DealPostData(DummyHandler())
	dpd.content_length = 500

	# Unlimited (-1) should not raise
	dpd.check_size_limit(max_size=-1)

	# Within limit should not raise
	dpd.check_size_limit(max_size=1000)
	dpd.check_size_limit(max_size=500)

	# Exceeding limit should raise PostError
	with pytest.raises(PostError):
		dpd.check_size_limit(max_size=499)

