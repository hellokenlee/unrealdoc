# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import traceback

from typing import List, Callable, Optional
from qrenderdoc import CaptureContext, MiniQtHelper
from PySide2 import QtGui, QtCore, QtWidgets

from .utils import Utils
from .settings import Settings
from .operators import OperatorBase


class ToolItem(object):

	def __init__(self, mqt: MiniQtHelper, label: str, value: QtWidgets.QWidget, default: str):
		super(ToolItem, self).__init__()
		self.mqt = mqt
		self.root = self.mqt.CreateHorizontalContainer()
		self._frozen = False
		#
		self._label = self.mqt.CreateLabel()
		self.mqt.SetWidgetText(self._label, label if label.endswith(":") else (label + ":"))
		self.mqt.AddWidget(self.root, self._label)
		#
		self._value = value
		self._default = default
		self.mqt.SetWidgetText(self._value, default)
		self.mqt.AddWidget(self.root, self._value)
		pass

	def reset(self):
		self.set_value(self._default)
		pass

	def get_value(self) -> str:
		return self.mqt.GetWidgetText(self._value)

	def set_value(self, value: str):
		self.freeze(True)
		self.mqt.SetWidgetText(self._value, str(value))
		self.freeze(False)
		pass

	def freeze(self, frozen: bool):
		self._frozen = frozen
		pass


class ToolInputItem(ToolItem):

	InputCallBack = Callable[[CaptureContext, QtWidgets.QWidget, str], None]
	FormatterCallBack = Callable[[str], str]

	def __init__(self, mqt: MiniQtHelper, label: str, default: str, callback: InputCallBack, formatter: FormatterCallBack):
		super(ToolInputItem, self).__init__(mqt, label, mqt.CreateTextBox(True, self.on_text_box_change), default)
		self._callback = callback
		self._formatter = formatter
		pass

	def set_read_only(self, readonly: bool):
		enabled = not readonly
		self.mqt.SetWidgetEnabled(self._value, enabled)
		pass

	def reformat(self):
		if self._formatter is not None:
			self.set_value(self._formatter(self.get_value()))
		pass

	def on_text_box_change(self, context, widget, text):
		if not self._frozen:
			if self._formatter is not None:
				text = self._formatter(text)
				self.set_value(text)
			self._callback(context, widget, text)
		pass


class ToolResultItem(ToolItem):

	def __init__(self, mqt: MiniQtHelper, label: str, default: str):
		super(ToolResultItem, self).__init__(mqt, label, mqt.CreateLabel(), default)
		self._spacer = self.mqt.CreateSpacer(True)
		self.mqt.AddWidget(self.root, self._spacer)
		pass


class ToolCustomButton(object):

	CustomButtonCallback = Callable[[CaptureContext, QtWidgets.QWidget, str], None]

	def __init__(self, mqt: MiniQtHelper, text: str, callback: CustomButtonCallback):
		super(ToolCustomButton, self).__init__()
		self.mqt = mqt
		self.root = self.mqt.CreateButton(callback)
		self.mqt.SetWidgetText(self.root, text)
		pass

	def set_enabled(self, enabled: bool):
		self.mqt.SetWidgetEnabled(self.root, enabled)
		pass


class ToolComboBoxItem(ToolItem):
	def __init__(self, mqt: MiniQtHelper, label: str, combo_list: list, callback: ToolInputItem.InputCallBack):
		self.combo = mqt.CreateComboBox(True, self.on_combo_box_change)
		super(ToolComboBoxItem, self).__init__(mqt, label, self.combo, combo_list[0])
		self.mqt = mqt
		self.mqt.SetComboOptions(self.combo, combo_list)
		self._callback = callback
		pass

	def set_value(self, value: str):
		self.freeze(True)
		super().set_value(value)
		self.mqt.SelectComboOption(self.combo, value)
		self.freeze(False)
		pass

	def on_combo_box_change(self, context, widget, text):
		self.set_value(text)
		if not self._frozen:
			if self._callback is not None:
				self._callback(context, widget, text)
		pass


