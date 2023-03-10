# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import os
import sys

DLL_PATH = os.path.join(os.path.dirname(__file__), "../.dbg/dlls")
EGG_PATH = os.path.join(os.path.dirname(__file__), "../.dbg/pydevd-pycharm.egg")


def connect_debug_server(enable):
	if not enable:
		return
	if os.path.exists(EGG_PATH):
		abspath = os.path.abspath(EGG_PATH)
		if abspath not in sys.path:
			sys.path.append(abspath)

	if os.path.exists(DLL_PATH):
		abspath = os.path.abspath(DLL_PATH)
		if abspath not in sys.path:
			sys.path.append(abspath)

	# noinspection PyUnresolvedReferences
	import pydevd_pycharm
	pydevd_pycharm.settrace('localhost', port=1091, stdoutToServer=True, stderrToServer=True, suspend=False)
	print("[Debug] Info: Connected to pycharm debugger.")
	pass


def disconnect_debug_server(enable):
	if not enable:
		return
	# noinspection PyBroadException
	try:
		# noinspection PyUnresolvedReferences
		import pydevd
		print("[Debug] Info: Disconnecting to pycharm debugger.")
		pydevd.stoptrace()
	except Exception as _e:
		pass
	pass
