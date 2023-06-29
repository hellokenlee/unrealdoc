# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import renderdoc
import qrenderdoc

from typing import *
from ..common.singleton import Singleton, Registerable


# noinspection PyMethodMayBeStatic
class Utils(object, metaclass=Singleton):

	def __init__(self):
		super(Utils, self).__init__()
		pass

	def startfile(self, filepath, msec=1):
		from PySide2 import QtCore

		def invoke():
			import os
			os.startfile(filepath)

		QtCore.QTimer.singleShot(msec, invoke)
		pass

	def get_attribute_name(self, obj, var) -> str:
		for k, v in obj.__dict__.items():
			if v is var:
				return k
		return ""

	def action_in_pass(self, action: renderdoc.ActionDescription, pname: str):
		cur_action = action
		while cur_action is not None:
			if pname in cur_action.customName:
				return True
			cur_action = cur_action.parent
		return False


# noinspection PyMethodMayBeStatic
class PipelineStateUtils(Registerable, metaclass=Singleton):

	def __init__(self):
		super(PipelineStateUtils, self).__init__()
		pass

	def find_resource(self, state: renderdoc.PipeState, resource_name: str, stage: Optional[renderdoc.ShaderStage] = None):
		return self.find_readonly_resource(state, resource_name, stage) + self.find_readwrite_resource(state, resource_name, stage)

	def find_readonly_resource(self, state: renderdoc.PipeState, resource_name: str, stage: Optional[renderdoc.ShaderStage] = None) -> List[renderdoc.ResourceId]:
		return self._internal_find_resources(resource_name, state.GetReadOnlyResources, True, stage)

	def find_readwrite_resource(self, state: renderdoc.PipeState, resource_name: str, stage: Optional[renderdoc.ShaderStage] = None) -> List[renderdoc.ResourceId]:
		return self._internal_find_resources(resource_name, state.GetReadWriteResources, True, stage)

	def get_root_signature_resource(self, state: renderdoc.PipeState) -> Optional[renderdoc.ResourceId]:
		pipline_id = state.GetGraphicsPipelineObject()
		pipeline_resource = self.context.GetResource(pipline_id)
		for resource_id in pipeline_resource.parentResources:
			if self.context.GetResourceName(resource_id).startswith("Root Signature"):
				return resource_id
		return None

	def _internal_find_resources(self, resource_name: str, get_resource_lambda: callable, usedonly: bool, stage: renderdoc.ShaderStage) -> List[renderdoc.ResourceId]:
		#
		result = []
		# Check all stage
		if stage is None:
			stages = [renderdoc.ShaderStage.Vertex, renderdoc.ShaderStage.Pixel, renderdoc.ShaderStage.Compute]
		else:
			stages = [stage]
		# Find in readonly resource
		for stage in stages:
			resources_list = get_resource_lambda(stage, usedonly)
			for resources in resources_list:
				for resource in resources.resources:
					if self.context.GetResourceName(resource.resourceId) == resource_name:
						result.append(resource.resourceId)
		return result


# noinspection PyMethodMayBeStatic
class OperatorUtils(Registerable, metaclass=Singleton):
	from .operators import OperatorBase
	from qrenderdoc import CaptureContext

	def __init__(self):
		super(OperatorUtils, self).__init__()
		pass

	def invoke_single_operator(self, context: CaptureContext, operator: OperatorBase):
		operator.do_prepare(context, 0)
		context.Replay().BlockInvoke(operator.do_invoke)
		if operator.exception is not None:
			msg = "Error while invoking %s:\n\n%s" % (operator.__class__.__name__, operator.exception)
			context.Extensions().MessageDialog(msg, "Debug")
		elif operator.invoked():
			operator.do_post_invoked()
		pass