class ToolRadioBox(object):
	def __init__(self, mqt: MiniQtHelper, label: str, default: bool):
		super(ToolRadioBox, self).__init__()
		self.mqt = mqt
		self.root = self.mqt.CreateRadiobox(None)
		self.mqt.SetWidgetText(self.root, label)
		self.mqt.SetWidgetChecked(self.root, default)
		pass

	def get_checked_value(self):
		return self.mqt.IsWidgetChecked(self.root)

	def set_checked_value(self, value: bool):
		return self.mqt.SetWidgetChecked(self.root, value)


class ToolBase(object):

	SETTINGS_GROUP_NAME = "Tools"
	SETTINGS_CONFIG_NAME = "Configs"
	WidgetClosedCallback = Callable[[QtWidgets.QWidget], None]

	plugin_dir_path = ""

	def __init__(self, context: CaptureContext):
		super(ToolBase, self).__init__()
		self.mqt = context.Extensions().GetMiniQtHelper()
		self.context = context
		self.root = self.mqt.CreateGroupBox(True)

		#
		self._num_inputs = 0
		self._num_results = 0
		self._spacer = False
		self._mannual_eveluate = False
		self._input_items: List[ToolInputItem] = []

		#
		self.mqt.SetWidgetText(self.root, "ToolBase")

		self._input_label = self.mqt.CreateLabel()
		self.mqt.SetWidgetText(self._input_label, "Inputs:")
		self._input_layout = self.mqt.CreateVerticalContainer()
		self._result_label = self.mqt.CreateLabel()
		self._result_layout = self.mqt.CreateVerticalContainer()
		self.mqt.SetWidgetText(self._result_label, "Results:")
		self._custom_button_layout = self.mqt.CreateHorizontalContainer()
		pass

	def set_title(self, title: str):
		self.mqt.SetWidgetText(self.root, title)
		pass

	def show_eveluate_button(self, show: bool):
		self._mannual_eveluate = show
		pass

	def add_input(self, label: str, default: str, readonly=False, formatter: Optional[ToolInputItem.FormatterCallBack] = None):
		self._num_inputs = self._num_inputs + 1
		item = ToolInputItem(self.mqt, label, default, self.on_input_changed, formatter)
		self.mqt.AddWidget(self._input_layout, item.root)
		item.set_read_only(readonly)
		self._input_items.append(item)
		return item

	def add_result(self, label: str, default: str):
		self._num_results = self._num_results + 1
		item = ToolResultItem(self.mqt, label, default)
		self.mqt.AddWidget(self._result_layout, item.root)
		return item

	def add_custom_button(self, text: str, callback: ToolCustomButton.CustomButtonCallback):
		button = ToolCustomButton(self.mqt, text, callback)
		self.mqt.AddWidget(self._custom_button_layout, button.root)
		return button

	def add_combo_box(self, label: str, combo_list: list, callback: ToolCustomButton.CustomButtonCallback = None):
		combo_box = ToolComboBoxItem(self.mqt, label, combo_list, callback)
		self.mqt.AddWidget(self._input_layout, combo_box.root)
		return combo_box

	def add_radio_box(self, label: str, default: bool):
		radio_box = ToolRadioBox(self.mqt, label, default)
		self.mqt.AddWidget(self._input_layout, radio_box.root)
		return radio_box

	@classmethod
	def add_config(cls, key, default_value=""):
		_cls = cls.__class__ if not isinstance(cls, type) else cls
		if issubclass(_cls, ToolBase):
			Settings()[_cls.SETTINGS_GROUP_NAME][_cls.__name__][_cls.SETTINGS_CONFIG_NAME].setdefault(key, default_value)
		pass

	@classmethod
	def get_config(cls, key):
		_cls = cls.__class__ if not isinstance(cls, type) else cls
		if issubclass(_cls, ToolBase):
			return Settings()[_cls.SETTINGS_GROUP_NAME][_cls.__name__][_cls.SETTINGS_CONFIG_NAME][key]
		return ""

	def save_layout(self, pdict: dict):
		"""
		Override to save a custom data to a local file and restore when the tool is created.
		See also `load_layout`.

		"""
		pass

	def load_layout(self, pdict: dict):
		"""
		Override to save a custom data to a local file and restore when the tool is created.
		See also `save_layout`.
		"""
		pass

	def update(self):
		"""
		Override to update the widget showing to display up-to-date informations.
		"""
		pass

	def operate(self) -> List[OperatorBase]:
		"""
		Override to generate a list of operators that later operate the controller.

		Called when selected event changed.
		"""
		return []

	def eveluate(self):
		"""
		Override to perform your own eveluation to generate result.

		Called when any input chaged.
		"""
		pass

	def show(self):
		"""
		Set the default status of widgets, e.g. collapse a group box.

		Called after creation and added to parent widget
		"""
		pass

	def collapse(self, collapsed: bool):

		# Hack for renderdoc's miniqt dont provide a method to collapse GroupBox
		# Fake a click event
		# click_pos = QtCore.QPoint(11, 11)
		# event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, click_pos, QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.MouseButtons(), QtCore.Qt.NoModifier)
		# QtCore.QCoreApplication.instance().notify(self.root, event)
		self.mqt.SetWidgetChecked(self.root, collapsed)
		pass

	def is_collapsed(self):
		return self.mqt.IsWidgetChecked(self.root)

	def name(self, attrib: any) -> str:
		"""
		Reflect an object's attribute to its name
		"""
		return Utils().get_attribute_name(self, attrib)

	def save_item(self, pdict: dict, attrib: ToolItem):
		pdict[self.name(attrib)] = attrib.get_value()
		pass

	def load_item(self, pdict: dict, attrib: ToolItem, default: str):
		attrib.set_value(pdict.get(self.name(attrib), default))
		pass

	def finalize(self):
		root_spacer = self.mqt.CreateSpacer(False)
		button_spacer = self.mqt.CreateSpacer(True)
		if self._num_inputs > 0:
			self.mqt.AddWidget(self.root, self._input_label)
			self.mqt.AddWidget(self.root, self._input_layout)
		if self._num_results > 0:
			self.mqt.AddWidget(self.root, self._result_label)
			self.mqt.AddWidget(self.root, self._result_layout)
		self.mqt.AddWidget(self.root, self._custom_button_layout)
		self.mqt.AddWidget(self._custom_button_layout, button_spacer)
		self.mqt.AddWidget(self.root, root_spacer)
		if self._spacer:
			input_spacer = self.mqt.CreateSpacer(True)
			result_spacer = self.mqt.CreateSpacer(True)
			self.mqt.AddWidget(self._input_layout, input_spacer)
			self.mqt.AddWidget(self._result_layout, result_spacer)
		if self._mannual_eveluate:
			self.add_custom_button("Eveluate", self.on_eveluate_button_pressed)
		pass

	def on_event_changed(self, event: int):
		"""
		Called when user selected an event.
		"""
		#
		self.__do_update()
		#
		if not self._mannual_eveluate:
			self.__do_eveluate(event)
		pass

	def on_input_changed(self, _context, _widget, _text):
		"""
		Called when any input of this tool is changed.
		"""
		if not self._mannual_eveluate:
			self.__do_eveluate(self.context.CurEvent())
		pass

	def on_eveluate_button_pressed(self, _context, _widget, _text):
		"""
		Called when the mannual eveluate button is pressed.
		"""
		# Only eveluate on release event
		if self._mannual_eveluate:
			self.__do_eveluate(self.context.CurEvent())
		pass

	# noinspection PyBroadException
	def __do_update(self):
		try:
			self.update()
			for input_item in self._input_items:
				input_item.reformat()
		except Exception as _e:
			self.message(traceback.format_exc())
		pass

	# noinspection PyBroadException
	def __do_eveluate(self, event):
		try:
			# Call `operate()`
			operators = self.operate()
			for operator in operators:
				operator.reset()
			for operator in operators:
				operator.do_prepare(self.context, event)

			# Invoke all operators
			for operator in operators:
				self.context.Replay().BlockInvoke(operator.do_invoke)
				# Promt exception for invoking
				if operator.exception is not None:
					msg = "Error while invoking %s::%s:\n\n%s" % (self.__class__.__name__, operator.__class__.__name__, operator.exception)
					self.message(msg)
					break
				elif operator.invoked():
					operator.do_post_invoked()

			# Call `eveluate()`
			self.eveluate()
		except Exception as _e:
			self.message(traceback.format_exc())
			return
		pass

	def message(self, msg: str, title="Debug"):
		self.context.Extensions().MessageDialog(msg, title)
		pass
