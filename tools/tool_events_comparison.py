# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import os
import sys

from .utils import Utils
from .tool_base import ToolBase


class ToolEventsComparison(ToolBase):
    def __init__(self, *args):
        super(ToolEventsComparison, self).__init__(*args)
        self.set_title("Events Comparison")
        self.show_eveluate_button(True)
        self.is_x20 = self.add_radio_box("Is X20", True)
        self.root_pass = self.add_input("RootName", "")
        self.file_path = self.add_input("FilePath", "Current File")
        self.control_file_path = self.add_input("CompareFilePath", "")
        self.result_path = self.add_result("Comparison Result", "Please click eveluate first!")
        self._processed_file_path = ""
        self._processed_control_file_path = ""
        self._processed_root_pass = ""
        self._processed_is_x20 = False
        pass

    def save_layout(self, pdict: dict):
        pdict[self.name(self.root_pass)] = self.root_pass.get_value()
        pdict[self.name(self.is_x20)] = self.is_x20.get_checked_value()
        pass

    def load_layout(self, pdict: dict):
        self.root_pass.set_value(pdict.get(self.name(self.root_pass), "Scene"))
        self.is_x20.set_checked_value(pdict.get(self.name(self.is_x20), True))
        pass

    def eveluate(self):
        from .renderdocvisualizer.EventsComparison import EventsComparison

        EventsComparison.pyrenderdoc = self.context
        EventsComparison.ROOT_NAME = self.root_pass.get_value()
        file_path = self.file_path.get_value()
        EventsComparison.RDC_FILE = file_path if file_path != "Current File" else ""
        EventsComparison.CONTROL_RDC_FILE = self.control_file_path.get_value()
        EventsComparison.IS_X20 = self.is_x20.get_checked_value()
        # Read events from frame of control group
        if self._processed_control_file_path != EventsComparison.CONTROL_RDC_FILE or \
            self._processed_file_path != EventsComparison.RDC_FILE or \
                self._processed_root_pass != EventsComparison.ROOT_NAME:
            EventsComparison.main()
        self._processed_file_path = EventsComparison.RDC_FILE
        self._processed_control_file_path = EventsComparison.CONTROL_RDC_FILE
        self._processed_root_pass = EventsComparison.ROOT_NAME
        self._processed_is_x20 = EventsComparison.IS_X20

        self.result_path.set_value("%s" % EventsComparison.g_assets_folder)
        pass
