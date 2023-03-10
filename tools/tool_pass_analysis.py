# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import os
import sys

from .utils import Utils
from .tool_base import ToolBase


class ToolPassAnalysis(ToolBase):

	def __init__(self, *args):
		super(ToolPassAnalysis, self).__init__(*args)
		self.set_title("Pass Analysis")
		self.show_eveluate_button(True)
		self.py_path = self.add_input("PythonPath", "")
		self.root_pass = self.add_input("RootPass", "")
		self.combo_list = ["None", "PrePass DDM_AllOpaque (Forced by DBuffer)", "CompositionBeforeBasePass", "BasePass", "Lights", "Translucency"]
		self.shader_analysis_for_pass = self.add_combo_box("ShaderAnalysisForPass", self.combo_list)
		self.result_path = self.add_result("Analysis Path", "Please click eveluate first!")
		self._processed_py_path = ""
		self._processed_root_pass = ""
		self._processed_file_path = ""
		self._processed_shader_analysis_for_pass = ""
		self._first_time_running = True
		pass

	def save_layout(self, pdict: dict):
		pdict[self.name(self.py_path)] = self.py_path.get_value()
		pdict[self.name(self.root_pass)] = self.root_pass.get_value()
		pass

	def load_layout(self, pdict: dict):
		self.py_path.set_value(pdict.get(self.name(self.py_path), "C:\\Python36"))
		self.root_pass.set_value(pdict.get(self.name(self.root_pass), "Scene"))
		pass

	def eveluate(self):
		# TODO: Make pyechart run in local python env
		self.add_local_python36_lib_path(self.py_path.get_value())

		from .renderdocvisualizer.PassAnalysis import RenderDocAnalysis

		RenderDocAnalysis.LOCAL_PYTHON36_PATH = self.py_path.get_value()
		RenderDocAnalysis.ROOT_NAME = self.root_pass.get_value()
		RenderDocAnalysis.pyrenderdoc = self.context
		RenderDocAnalysis.RDC_FILE = ""
		RenderDocAnalysis.SHADER_RESOURCES_FOR_PASS = self.shader_analysis_for_pass.get_value()

		if self._first_time_running:
			RenderDocAnalysis.main()
			self._first_time_running = False
		else:
			RenderDocAnalysis.update_shader_information_for_pass()
		self.result_path.set_value("%s" % RenderDocAnalysis.g_assetsfolder)
		self._processed_file_path = os.path.join(RenderDocAnalysis.g_assetsfolder, "TopLevelAnalysis.html")
		self._processed_py_path = RenderDocAnalysis.LOCAL_PYTHON36_PATH
		self._processed_root_pass = RenderDocAnalysis.ROOT_NAME
		self._processed_shader_analysis_for_pass = RenderDocAnalysis.SHADER_RESOURCES_FOR_PASS

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
