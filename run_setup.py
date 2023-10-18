import os, shutil

# clear dist folder
shutil.rmtree("dist", ignore_errors=True)

os.system("python -m build")

with open('VERSION', 'r') as f:
	version = f.read().strip()

os.system("pip uninstall pyrobox -y")
os.system(f"pip install ./dist/pyrobox-{version}.tar.gz")
# os.system("pyrobox 45454")

# post to pypi
os.system("twine upload dist/*")