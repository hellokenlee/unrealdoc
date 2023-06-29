# -*- coding:UTF-8 -*-

import pickle
import os.path
import shutil
import subprocess
from typing import Callable, Optional
from .common.event_tree import EventsTree
from ..operators import OperatorBase
from ..utils import OperatorUtils
from renderdoc import ReplayController, ActionFlags, GPUCounter, CounterUnit, ActionDescription
from qrenderdoc import CaptureContext, MiniQtHelper


class OperatorCollectEventTree(OperatorBase):

	def __init__(self, root_pass_name: str, output_dirpath: str):
		super(OperatorCollectEventTree, self).__init__(None)
		self.root_pass_name = root_pass_name
		self.output_dirpath = output_dirpath
		self._result: Optional[EventsTree] = None
		pass

	def invoke(self, controller: ReplayController):
		self._result = EventsTree(self.root_pass_name, self.output_dirpath, controller)
		self._result.reset()
		self._result.root_frame = controller.GetRootActions()
		#
		if self.root_pass_name == "":
			pass_list = self._result.root_frame
		else:
			entry = None
			for item in self._result.root_frame:
				entry = self.find_events_tree_entry(item)
				if entry is not None:
					break
			if entry is None:
				raise ValueError("[Error] ROOT_FRAME: '%s' do not exist!Please ensure!\n" % self.root_pass_name)
			pass_list = entry.children
		#
		self._result.add_pass(None)
		#
		for item in pass_list:
			if len(item.children) > 1:
				self._result.add_pass(item)
			elif item.flags and ActionFlags.Drawcall:
				self._result.passes[0].add_draw(item)
		#
		self.collect_frame_resources(controller)
		#
		self.calculate_passes_attributes()
		#
		self._result.controller = None
		#

		def recusive_clear_draw(node):
			for child in node.childs:
				child.current = None
				recusive_clear_draw(child)
			pass

		for apass in self._result.passes:
			recusive_clear_draw(apass)

		for draw in self._result.draw_call_dict.values():
			draw.draw = None

		return self._result

	def find_events_tree_entry(self, root):
		# Structure of renderDoc actions:
		# Frame XXXX
		#     FRAME
		#         WorldTick
		#         SendAllEndOfFrameUpdates
		#         Scene
		#             PrePass
		#             BasePass
		#             ......
		#         SlateUI Title = Marvel(......)
		#         Present
		name = root.GetName(self._result.controller.GetStructuredFile())
		if str(name) == self.root_pass_name:
			return root
		for child in root.children:
			entry = self.find_events_tree_entry(child)
			if entry:
				return entry
		pass

	# Handle resources and collect drawcall information
	def collect_frame_resources(self, controller):
		textures = controller.GetTextures()
		for tex in textures:
			self._result.textures_dict[tex.resourceId] = tex
		resources = self._result.controller.GetResources()
		for res in resources:
			self._result.resources_dict[res.resourceId] = res
		pass

	def calculate_passes_attributes(self):
		# get counter result
		results_duration = self._result.controller.FetchCounters([GPUCounter.EventGPUDuration])
		gpu_duration_desc = self._result.controller.DescribeCounter(GPUCounter.EventGPUDuration)
		gpu_duration_desc.Counter = CounterUnit.Seconds
		for result_d in results_duration:
			for single_pass in self._result.passes:
				if result_d.eventId in single_pass.childsId:
					# change second(s) to microsecond(us)
					val = result_d.value.d * 1000000
					self._result.time += single_pass.calculate_time_overhead(result_d.eventId, val)

		result_invocation = self._result.controller.FetchCounters([GPUCounter.PSInvocations])
		ps_invocation_desc = self._result.controller.DescribeCounter(GPUCounter.PSInvocations)
		for result_i in result_invocation:
			for single_pass in self._result.passes:
				if result_i.eventId in single_pass.childsId:
					self._result.ps_invocation += single_pass.calculate_invocation(result_i, ps_invocation_desc)

		result_invocation = self._result.controller.FetchCounters([GPUCounter.VSInvocations])
		vs_invocation_desc = self._result.controller.DescribeCounter(GPUCounter.VSInvocations)
		for result_i in result_invocation:
			for single_pass in self._result.passes:
				if result_i.eventId in single_pass.childsId:
					self._result.vs_invocation += single_pass.calculate_invocation(result_i, vs_invocation_desc, True)

		# Calculate other attributes of passes
		for single_pass in self._result.passes:
			self._result.triangles_num += single_pass.calculate_triangles_number()
			self._result.draw_call += single_pass.calculate_drawcall()
			# get resolution of each pass
			if single_pass.first_draw_id > 0:
				self._result.controller.SetFrameEvent(single_pass.first_draw_id, False)
				state = self._result.controller.GetPipelineState()
				targets = state.GetOutputTargets()
				if len(targets) > 0:
					target_id = targets[0].resourceId
				else:
					depth_target = state.GetDepthTarget()
					target_id = depth_target.resourceId
				if target_id in self._result.textures_dict.keys():
					single_pass.resolution_width = self._result.textures_dict[target_id].width
					single_pass.resolution_height = self._result.textures_dict[target_id].height
					single_pass.resolution_depth = self._result.textures_dict[target_id].depth
		pass


def collect_pass_analysis(root_pass: str, context: CaptureContext):
	#
	rdc_filepath = os.path.abspath(context.GetCaptureFilename())
	assert(rdc_filepath.endswith(".rdc"))
	output_dirpath = rdc_filepath[:-4] + "_Report"
	if os.path.exists(output_dirpath):
		shutil.rmtree(output_dirpath, True)
	#
	operator = OperatorCollectEventTree(root_pass, output_dirpath)
	OperatorUtils().invoke_single_operator(context, operator)
	#
	if operator.result() is not None:
		os.mkdir(output_dirpath)
		with open(os.path.join(output_dirpath, "EventTree.bin"), "wb") as fp:
			pickle.dump(operator.result(), fp)
		# Call local python environment
		script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "common/pyechart_tree_renderer.py")
		cmd = ["py", "-3", script, output_dirpath]
		subprocess.call(cmd)
	pass


if __name__ == "__main__":
	assert('pyrenderdoc' in globals())
	collect_pass_analysis("Scene", globals()["pyrenderdoc"])
	pass
