# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import os
import sys

from .utils import Utils
from .tool_base import ToolBase


class ToolMeshDrawCall(ToolBase):

	def __init__(self, *args):
		super(ToolMeshDrawCall, self).__init__(*args)
		self.set_title("Mesh Draw Call")
		self.show_eveluate_button(True)
		self.py_path = self.add_input("PythonPath", "")
		self.root_pass = self.add_input("RootName", "")
		self.draw_call_threshold = self.add_input("DrawCallThreshold", "")
		self.result_path = self.add_result("Analysis Path", "Please click eveluate first!")
		self._processed_py_path = ""
		self._processed_root_pass = ""
		self._processed_file_path = ""
		self._processed_draw_call_threshold = ""
		pass

	def save_layout(self, pdict: dict):
		pdict[self.name(self.py_path)] = self.py_path.get_value()
		pdict[self.name(self.root_pass)] = self.root_pass.get_value()
		pdict[self.name(self.draw_call_threshold)] = self.draw_call_threshold.get_value()
		pass

	def load_layout(self, pdict: dict):
		self.py_path.set_value(pdict.get(self.name(self.py_path), "C:\\Python36"))
		self.root_pass.set_value(pdict.get(self.name(self.root_pass), "Scene"))
		self.draw_call_threshold.set_value(pdict.get(self.name(self.draw_call_threshold), "2"))
		pass

	def eveluate(self):
		# TODO: Make pyechart run in local python env
		self.add_local_python36_lib_path(self.py_path.get_value())

		from .renderdocvisualizer.MeshDrawCall import MeshAnalysis

		MeshAnalysis.LOCAL_PYTHON36_PATH = self.py_path.get_value()
		MeshAnalysis.ROOT_NAME = self.root_pass.get_value()
		MeshAnalysis.DRAWCALL_THRESHOLD = int(self.draw_call_threshold.get_value())
		MeshAnalysis.pyrenderdoc = self.context
		MeshAnalysis.RDC_FILE = ""

		MeshAnalysis.main()
		self.result_path.set_value("%s" % MeshAnalysis.g_assetsfolder)
		self._processed_file_path = os.path.join(MeshAnalysis.g_assetsfolder, "MeshDrawCall.html")
		self._processed_py_path = MeshAnalysis.LOCAL_PYTHON36_PATH
		self._processed_root_pass = MeshAnalysis.ROOT_NAME
		self._processed_draw_call_threshold = str(MeshAnalysis.DRAWCALL_THRESHOLD)

		if os.path.exists(self._processed_file_path):
			Utils().startfile(self._processed_file_path)
		pass

	@staticmethod
	def add_local_python36_lib_path(py36path: str):
		lib_path = '{0}\\lib'.format(py36path)
		package_path = '{0}\\lib\\site-packages'.format(py36path)
		dll_path = '{0}\\DLLs'.format(py36path)
		if lib_path not in sys.path:
			sys.path.append(lib_path)
		if package_path not in sys.path:
			sys.path.append(package_path)
		if dll_path not in sys.path:
			sys.path.append(dll_path)
		pass
