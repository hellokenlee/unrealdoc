# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import os

from PySide2 import QtCore
from typing import Optional
from qrenderdoc import CaptureContext, PanelMenu

from ..common.singleton import Singleton, Registerable

from .struct_buffer_viewer import StructBufferViewer


class StructBufferViewerManager(Registerable, metaclass=Singleton):

	PrimitiveDataBufferViewerFormatHlsl = \
		os.path.join(os.path.dirname(os.path.abspath(__file__)), "builtinbufferformats/ScenePrimitiveData.hlsl")

	InstanceSceneDataBufferViewerFormatHlsl = \
		os.path.join(os.path.dirname(os.path.abspath(__file__)), "builtinbufferformats/InstanceSceneData.hlsl")

	InstanceSceneDataPanelExtensionSubmenuPath = "Instance Scene Data"

	def __init__(self):
		super(StructBufferViewerManager, self).__init__()
		self._primitive_scene_data_viewer: Optional[StructBufferViewer] = None
		self._instance_scene_data_viewer: Optional[StructBufferViewer] = None
		pass

	def get_primitive_scene_data_viewer(self) -> StructBufferViewer:
		if self._primitive_scene_data_viewer is None:
			assert(self.context is not None)
			self._primitive_scene_data_viewer = StructBufferViewer(self.context, self.PrimitiveDataBufferViewerFormatHlsl)
		return self._primitive_scene_data_viewer

	def get_instance_scene_data_viewer(self) -> StructBufferViewer:
		if self._instance_scene_data_viewer is None:
			assert (self.context is not None)
			self._instance_scene_data_viewer = StructBufferViewer(self.context, self.InstanceSceneDataBufferViewerFormatHlsl)
		return self._instance_scene_data_viewer

	def _on_instance_scene_data_viewer_extension_soa(self, index: int):
		# Some how call back from panel menu is not in the same thread of Qt runing
		# Hack for using QTimer to get this run into Qt thread
		# if self._instance_scene_data_viewer is not None:
		# 	def action_qt_thread():
		# 		self._instance_scene_data_viewer.close()
		# 		self._instance_scene_data_viewer.soa_index = index
		# 		self._instance_scene_data_viewer.view()
		# 	QtCore.QTimer.singleShot(10, action_qt_thread)
		pass
