# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

from typing import List, Optional
from renderdoc import ResourceId
from qrenderdoc import CaptureContext, DockReference, BufferViewer


class HlslPreProcessor(object):

	def __init__(self, filepath: str):
		super(HlslPreProcessor, self).__init__()
		self._filepath = filepath
		self._sources = []
		self._defines = {}
		self._override_defines = {}
		pass

	def define(self, key: str, value: str):
		self._override_defines[key] = value
		pass

	def undefine(self, key):
		self._override_defines.pop(key)
		pass

	def pre_process(self) -> str:
		lines = self._load_file()
		# Pre Process `#define`
		self._split_defines(lines)
		source = "".join(self._sources)
		comments = []
		for key, value in self._defines.items():
			value = self._override_defines[key] if key in self._override_defines else value
			source = source.replace(key, value)
			comments.append("// #define %s %s" % (key, value))

		# Pre Process ...
		# TODO: Add other pre processor
		# Comment hints
		source = "// Defs:\n" + "\n".join(comments) + "\n" + source
		return source

	def _load_file(self) -> List[str]:
		with open(self._filepath, "r") as file:
			lines = file.readlines()
		return lines

	def _split_defines(self, lines: List[str]):
		self._sources.clear()
		self._defines.clear()
		for line in lines:
			if "#define" in line:
				# `#define XXX YYY`
				_, key, value = line.strip().split(" ")
				self._defines[key] = value
			else:
				self._sources.append(line)
		pass


class StructBufferViewer(object):
	def __init__(self, context: CaptureContext, hlslfileptah: str):
		super(StructBufferViewer, self).__init__()
		self.context = context
		self.byte_length = 0
		self.byte_offset = 0
		self.buffer_id = ResourceId.Null()
		self.format_hlsl = HlslPreProcessor(hlslfileptah)
		self._buffer_viewer: Optional[BufferViewer] = None
		self._current_row = 0
		self._current_col = 0
		pass

	def valid(self):
		return self._buffer_viewer is not None

	def view(self, show=True):
		if self.context.GetResource(self.buffer_id) is None:
			return
		format_str = self.format_hlsl.pre_process()
		if self._buffer_viewer is None:
			self._buffer_viewer = self.context.ViewBuffer(self.byte_offset, self.byte_length, self.buffer_id, format_str)
			self._buffer_viewer.Widget().destroyed.connect(self._on_buffer_viewer_close)
			self.context.AddDockWindow(self._buffer_viewer.Widget(), DockReference.MainToolArea, None)
		if show:
			self.context.RaiseDockWindow(self._buffer_viewer.Widget())
		self.scroll_to(self._current_row, self._current_col)
		pass

	def close(self):
		index = self._buffer_viewer.Widget().parent().parent().currentIndex()
		self._buffer_viewer.Widget().parent().parent().tabCloseRequested.emit(index)
		pass

	def scroll_to(self, row: int, col: int):
		if self._buffer_viewer is not None:
			if row > 0:
				# noinspection PyArgumentList
				self._buffer_viewer.ScrollToRow(row)
			if col > 0:
				# noinspection PyArgumentList
				self._buffer_viewer.ScrollToColumn(col)
		self._current_row = row
		self._current_col = col
		pass

	def _on_buffer_viewer_close(self):
		"""
		Hack for adding a view buffer and get noticed when it's destroyed.
		"""
		self._buffer_viewer = None
		pass
