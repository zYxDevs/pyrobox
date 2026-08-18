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
