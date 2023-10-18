#!/usr/bin/env python3
# -*- coding: utf-8 -*-



# TODO
# ----------------------------------------------------------------
# * ADD MORE FILE TYPES
# * ADD SEARCH


import html
from string import Template
import os
import sys
import posixpath
import shutil

import datetime

import importlib.util

import urllib.parse
import urllib.request

import subprocess
import json
from http import HTTPStatus

import traceback

from .pyroboxCore import config, logger, SimpleHTTPRequestHandler as SH_base, DealPostData as DPD, run as run_server, tools, reload_server, __version__

from ._fs_utils import get_titles, dir_navigator, get_dir_size, get_dir_m_time, get_stat, get_tree_count_n_size, _get_tree_path_n_size, fmbytes, humanbytes
from ._arg_parser import main as arg_parser
from . import _page_templates as pt
from ._exceptions import LimitExceed
from ._zipfly_manager import ZIP_Manager

__version__ = __version__
true = T = True
false = F = False
enc = "utf-8"

###########################################
# ADD COMMAND LINE ARGUMENTS
###########################################
arg_parser(config)
cli_args = config.parser.parse_known_args()[0]
config.PASSWORD = cli_args.password

logger.info(tools.text_box("Server Config", *({i: getattr(cli_args, i)} for i in vars(cli_args))))

###########################################
config.dev_mode = False
pt.pt_config.dev_mode = config.dev_mode

config.MAIN_FILE = os.path.abspath(__file__)

config.disabled_func.update({
			"send2trash": False,
			"natsort": False,
			"zip": False,
			"update": False,
			"delete": False,
			"download": False,
			"upload": False,
			"new_folder": False,
			"rename": False,
})

########## ZIP MANAGER ################################
config.max_zip_size = 6*1024*1024*1024
zip_manager = ZIP_Manager(config, size_limit=config.max_zip_size)

#######################################################



# INSTALL REQUIRED PACKAGES
REQUEIREMENTS= ['send2trash', 'natsort']




def check_installed(pkg):
	return bool(importlib.util.find_spec(pkg))



def run_update():
	dep_modified = False

	import sysconfig, pip

	i = "pyrobox"
	more_arg = ""
	if pip.__version__ >= "6.0":
		more_arg += " --disable-pip-version-check"
	if pip.__version__ >= "20.0":
		more_arg += " --no-python-version-warning"


	py_h_loc = os.path.dirname(sysconfig.get_config_h_filename())
	on_linux = f'export CPPFLAGS="-I{py_h_loc}";'
	command = "" if config.OS == "Windows" else on_linux
	comm = f'{command} {sys.executable} -m pip install -U --user {more_arg} {i}'

	try:
		subprocess.call(comm, shell=True)
	except Exception as e:
		logger.error(traceback.format_exc())
		return False


	#if i not in get_installed():
	if not check_installed(i):
		return False

	ver = subprocess.check_output(['pyrobox', "-v"]).decode()

	if ver > __version__:
		return True


	print("Failed to load ", i)
	return False



#############################################
#            PATCH SERVER CLASS            #
#############################################



class SH(SH_base):
	"""
	Just a wrapper for SH_base to add some extra functionality
	"""
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def send_error(self, code, message=None, explain=None):
		print("ERROR", code, message, explain)

		displaypath = self.get_displaypath(self.url_path)

		title = get_titles(displaypath)

		_format = pt.error_page().safe_substitute(
			PY_PAGE_TITLE=title,
			PY_PUBLIC_URL=config.address(),
			PY_DIR_TREE_NO_JS=dir_navigator(displaypath))

		return super().send_error(code, message, explain, Template(_format))




#############################################
#                FILE HANDLER               #
#############################################



def list_directory_json(self:SH, path=None):
	"""Helper to produce a directory listing (JSON).
	Return json file of available files and folders"""
	if path is None:
		path = self.translate_path(self.path)

	try:
		dir_list = scansort(os.scandir(path))
	except OSError:
		self.send_error(
			HTTPStatus.NOT_FOUND,
			"No permission to list directory")
		return None
	dir_dict = []


	for file in dir_list:
		name = file.name
		displayname = linkname = name


		if file.is_dir():
			displayname = f"{name}/"
			linkname = f"{name}/"
		elif file.is_symlink():
			displayname = f"{name}@"

		dir_dict.append([urllib.parse.quote(linkname, errors='surrogatepass'),
						html.escape(displayname, quote=False)])

	return self.send_json(dir_dict)



