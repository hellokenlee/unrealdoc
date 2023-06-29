# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import os
import sys

from .utils import Utils
from .tool_base import ToolBase
from .renderdocvisualizer.pass_analysis import collect_pass_analysis


class ToolPassAnalysis(ToolBase):

	def __init__(self, *args):
		super(ToolPassAnalysis, self).__init__(*args)
		self.set_title("Pass Analysis")
		self.add_config("LocalPythonPath", "C://Python36")
		self.show_eveluate_button(True)
		self.root_pass = self.add_input("RootName", "Scene")
		self.combo_list = ["None", "PrePass DDM_AllOpaque (Forced by DBuffer)", "CompositionBeforeBasePass", "BasePass", "Lights", "Translucency"]
		self.shader_analysis_for_pass = self.add_combo_box("ShaderAnalysisForPass", self.combo_list)
		self.result_path = self.add_result("Analysis Path", "Please click eveluate first!")
		pass

	def save_layout(self, pdict: dict):
		pdict[self.name(self.root_pass)] = self.root_pass.get_value()
		pass

	def load_layout(self, pdict: dict):
		self.load_item(pdict, self.root_pass, "Scene")
		pass

	def eveluate(self):
		collect_pass_analysis(self.root_pass.get_value(), self.context)
		pass
