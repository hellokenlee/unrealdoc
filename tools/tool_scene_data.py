# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

from .utils import Utils, PipelineStateUtils
from .tool_base import ToolBase
from .operators import DataFormat, OperatorBase, OperatorMeshVsInput, OperatorResourceStructuredBuffer, OperatorResourceConstantBuffer
from .struct_buffer_viewer_mgr import StructBufferViewerManager

from renderdoc import ShaderStage, ResourceId

PRIMITIVE_ID_NUM_BITS = 20                  # Max of 1,048,576 primitives
INSTANCE_SCENE_DATA_FLAGS_NUM_BITS = 12     # Max of 12 flags
PRIMITIVE_SCENE_DATA_STRIDE = 80            # Stride of a single primitive's data in float4's, must match C++
VF_TREAT_INSTANCE_ID_OFFSET_AS_PRIMITIVE_ID_FLAG = 1 << 31
MARVEL_NUM_CUSTOM_PRIMITIVE_DATA = 47


def bit_field_extract_u32(data, size, offset):
	size &= 31
	offset &= 31
	return (data >> offset) & ((1 << size) - 1)


def unpack_primitive_id_and_flags(packed_primitive_id_and_flags: int) -> (int, int):
	primitive_id = bit_field_extract_u32(packed_primitive_id_and_flags, PRIMITIVE_ID_NUM_BITS, 0)
	instance_flags = bit_field_extract_u32(packed_primitive_id_and_flags, INSTANCE_SCENE_DATA_FLAGS_NUM_BITS, PRIMITIVE_ID_NUM_BITS)
	return primitive_id, instance_flags


