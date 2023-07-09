# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import os
import pickle

from typing import Optional, List
from qrenderdoc import CaptureContext, CaptureViewer, DockReference

from .tools.utils import Utils
from .tools.settings import Settings
from .tools.tool_base import ToolBase


class UnrealDocViewer(CaptureViewer):

	def __init__(self, context: CaptureContext, plugin_root_path: str):
		super(UnrealDocViewer, self).__init__()

		self.mqt = context.Extensions().GetMiniQtHelper()
		self.context = context
		self.window = self.mqt.CreateToplevelWidget("UnrealDoc", lambda c, w, d: UnrealDocViewerManager.on_window_closed())
		self.context.AddCaptureViewer(self)
		self.layout = self.mqt.CreateVerticalContainer()
		self.plugin_root_path = plugin_root_path
		self.mqt.AddWidget(self.window, self.layout)
		self._tools: List[ToolBase] = []

		#
		ToolBase.plugin_dir_path = plugin_root_path

		#
		self.__inittools__(context)
		self.OnEventChanged(context.CurEvent())

		# Tailing Spacer
		self.tail_spacer = self.mqt.CreateSpacer(False)
		self.mqt.AddWidget(self.layout, self.tail_spacer)
		pass

	def __inittools__(self, context: CaptureContext):
		"""
		Init all tools here
		"""
		# noinspection PyBroadException
		try:
			#
			Settings().load()

			# Following the setup of different tools
			from .tools.tool_scene_data import ToolSceneData
			self.add_tool(ToolSceneData)

			from .tools.tool_pass_analysis import ToolPassAnalysis
			self.add_tool(ToolPassAnalysis)
			
			from .tools.tool_mesh_draw_call import ToolMeshDrawCall
			self.add_tool(ToolMeshDrawCall)

			from .tools.tool_events_comparison import ToolEventsComparison
			self.add_tool(ToolEventsComparison)

			from .tools.tool_shader_analyzer import ToolShaderAnalyzer
			self.add_tool(ToolShaderAnalyzer)

			# ...

			#
			Settings().save()
		except Exception as _e:
			import traceback
			UnrealDocViewerManager.message(context, traceback.format_exc())
		pass

	def add_tool(self, tool_cls: type):
		#
		assert(issubclass(tool_cls, ToolBase))

		# Setting
		settings = Settings().setdefault(ToolBase.SETTINGS_GROUP_NAME, {}).setdefault(
			tool_cls.__name__,
			{
				"Enabled": True,
				ToolBase.SETTINGS_CONFIG_NAME: {}
			}
		)

		tool = tool_cls(self.context)

		# Add Tools
		if settings["Enabled"]:
			tool.finalize()
			self._tools.append(tool)
			self.mqt.AddWidget(self.layout, tool.root)
		pass

	def show(self):
		for tool in self._tools:
			tool.show()
		pass

	def load_layout(self, pdict: dict):
		for tool in self._tools:
			tdict = pdict.get(tool.__class__.__name__, {})
			tool.load_layout(tdict)
			is_collapsed = tdict.get("collapsed", False)
			tool.collapse(is_collapsed)
		pass

	def save_layout(self, pdict: dict):
		for tool in self._tools:
			pdict[tool.__class__.__name__] = {
				"collapsed": tool.is_collapsed()
			}
			tool.save_layout(pdict[tool.__class__.__name__])
		pass

	def OnCaptureLoaded(self):
		pass

	def OnCaptureClosed(self):
		UnrealDocViewerManager.on_app_close()
		pass

	def OnSelectedEventChanged(self, event):
		pass

	def OnEventChanged(self, event: int):
		for tool in self._tools:
			tool.on_event_changed(event)
		pass


class UnrealDocViewerManager(object):

	context: CaptureContext = None
	version: str = ""
	windowraised = False
	instance: Optional[UnrealDocViewer] = None
	instance_layout = {}

	LAYOUT_FILENAME = "layout.bin"

	@classmethod
	def open_window(cls, context: CaptureContext, _data):
		shown = False
		if cls.instance is None:
			shown = True
			# Create new window instance
			plugin_root = os.path.dirname(os.path.abspath(__file__))
			cls.instance = UnrealDocViewer(context, plugin_root)
			cls.instance.load_layout(cls.instance_layout)
			context.AddDockWindow(cls.instance.window, DockReference.RightOf, context.GetTextureViewer().Widget(), 0.05)
		context.RaiseDockWindow(cls.instance.window)
		cls.windowraised = True
		if shown:
			cls.instance.show()
		pass

	@classmethod
	def close_window(cls):
		if cls.instance is not None:
			assert (isinstance(cls.instance, UnrealDocViewer))
			cls.instance.mqt.CloseToplevelWidget(cls.instance.window)
		pass

	@classmethod
	def load_layout(cls, pdict):
		cls.instance_layout = pdict.get(UnrealDocViewer.__class__.__name__, {})
		if pdict["windowraise"]:
			cls.open_window(cls.context, None)
		pass

	@classmethod
	def save_layout(cls, pdict):
		pdict["windowraise"] = cls.windowraised
		pdict[UnrealDocViewer.__class__.__name__] = cls.instance_layout
		pass

	@classmethod
	def do_load_layout(cls):
		plugin_root = os.path.dirname(os.path.abspath(__file__))
		layout_path = os.path.join(plugin_root, cls.LAYOUT_FILENAME)
		if os.path.exists(layout_path):
			with open(layout_path, "rb") as file:
				pdict = pickle.load(file)
				cls.load_layout(pdict)
		pass

	@classmethod
	def do_save_layout(cls):
		plugin_root = os.path.dirname(os.path.abspath(__file__))
		layout_path = os.path.join(plugin_root, cls.LAYOUT_FILENAME)
		with open(layout_path, "wb") as file:
			pdict = {}
			cls.save_layout(pdict)
			pickle.dump(pdict, file)
		pass

	@classmethod
	def on_window_closed(cls):
		cls.windowraised = False
		if cls.instance is not None:
			assert (isinstance(cls.instance, UnrealDocViewer))
			cls.instance.save_layout(cls.instance_layout)
			cls.instance.context.RemoveCaptureViewer(cls.instance)
		cls.instance = None
		cls.do_save_layout()
		pass

	@classmethod
	def on_app_start(cls):
		cls.do_load_layout()
		pass

	@classmethod
	def on_app_close(cls):
		if cls.instance is not None:
			cls.instance.save_layout(cls.instance_layout)
		cls.do_save_layout()
		pass

	@classmethod
	def message(cls, context: CaptureContext, msg: str):
		context.Extensions().MessageDialog(msg, "Debug")
		pass

	@classmethod
	def open_settings_json(cls, context: CaptureContext, _data):
		Utils().startfile(Settings().abs_filepath())
		pass
