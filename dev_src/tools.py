import os
import re
import shutil
import subprocess
import sys
from typing import Generator, List, Union


def get_codec():
	# return "libx264"

	if sys.platform.startswith('win'):
		data = subprocess.check_output("wmic path win32_VideoController get name", shell=True).decode().lower()
	elif sys.platform.startswith('linux'):
		try:
			subprocess.run(["nvidia-smi"], capture_output=True, check=True)
			data = "nvidia"
		except (subprocess.CalledProcessError, FileNotFoundError):
			try:
				data = subprocess.check_output("lspci | grep VGA", shell=True).decode().lower()
			except Exception as e:
				data = "none"
	elif sys.platform.startswith('darwin'):
		return "videotoolbox"


	if "nvidia" in data:
		# return "libx265"
		# return "hevc_nvenc"
		return "h264_nvenc"
	elif "intel" in data:
		return "h264_qsv"
	elif "amd" in data or "radeon" in data:
		return "h264_amf"
	else:
		return "libx264"

exe_location_cache = {}


def get_exe_location(executable='ffmpeg'):
	return shutil.which(executable)



def set_terminal_title(title):
	if sys.platform.startswith('win'):
		import ctypes
		ctypes.windll.kernel32.SetConsoleTitleW(title)
	else:
		sys.stdout.write(f"\x1b]2;{title}\x07")

def open_explorar(path):
	path = os.path.realpath(path)
	if sys.platform.startswith('win'):
		os.startfile(path)
	elif sys.platform.startswith('linux'):
		subprocess.Popen(["xdg-open", path])
	elif sys.platform.startswith('darwin'):
		subprocess.Popen(["open", path])

def xpath(*path: Union[str, bytes], realpath=False, posix=True, win=False):
	"""
	Join path and normalize it.
	* path: list of strings
	* realpath: return real path
	* posix: use posix path separator
	"""
	d_type = isinstance(path[0], bytes) # detect if path is bytes
	if d_type:
		path = [p.decode() for p in path]
	path:str = os.path.join(*path)
	path = path.replace("\\", "/") if posix else path.replace("/", "\\") if win else path
	path = re.sub(r"/+", "/", path)
	path = re.sub(r"[\\]+", r"\\", path)

	out_path = path if not realpath else os.path.realpath(path)
	return out_path.encode('utf-8') if d_type else out_path

def EXT(path):
	"""
	Returns the extension of the file
	
	ie. EXT("file.txt") -> "txt"
	"""
	return path.rsplit('.', 1)[-1]

def make_dir(*path):
	"""make directory if not exists"""
	path = xpath(*path)
	os.makedirs(path, exist_ok=True)

	return path

def os_scan_walk(*path, allow_dir=False, return_list=True) -> Union[List[os.DirEntry], Generator[os.DirEntry, None, None]]:
	"""
	Iterate through a directory and its subdirectories
	and `yield` the filePath object of each Files and Folders*.

	path: path to the directory
	allow_dir: if True, will also yield directories
	return_list: if True, will return a list of all files and directories. If False, will yield each file and directory.
	"""
	files = []
	for f in os.scandir(xpath(*path)):
		if f.is_file():
			if return_list:
				files.append(f)
			else:
				yield f
		elif f.is_dir():
			if allow_dir:
				if return_list:
					files.append(f)
				else:
					yield f

			if return_list:
				files.extend(os_scan_walk(f.path))
			else:
				for i in os_scan_walk(f.path):
					yield i

	if return_list:
		return files


def is_file(*path):
	return os.path.isfile(xpath(*path))
	
	
class Text_Box:
	def __init__(self):
		self.styles = {
			"equal" : "=",
			"star"    : "*",
			"hash"  : "#",
			"dash"  : "-",
			"udash": "_"
		}

	def box(self, *text, style = "equal"):
		"""
		Returns a string of text with a border around it.
		"""
		text = " ".join(map(str, text))
		term_col = shutil.get_terminal_size()[0]

		s = self.styles[style] if style in self.styles else style
		tt = ""
		for i in text.split('\n'):
			tt += i.center(term_col) + '\n'
		return f"\n\n{s*term_col}\n{tt}{s*term_col}\n\n"

	def print_box(self, *text, style = "equal"):
		"""
		Prints a string of text with a border around it.
		"""
		print(self.box(*text, style=style))


text_box = Text_Box()


def ease_in_out(t, duration, ease_in_time, ease_out_time):
	if t < 0:
		return 0
	if t > duration:
		return 1

	ease_in_end = ease_in_time
	ease_out_start = duration - ease_out_time

	if t < ease_in_end:
		# Ease-in phase (quadratic)
		normalized_time = t / ease_in_time
		return normalized_time ** 2
	elif t < ease_out_start:
		# Linear phase
		return (t - ease_in_end) / (ease_out_start - ease_in_end)
	else:
		# Ease-out phase (quadratic)
		normalized_time = (t - ease_out_start) / ease_out_time
		return 1 - (1 - normalized_time) ** 2

def str_comma(x):
	"""
	To support EU number format (comma instead of dot)
	"""
	try:
		from pyroDB import _PickleTCell
		if isinstance(x, _PickleTCell):
			x = x.value
	except ImportError:
		pass
	if isinstance(x, str):
		if "," in x:
			x = x.replace(",", ".")
		x = float(x)

	x = round(x, 2)
	
	return ("{:.2f}".format(x)).replace('.', ',')
	

def str_comma_to_float(x):
	try:
		from pyroDB import _PickleTCell
		if isinstance(x, _PickleTCell):
			x = x.value
	except ImportError:
		pass
	if isinstance(x, str):
		if "," in x:
			x = x.replace(",", ".")
	return float(x)


if __name__ == '__main__':
	FFMPEG_BINARY = get_exe_location('ffmpeg') or ("./bin.tmp/ffmpeg.exe" if os.path.exists("./bin.tmp/ffmpeg.exe") else None)

	print(f"FFMPEG_BINARY: {FFMPEG_BINARY}")

	CODEC = get_codec()

	print(f"Using {CODEC} codec")

	print(f"FFMPEG_BINARY: {FFMPEG_BINARY}")
	print(f"Using {CODEC} codec")