def list_directory(self:SH, path):
	"""Helper to produce a directory listing (absent index.html).

	Return value is either a file object, or None (indicating an
	error).  In either case, the headers are sent, making the
	interface the same as for send_head().

	"""

	try:
		dir_list = scansort(os.scandir(path))
	except OSError:
		self.send_error(
			HTTPStatus.NOT_FOUND,
			"No permission to list directory")
		return None
	displaypath = self.get_displaypath(self.url_path)


	title = get_titles(displaypath)


	r = [
		pt.directory_explorer_header().safe_substitute(
			PY_PAGE_TITLE=title,
			PY_PUBLIC_URL=config.address(),
			PY_DIR_TREE_NO_JS=dir_navigator(displaypath),
		)
	]
	r_li= [] # type + file_link
	f_li = [] # file_names
	s_li = [] # size list

	r_folders = [] # no js
	r_files = [] # no js


	LIST_STRING = '<li><a class= "%s" href="%s">%s</a></li><hr>'

	r.append("""
			<div id="content_list">
				<ul id="linkss">
					<!-- CONTENT LIST (NO JS) -->
			""")


	# r.append("""<a href="../" style="background-color: #000;padding: 3px 20px 8px 20px;border-radius: 4px;">&#128281; {Prev folder}</a>""")
	for file in dir_list:
		#fullname = os.path.join(path, name)
		name = file.name
		displayname = linkname = name
		size=0
		# Append / for directories or @ for symbolic links
		_is_dir_ = True
		if file.is_dir():
			displayname = f"{name}/"
			linkname = f"{name}/"
		elif file.is_symlink():
			displayname = f"{name}@"
		else:
			_is_dir_ =False
			size = fmbytes(file.stat().st_size)
			__, ext = posixpath.splitext(name)
			if ext=='.html':
				r_files.append(LIST_STRING % ("link", urllib.parse.quote(linkname,
									errors='surrogatepass'),
									html.escape(displayname, quote=False)))

				r_li.append('h'+ urllib.parse.quote(linkname, errors='surrogatepass'))
			elif self.guess_type(linkname).startswith('video/'):
				r_files.append(LIST_STRING % ("vid", urllib.parse.quote(linkname,
									errors='surrogatepass'),
									html.escape(displayname, quote=False)))

				r_li.append('v'+ urllib.parse.quote(linkname, errors='surrogatepass'))
			elif self.guess_type(linkname).startswith('image/'):
				r_files.append(LIST_STRING % ("file", urllib.parse.quote(linkname,
									errors='surrogatepass'),
									html.escape(displayname, quote=False)))

				r_li.append('i'+ urllib.parse.quote(linkname, errors='surrogatepass'))
			else:
				r_files.append(LIST_STRING % ("file", urllib.parse.quote(linkname,
									errors='surrogatepass'),
									html.escape(displayname, quote=False)))

				r_li.append('f'+ urllib.parse.quote(linkname, errors='surrogatepass'))
			f_li.append(html.escape(displayname, quote=False))

		if _is_dir_:
			r_folders.append(LIST_STRING % ("", urllib.parse.quote(linkname,
									errors='surrogatepass'),
									html.escape(displayname, quote=False)))

			r_li.append('d' + urllib.parse.quote(linkname, errors='surrogatepass'))
			f_li.append(html.escape(displayname, quote=False))

		s_li.append(size)



	r.extend(r_folders)
	r.extend(r_files)

	r.extend(
		(
			"""</ul>
				</div>
				<!-- END CONTENT LIST (NO JS) -->
				<div id="js-content_list" class="jsonly"></div>
			""",
			pt.file_list().safe_substitute(),
		)
	)
	if (
		not cli_args.no_upload
		and not cli_args.read_only
		and not cli_args.view_only
	):

		r.append(pt.upload_form().safe_substitute(PY_PUBLIC_URL=config.address()))

	r.append(pt.file_list_script().safe_substitute(PY_LINK_LIST=str(r_li),
										PY_FILE_LIST=str(f_li),
										PY_FILE_SIZE =str(s_li)))


	encoded = '\n'.join(r).encode(enc, 'surrogateescape')

	return self.send_txt(HTTPStatus.OK, encoded)





