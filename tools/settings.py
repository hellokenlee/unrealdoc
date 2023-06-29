# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import os
import json
from ..common.singleton import Singleton


class Settings(dict, metaclass=Singleton):

	SETTINGS_FILE_PATH = "settings.json"

	def __init__(self):
		super(Settings, self).__init__()
		pass

	def save(self):
		json.dump(self, open(self.abs_filepath(), "w"), indent=4)
		pass

	def load(self):
		if os.path.exists(self.abs_filepath()):
			json_dict = json.load(open(self.abs_filepath()))
			self.update(json_dict)
		pass

	def abs_filepath(self) -> str:
		plugin_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir)
		settings_path = os.path.join(plugin_root, self.SETTINGS_FILE_PATH)
		return settings_path
