# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import qrenderdoc

from typing import *


class Singleton(type):
	"""Singletone Meta Class

	__instances: Dict[type, object]
	"""

	__instances = {}

	def __call__(cls, *args, **kwargs):
		if cls not in cls.__instances:
			cls.__instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
		return cls.__instances[cls]


class Registerable(object):

	def __init__(self):
		super(Registerable, self).__init__()
		self.context: Optional[qrenderdoc.CaptureContext] = None
		self.registered = False
		pass

	def register(self, context: qrenderdoc.CaptureContext):
		self.context = context
		self.registered = True
		pass

	def unregister(self):
		self.context = None
		self.registered = False
		pass