if not os.path.isdir(config.log_location):
	try:
		os.mkdir(path=config.log_location)
	except Exception:
		config.log_location ="./"




if not config.disabled_func["send2trash"]:
	try:
		from send2trash import send2trash, TrashPermissionError
	except Exception:
		config.disabled_func["send2trash"] = True
		logger.warning("send2trash module not found, send2trash function disabled")

if not config.disabled_func["natsort"]:
	try:
		import natsort
	except Exception:
		config.disabled_func["natsort"] = True
		logger.warning("natsort module not found, natsort function disabled")

def humansorted(li):
	if not config.disabled_func["natsort"]:
		return natsort.humansorted(li)

	return sorted(li, key=lambda x: x.lower())

def scansort(li):
	if not config.disabled_func["natsort"]:
		return natsort.humansorted(li, key=lambda x:x.name)

	return sorted(li, key=lambda x: x.name.lower())

def listsort(li):
	return humansorted(li)


























# download file from url using urllib
def fetch_url(url, file = None):
	try:
		with urllib.request.urlopen(url) as response:
			data = response.read() # a `bytes` object
			if not file:
				return data

		with open(file, 'wb') as f:
			f.write(data)
		return data
	except Exception:
		traceback.print_exc()
		return None




class PostError(Exception):
	pass






@SH.on_req('HEAD', '/favicon.ico')
def send_favicon(self: SH, *args, **kwargs):
	self.redirect('https://cdn.jsdelivr.net/gh/RaSan147/py_httpserver_Ult@main/assets/favicon.ico')

@SH.on_req('HEAD', hasQ="reload")
def reload(self: SH, *args, **kwargs):
	# RELOADS THE SERVER BY RE-READING THE FILE, BEST FOR TESTING REMOTELY. VULNERABLE
	config.reload = True

	reload_server()

@SH.on_req('HEAD', hasQ="admin")
def admin_page(self: SH, *args, **kwargs):
	title = "ADMIN PAGE"
	url_path = kwargs.get('url_path', '')
	displaypath = self.get_displaypath(url_path)

	head = pt.directory_explorer_header().safe_substitute(PY_PAGE_TITLE=title,
												PY_PUBLIC_URL=config.address(),
												PY_DIR_TREE_NO_JS=dir_navigator(displaypath))

	tail = pt.admin_page().template
	return self.return_txt(HTTPStatus.OK,  f"{head}{tail}")