class ToolSceneData(ToolBase):

	InstanceSceneDataSOA0Format = "IIIf"

	PrimitiveDataFormat = "%df" % (4 * PRIMITIVE_SCENE_DATA_STRIDE)

	Idx_LocalToWorldFloat4x4 = 10

	def __init__(self, *args):
		super(ToolSceneData, self).__init__(*args)
		self.set_title("Scene Data")
		self.instance_id_offset = self.add_input("InstanceIdOffset", "-1", True)
		self.draw_instance_id = self.add_input("DrawInstanceId", "0", False, self._draw_instance_id_formatter)
		self.instance_id = self.add_result("InstanceId", "-1")
		self.primitive_id = self.add_result("PrimitiveId", "-1")
		self.instance_flags = self.add_result("InstanceFlags", "0b0000")
		self.location = self.add_result("Location", "(0, 0, 0)")
		self.instance_scene_data_soa_stride = self.add_result("InstanceSceneDataSOAStride", "0")
		self.view_instance_data_btn = self.add_custom_button("View Instance Data", self.on_view_instance_data)
		self.view_primitive_data_btn = self.add_custom_button("View Primitive Data", self.on_view_primitive_data)
		#
		self._primitive_id_workaround = False
		#
		self.op_instance_id_offset = OperatorMeshVsInput(self._post_op_instance_id_offset_invoked, DataFormat.UINT, "ATTRIBUTE13", 0)
		self.op_instance_id = OperatorResourceStructuredBuffer(self._post_op_instance_id_invoked, DataFormat.UINT, ShaderStage.Vertex, "InstanceCulling.InstanceIdsBuffer")
		self.op_instance_scene_data = OperatorResourceStructuredBuffer(self._post_op_instance_scene_data_invoked, DataFormat(self.InstanceSceneDataSOA0Format), ShaderStage.Vertex, "GPUScene.InstanceSceneData")
		self.op_primitive_data = OperatorResourceStructuredBuffer(self._post_op_primitive_data_invoked, DataFormat(self.PrimitiveDataFormat), ShaderStage.Vertex, "GPUScene.PrimitiveData")
		self.op_view_constant_data = OperatorResourceConstantBuffer(self._post_op_view_constant_data_invoked, ShaderStage.Vertex, "View", "View_InstanceSceneDataSOAStride")
		self.op_global_constant_data = OperatorResourceConstantBuffer(self._post_op_view_constant_data_invoked, ShaderStage.Compute, "_RootShaderParameters", "GPUSceneInstanceSceneDataSOAStride")
		self.op_view_constant_data.keep_raw_buffer = True
		self.op_global_constant_data.keep_raw_buffer = True
		#
		StructBufferViewerManager().get_primitive_scene_data_viewer().format_hlsl.define("NUM_CUSTOM_PRIMITIVE_DATA", str(MARVEL_NUM_CUSTOM_PRIMITIVE_DATA))
		pass

	def update(self):
		# Reset widgets
		self.instance_id_offset.reset()
		self.instance_id.reset()
		self.primitive_id.reset()
		self.instance_flags.reset()
		self.location.reset()
		#
		instance_data_buffers = PipelineStateUtils().find_resource(self.context.CurPipelineState(), "GPUScene.InstanceSceneData")
		if len(instance_data_buffers) > 0:
			self.view_instance_data_btn.set_enabled(True)
			StructBufferViewerManager().get_instance_scene_data_viewer().buffer_id = instance_data_buffers[0]
		else:
			self.view_instance_data_btn.set_enabled(False)
			StructBufferViewerManager().get_instance_scene_data_viewer().buffer_id = ResourceId.Null()
		#
		primitive_data_buffers = PipelineStateUtils().find_resource(self.context.CurPipelineState(), "GPUScene.PrimitiveData")
		if len(primitive_data_buffers) > 0:
			self.view_primitive_data_btn.set_enabled(True)
			StructBufferViewerManager().get_primitive_scene_data_viewer().buffer_id = primitive_data_buffers[0]
		else:
			self.view_primitive_data_btn.set_enabled(False)
			StructBufferViewerManager().get_primitive_scene_data_viewer().buffer_id = ResourceId.Null()
		pass

	def operate(self):
		self._primitive_id_workaround = False
		operators = [self.op_instance_id_offset, self.op_instance_id, self.op_instance_scene_data, self.op_primitive_data, self.op_view_constant_data]
		if Utils().action_in_pass(self.context.CurAction(), "ShadowDepthPass"):
			self.op_instance_id_offset.sematic = "ATTRIBUTE1"
			return operators
		elif Utils().action_in_pass(self.context.CurAction(), "DepthPass"):
			self.op_instance_id_offset.sematic = "ATTRIBUTE1"
			return operators
		elif Utils().action_in_pass(self.context.CurAction(), "BasePass"):
			self.op_instance_id_offset.sematic = "ATTRIBUTE13"
			return operators
		elif Utils().action_in_pass(self.context.CurAction(), "CompositeEditorPrimitives"):
			self.op_instance_id_offset.sematic = "ATTRIBUTE13"
			self._primitive_id_workaround = True
			return [self.op_instance_id_offset, self.op_primitive_data, self.op_view_constant_data]
		elif Utils().action_in_pass(self.context.CurAction(), "GPUScene.Update") or Utils().action_in_pass(self.context.CurAction(), "GPUScene.UploadDynamicPrimitiveShaderDataForView") or Utils().action_in_pass(self.context.CurAction(), "BuildRenderingCommandsDeferred"):
			return [self.op_global_constant_data]
		return []

	def on_view_instance_data(self, _c, _w, _t):
		StructBufferViewerManager().get_instance_scene_data_viewer().view()
		StructBufferViewerManager().get_instance_scene_data_viewer().scroll_to(int(self.instance_id.get_value()), 0)
		pass

	def on_view_primitive_data(self, _c, _w, _t):
		StructBufferViewerManager().get_primitive_scene_data_viewer().view()
		StructBufferViewerManager().get_primitive_scene_data_viewer().scroll_to(int(self.primitive_id.get_value()), 0)
		pass

	def _draw_instance_id_formatter(self, text: str):
		action = self.context.CurAction()
		if action is None:
			return "0"
		max_draw_instance_id = max(action.numInstances - 1, 0)
		try:
			draw_inextance_id = int(text)
		except ValueError:
			draw_inextance_id = 0
		draw_inextance_id = min(draw_inextance_id, max_draw_instance_id)
		return str(draw_inextance_id)

	def _post_op_instance_id_offset_invoked(self, operator: OperatorBase):
		# refs: SceneData.ush::GetSceneDataIntermediates(uint InstanceIdOffset, uint DrawInstanceId)
		assert(len(operator.result()) == 1)
		instance_id_offset = operator.result()[0]
		self.instance_id_offset.set_value(str(instance_id_offset))
		# refs: GPUCULL_TODO:
		if self._primitive_id_workaround:
			assert(instance_id_offset & VF_TREAT_INSTANCE_ID_OFFSET_AS_PRIMITIVE_ID_FLAG != 0)
			primitive_id = instance_id_offset & (VF_TREAT_INSTANCE_ID_OFFSET_AS_PRIMITIVE_ID_FLAG - 1)
			self.op_primitive_data.index = primitive_id
			self.primitive_id.set_value(str(primitive_id))
		else:
			self.op_instance_id.index = instance_id_offset + int(self.draw_instance_id.get_value())
		pass

	def _post_op_instance_id_invoked(self, operator: OperatorBase):
		assert(len(operator.result()) == 1)
		instance_id_raw = operator.result()[0]
		instance_id = instance_id_raw & ((1 << 28) - 1)
		self.instance_id.set_value(str(instance_id))
		#
		self.op_instance_scene_data.index = int(self.instance_id.get_value())
		pass

	def _post_op_instance_scene_data_invoked(self, operator: OperatorResourceStructuredBuffer):
		# refs: SceneData.ush::LoadInstancePrimitiveIdAndFlags(...)
		assert(len(operator.result()) == 4)
		packed_primitive_id_and_flags = operator.result()[0]
		primitive_id, instance_flags = unpack_primitive_id_and_flags(packed_primitive_id_and_flags)
		self.primitive_id.set_value(str(primitive_id))
		self.instance_flags.set_value(bin(instance_flags))
		#
		self.op_primitive_data.index = primitive_id
		pass

	def _post_op_primitive_data_invoked(self, operator: OperatorResourceStructuredBuffer):
		assert(len(operator.result()) == 4 * PRIMITIVE_SCENE_DATA_STRIDE)
		# Matrix4x4
		local_to_world = [
			operator.result()[(self.Idx_LocalToWorldFloat4x4 + 0) * 4: (self.Idx_LocalToWorldFloat4x4 + 1) * 4],
			operator.result()[(self.Idx_LocalToWorldFloat4x4 + 1) * 4: (self.Idx_LocalToWorldFloat4x4 + 2) * 4],
			operator.result()[(self.Idx_LocalToWorldFloat4x4 + 2) * 4: (self.Idx_LocalToWorldFloat4x4 + 3) * 4],
			operator.result()[(self.Idx_LocalToWorldFloat4x4 + 3) * 4: (self.Idx_LocalToWorldFloat4x4 + 4) * 4],
		]
		location = [local_to_world[3][0], local_to_world[3][1], local_to_world[3][2]]
		self.location.set_value(str(tuple(location)))
		pass

	def _post_op_view_constant_data_invoked(self, operator: OperatorResourceConstantBuffer):
		assert(len(operator.result()) == 1)
		soa_stride = int(operator.result()[0])
		self.instance_scene_data_soa_stride.set_value(str(soa_stride))
		StructBufferViewerManager().get_instance_scene_data_viewer().format_hlsl.define("View_InstanceSceneDataSOAStride", str(soa_stride))
		pass