@SH.on_req('HEAD', hasQ="update")
def update(self: SH, *args, **kwargs):
	"""Check for update and return the latest version"""
	if data := fetch_url(
		"https://raw.githubusercontent.com/RaSan147/py_httpserver_Ult/main/VERSION"
	):
		data  = data.decode("utf-8").strip()
		ret = json.dumps({"update_available": data > __version__, "latest_version": data})
		return self.return_txt(HTTPStatus.OK, ret)
	else:
		return self.return_txt(HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to fetch latest version")

@SH.on_req('HEAD', hasQ="update_now")
def update_now(self: SH, *args, **kwargs):
	"""Run update"""
	if config.disabled_func["update"]:
		return self.return_txt(HTTPStatus.OK, json.dumps({"status": 0, "message": "UPDATE FEATURE IS UNAVAILABLE !"}))
	if data := run_update():
		return self.return_txt(HTTPStatus.OK, json.dumps({"status": 1, "message": "UPDATE SUCCESSFUL !"}))
	else:
		return self.return_txt(HTTPStatus.OK, json.dumps({"status": 0, "message": "UPDATE FAILED !"}))

@SH.on_req('HEAD', hasQ="size")
def get_size(self: SH, *args, **kwargs):
	"""Return size of the file"""
	url_path = kwargs.get('url_path', '')

	xpath = self.translate_path(url_path)

	stat = get_stat(xpath)
	if not stat:
		return self.return_txt(HTTPStatus.OK, json.dumps({"status": 0}))
	size = stat.st_size if os.path.isfile(xpath) else get_dir_size(xpath)
	humanbyte = humanbytes(size)
	fmbyte = fmbytes(size)
	return self.return_txt(HTTPStatus.OK, json.dumps({"status": 1,
														"byte": size,
														"humanbyte": humanbyte,
														"fmbyte": fmbyte}))

@SH.on_req('HEAD', hasQ="size_n_count")
def get_size_n_count(self: SH, *args, **kwargs):
	"""Return size of the file"""
	url_path = kwargs.get('url_path', '')

	xpath = self.translate_path(url_path)

	stat = get_stat(xpath)
	if not stat:
		return self.return_txt(HTTPStatus.OK, json.dumps({"status": 0}))
	if os.path.isfile(xpath):
		count, size = 1, stat.st_size
	else:
		count, size = get_tree_count_n_size(xpath)

	humanbyte = humanbytes(size)
	fmbyte = fmbytes(size)
	return self.return_txt(HTTPStatus.OK, json.dumps({"status": 1,
														"byte": size,
														"humanbyte": humanbyte,
														"fmbyte": fmbyte,
														"count": count}))


@SH.on_req('HEAD', hasQ="czip")
def create_zip(self: SH, *args, **kwargs):
	"""Create ZIP task and return ID"""
	path = kwargs.get('path', '')
	url_path = kwargs.get('url_path', '')
	spathsplit = kwargs.get('spathsplit', '')

	if config.disabled_func["zip"]:
		return self.return_txt(HTTPStatus.INTERNAL_SERVER_ERROR, "ERROR: ZIP FEATURE IS UNAVAILABLE !")

	# dir_size = get_dir_size(path, limit=6*1024*1024*1024)

	# if dir_size == -1:
	# 	msg = "Directory size is too large, please contact the host"
	# 	return self.return_txt(HTTPStatus.OK, msg)

	displaypath = self.get_displaypath(url_path)
	filename = f"{spathsplit[-2]}.zip"

	title = "Creating ZIP"

	head = pt.directory_explorer_header().safe_substitute(PY_PAGE_TITLE=title,
											PY_PUBLIC_URL=config.address(),
											PY_DIR_TREE_NO_JS=dir_navigator(displaypath))

	try:
		zid = zip_manager.get_id(path)

		tail = pt.zip_script().safe_substitute(PY_ZIP_ID = zid,
												PY_ZIP_NAME = filename)
		return self.return_txt(HTTPStatus.OK, f"{head} {tail}")

	except LimitExceed:
		tail = "<h3>Directory size is too large, please contact the host</h3>"
		return self.return_txt(HTTPStatus.SERVICE_UNAVAILABLE, f"{head} {tail}")
	except Exception:
		self.log_error(traceback.format_exc())
		return self.return_txt(HTTPStatus.OK, "ERROR")

@SH.on_req('HEAD', hasQ="zip")
def get_zip(self: SH, *args, **kwargs):
	"""Return ZIP file if available
	Else return progress of the task"""
	path = kwargs.get('path', '')
	spathsplit = kwargs.get('spathsplit', '')

	query = self.query
	msg = False

	def reply(status, msg=""):
		return self.send_json({
			"status": status,
			"message": msg
		})

	if not os.path.isdir(path):
		msg = "Folder not found. Failed to create zip"
		self.log_error(msg)
		return reply("ERROR", msg)


	filename = f"{spathsplit[-2]}.zip"

	id = query["zid"][0]

	# IF NOT STARTED
	if zip_manager.calculating(id):
		return reply("CALCULATING")

	if not zip_manager.zip_id_status(id):
		t = zip_manager.archive_thread(path, id)
		t.start()

		return reply("SUCCESS", "ARCHIVING")


	if zip_manager.zip_id_status[id] == "DONE":
		if query("download"):
			path = zip_manager.zip_ids[id]

			return self.return_file(path, filename, True)


		if query("progress"):
			return reply("DONE") #if query("progress") or no query

	# IF IN PROGRESS
	if zip_manager.zip_id_status[id] == "ARCHIVING":
		progress = zip_manager.zip_in_progress[id]
		# return self.return_txt(HTTPStatus.OK, "%.2f" % progress)
		return reply("PROGRESS", "%.2f" % progress)

	if zip_manager.zip_id_status[id].startswith("ERROR"):
		# return self.return_txt(HTTPStatus.OK, zip_manager.zip_id_status[id])
		return reply("ERROR", zip_manager.zip_id_status[id])

@SH.on_req('HEAD', hasQ="json")
def send_ls_json(self: SH, *args, **kwargs):
	"""Send directory listing in JSON format"""
	return list_directory_json(self)

@SH.on_req('HEAD', hasQ="vid")
def send_video_page(self: SH, *args, **kwargs):
	# SEND VIDEO PLAYER
	path = kwargs.get('path', '')
	url_path = kwargs.get('url_path', '')

	vid_source = url_path
	if not self.guess_type(path).startswith('video/'):
		self.send_error(HTTPStatus.NOT_FOUND, "THIS IS NOT A VIDEO FILE")
		return None

	displaypath = self.get_displaypath(url_path)



	title = get_titles(displaypath, file=True)

	r = [
		pt.directory_explorer_header().safe_substitute(
			PY_PAGE_TITLE=title,
			PY_PUBLIC_URL=config.address(),
			PY_DIR_TREE_NO_JS=dir_navigator(displaypath),
		)
	]
	ctype = self.guess_type(path)
	warning = ""

	if ctype not in ['video/mp4', 'video/ogg', 'video/webm']:
		warning = ('<h2>It seems HTML player may not be able to play this Video format, Try Downloading</h2>')


	r.append(pt.video_script().safe_substitute(PY_VID_SOURCE=vid_source,
												PY_FILE_NAME = displaypath.split("/")[-1],
												PY_CTYPE=ctype,
												PY_UNSUPPORT_WARNING=warning))



	encoded = '\n'.join(r).encode(enc, 'surrogateescape')
	return self.return_txt(HTTPStatus.OK, encoded)



@SH.on_req('HEAD', url_regex="/@assets/.*")
def send_assets(self: SH, *args, **kwargs):
	"""Send assets"""
	if not config.ASSETS:
		self.send_error(HTTPStatus.NOT_FOUND, "Assets not available")
		return None


	path = kwargs.get('path', '')
	spathsplit = kwargs.get('spathsplit', '')

	path = config.ASSETS_dir + "/".join(spathsplit[2:])
	#	print("USING ASSETS", path)

	if not os.path.isfile(path):
		self.send_error(HTTPStatus.NOT_FOUND, "File not found")
		return None

	return self.return_file(path)



@SH.on_req('HEAD')
def default_get(self: SH, filename=None, *args, **kwargs):
	"""Serve a GET request."""
	path = kwargs.get('path', '')

	if os.path.isdir(path):
		parts = urllib.parse.urlsplit(self.path)
		if not parts.path.endswith('/'):
			# redirect browser - doing basically what apache does
			self.send_response(HTTPStatus.MOVED_PERMANENTLY)
			new_parts = parts[0], parts[1], f'{parts[2]}/', parts[3], parts[4]
			new_url = urllib.parse.urlunsplit(new_parts)
			self.send_header("Location", new_url)
			self.send_header("Content-Length", "0")
			self.end_headers()
			return None
		for index in "index.html", "index.htm":
			index = os.path.join(path, index)
			if os.path.exists(index):
				path = index
				break
		else:
			return list_directory(self, path)

	# check for trailing "/" which should return 404. See Issue17324
	# The test for this was added in test_httpserver.py
	# However, some OS platforms accept a trailingSlash as a filename
	# See discussion on python-dev and Issue34711 regarding
	# parseing and rejection of filenames with a trailing slash

	if path.endswith("/"):
		self.send_error(HTTPStatus.NOT_FOUND, "File not found")
		return None



	# else:

	if cli_args.view_only or cli_args.no_download:
		if not os.path.exists(path):
			return self.send_error(HTTPStatus.NOT_FOUND, "File not found")
		return self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Download is disabled")
	return self.return_file(path, filename)













def AUTHORIZE_POST(req: SH, post:DPD, post_type=''):
	"""Check if the user is authorized to post"""

	# START
	post.start()
	form = post.form

	verify_1 = form.get_multi_field(verify_name='post-type', verify_msg=post_type, decode=T)


	# GET UID
	uid_verify = form.get_multi_field(verify_name='post-uid', decode=T)

	if uid := uid_verify[1]:
		##################################

		# HANDLE USER PERMISSION BY CHECKING UID

		##################################

		return uid
	else:
		raise PostError("Invalid request: No uid provided")





@SH.on_req('POST', hasQ="upload")
def upload(self: SH, *args, **kwargs):
	"""GET Uploaded files"""
	if cli_args.no_upload or cli_args.read_only or cli_args.view_only:
		return self.send_txt(HTTPStatus.SERVICE_UNAVAILABLE, "Upload not allowed")


	path = kwargs.get('path')
	url_path = kwargs.get('url_path')


	post = DPD(self)


	# AUTHORIZE
	uid = AUTHORIZE_POST(self, post, 'upload')

	form = post.form

	if not uid:
		return None


	uploaded_files = [] # Uploaded folder list



	# PASSWORD SYSTEM
	password = form.get_multi_field(verify_name='password', decode=T)[1]

	self.log_debug(f'post password: {[password]} by client')
	if password != config.PASSWORD: # readline returns password with \r\n at end
		self.log_info(f"Incorrect password by {uid}")

		return self.send_txt(HTTPStatus.UNAUTHORIZED, "Incorrect password")

	while post.remainbytes > 0:
		fn = form.get_file_name() # reads the next line and returns the file name
		if not fn:
			return self.send_error(HTTPStatus.BAD_REQUEST, "Can't find out file name...")


		path = self.translate_path(self.path)
		rltv_path = posixpath.join(url_path, fn)

		temp_fn = os.path.join(path, f".LStemp-{fn[0]}.tmp")
		config.temp_file.add(temp_fn)


		fn = os.path.join(path, fn)



		line = post.get() # content type
		line = post.get() # line gap



		# ORIGINAL FILE STARTS FROM HERE
		try:
			with open(temp_fn, 'wb') as out:
				preline = post.get()
				while post.remainbytes > 0:
					line = post.get()
					if post.boundary in line:
						preline = preline[:-1]
						if preline.endswith(b'\r'):
							preline = preline[:-1]
						out.write(preline)
						uploaded_files.append(rltv_path,)
						break
					else:
						out.write(preline)
						preline = line


			while cli_args.no_update and os.path.isfile(fn):
				n = 1
				name, ext = os.path.splitext(fn)
				fn = f"{name}({n}){ext}"
				n += 1
			os.replace(temp_fn, fn)



		except (IOError, OSError):
			traceback.print_exc()
			return self.send_txt(HTTPStatus.SERVICE_UNAVAILABLE, "Can't create file to write, do you have permission to write?")

		finally:
			try:
				os.remove(temp_fn)
				config.temp_file.remove(temp_fn)

			except OSError:
				pass



	return self.return_txt(HTTPStatus.OK, "File(s) uploaded")





@SH.on_req('POST', hasQ="del-f")
def del_2_recycle(self: SH, *args, **kwargs):
	"""Move 2 recycle bin"""

	if cli_args.read_only or cli_args.view_only or cli_args.no_delete:
		return self.send_json({"head": "Failed", "body": "Recycling unavailable! Try deleting permanently..."})

	path = kwargs.get('path')
	url_path = kwargs.get('url_path')


	post = DPD(self)

	# AUTHORIZE
	uid = AUTHORIZE_POST(self, post, 'del-f')
	form = post.form

	if config.disabled_func["send2trash"]:
		return self.send_json({"head": "Failed", "body": "Recycling unavailable! Try deleting permanently..."})



	# File link to move to recycle bin
	filename = form.get_multi_field(verify_name='name', decode=T)[1].strip()

	path = self.get_rel_path(filename)
	xpath = self.translate_path(posixpath.join(url_path, filename))

	self.log_warning(f'<-send2trash-> {xpath} by {[uid]}')

	head = "Failed"
	try:
		send2trash(xpath)
		msg = f"Successfully Moved To Recycle bin{post.refresh}"
		head = "Success"
	except TrashPermissionError:
		msg = "Recycling unavailable! Try deleting permanently..."
	except Exception as e:
		traceback.print_exc()
		msg = f"<b>{path}</b> {e.__class__.__name__}"

	return self.send_json({"head": head, "body": msg})





@SH.on_req('POST', hasQ="del-p")
def del_permanently(self: SH, *args, **kwargs):
	"""DELETE files permanently"""
	if cli_args.read_only or cli_args.view_only or cli_args.no_delete:
		return self.send_json({"head": "Failed", "body": "Recycling unavailable! Try deleting permanently..."})

	path = kwargs.get('path')
	url_path = kwargs.get('url_path')


	post = DPD(self)

	# AUTHORIZE
	uid = AUTHORIZE_POST(self, post, 'del-p')
	form = post.form



	# File link to move to recycle bin
	filename = form.get_multi_field(verify_name='name', decode=T)[1].strip()
	path = self.get_rel_path(filename)

	xpath = self.translate_path(posixpath.join(url_path, filename))

	self.log_warning(f'Perm. DELETED {xpath} by {[uid]}')


	try:
		if os.path.isfile(xpath): os.remove(xpath)
		else: shutil.rmtree(xpath)

		return self.send_json(
			{"head": "Success", "body": f"PERMANENTLY DELETED  {path}{post.refresh}"}
		)


	except Exception as e:
		traceback.print_exc()
		return self.send_json(
			{"head": "Failed", "body": f"<b>{path}<b>{e.__class__.__name__}"}
		)





@SH.on_req('POST', hasQ="rename")
def rename_content(self: SH, *args, **kwargs):
	"""Rename files"""

	print(cli_args.read_only , cli_args.view_only , cli_args.no_update)

	if cli_args.read_only or cli_args.view_only or cli_args.no_update:
		return self.send_json({"head": "Failed", "body": "Renaming is disabled."})


	path = kwargs.get('path')
	url_path = kwargs.get('url_path')


	post = DPD(self)

	# AUTHORIZE
	uid = AUTHORIZE_POST(self, post, 'rename')
	form = post.form



	# File link to move to recycle bin
	filename = form.get_multi_field(verify_name='name', decode=T)[1].strip()

	new_name = form.get_multi_field(verify_name='data', decode=T)[1].strip()

	path = self.get_rel_path(filename)


	xpath = self.translate_path(posixpath.join(url_path, filename))


	new_path = self.translate_path(posixpath.join(url_path, new_name))

	self.log_warning(f'Renamed "{xpath}" to "{new_path}" by {[uid]}')


	try:
		os.rename(xpath, new_path)
		return self.send_json({"head": "Renamed Successfully", "body":  post.refresh})
	except Exception as e:
		return self.send_json(
			{
				"head": "Failed",
				"body": f"<b>{path}</b><br><b>{e.__class__.__name__}</b> : {str(e)}",
			}
		)





@SH.on_req('POST', hasQ="info")
def get_info(self: SH, *args, **kwargs):
	"""Get files permanently"""
	path = kwargs.get('path')
	url_path = kwargs.get('url_path')

	script = None


	post = DPD(self)

	# AUTHORIZE
	uid = AUTHORIZE_POST(self, post, 'info')
	form = post.form





	# File link to move to check info
	filename = form.get_multi_field(verify_name='name', decode=T)[1].strip()

	path = self.get_rel_path(filename) # the relative path of the file or folder

	xpath = self.translate_path(posixpath.join(url_path, filename)) # the absolute path of the file or folder


	self.log_warning(f'Info Checked "{xpath}" by: {[uid]}')

	if not os.path.exists(xpath):
		return self.send_json({"head":"Failed", "body":"File/Folder Not Found"})

	file_stat = get_stat(xpath)
	if not file_stat:
		return self.send_json({"head":"Failed", "body":"Permission Denied"})

	data = []
	data.append(["Name", urllib.parse.unquote(filename, errors= 'surrogatepass')])

	if os.path.isfile(xpath):
		data.append(["Type","File"])
		if "." in filename:
			data.append(["Extension", filename.rpartition(".")[2]])

		size = file_stat.st_size
		data.append(["Size", humanbytes(size) + " (%i bytes)"%size])

	else: #if os.path.isdir(xpath):
		data.append(["Type", "Folder"])
		# size = get_dir_size(xpath)

		data.append(["Total Files", '<span id="f_count">Please Wait</span>'])


		data.append(["Total Size", '<span id="f_size">Please Wait</span>'])
		script = '''
		tools.fetch_json(tools.full_path("''' + path + '''?size_n_count")).then(resp => {
		console.log(resp);
		if (resp.status) {
			size = resp.humanbyte;
			count = resp.count;
			document.getElementById("f_size").innerHTML = resp.humanbyte + " (" + resp.byte + " bytes)";
			document.getElementById("f_count").innerHTML = count;
		} else {
			throw new Error(resp.msg);
		}}).catch(err => {
		console.log(err);
		document.getElementById("f_size").innerHTML = "Error";
		});
		'''

	data.append(["Path", path])

	def get_dt(time):
		return datetime.datetime.fromtimestamp(time)

	data.append(["Created on", get_dt(file_stat.st_ctime)])
	data.append(["Last Modified", get_dt(file_stat.st_mtime)])
	data.append(["Last Accessed", get_dt(file_stat.st_atime)])

	body = """
<style>
table {
font-family: arial, sans-serif;
border-collapse: collapse;
width: 100%;
}

td, th {
border: 1px solid #00BFFF;
text-align: left;
padding: 8px;
}

tr:nth-child(even) {
background-color: #111;
}
</style>

<table>
<tr>
<th>About</th>
<th>Info</th>
</tr>
"""
	for key, val in data:
		body += "<tr><td>{key}</td><td>{val}</td></tr>".format(key=key, val=val)
	body += "</table>"

	return self.send_json({"head":"Properties", "body":body, "script":script})



@SH.on_req('POST', hasQ="new_folder")
def new_folder(self: SH, *args, **kwargs):
	"""Create new folder"""
	path = kwargs.get('path')
	url_path = kwargs.get('url_path')

	post = DPD(self)

	# AUTHORIZE
	uid = AUTHORIZE_POST(self, post, 'new_folder')
	form = post.form

	filename = form.get_multi_field(verify_name='name', decode=T)[1].strip()

	path = self.get_rel_path(filename)

	xpath = filename
	if xpath.startswith(('../', '..\\', '/../', '\\..\\')) or '/../' in xpath or '\\..\\' in xpath or xpath.endswith(('/..', '\\..')):
		return self.send_json({"head": "Failed", "body": f"Invalid Path:  {path}"})

	xpath = self.translate_path(posixpath.join(url_path, filename))


	self.log_warning(f'New Folder Created "{xpath}" by: {[uid]}')

	try:
		if os.path.exists(xpath):
			return self.send_json(
				{"head": "Failed", "body": f"Folder Already Exists:  {path}"}
			)
		if os.path.isfile(xpath):
			return self.send_json(
				{"head": "Failed", "body": f"File Already Exists:  {path}"}
			)
		os.makedirs(xpath)
		return self.send_json(
			{"head": "Success", "body": f"New Folder Created:  {path}{post.refresh}"}
		)

	except Exception as e:
		self.log_error(traceback.format_exc())
		return self.send_json({"head": "Failed", "body": f"<b>{ path }</b><br><b>{ e.__class__.__name__ }</b>"})





@SH.on_req('POST')
def default_post(self: SH, *args, **kwargs):
	raise PostError("Bad Request")




































# proxy for old versions
def run():
	run_server(handler=SH)

if __name__ == '__main__':
	run()
