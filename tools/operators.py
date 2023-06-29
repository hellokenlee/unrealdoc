# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import struct
import traceback

from enum import Enum
from typing import Callable
from qrenderdoc import CaptureContext
from renderdoc import ReplayController, ResourceId, BoundVBuffer, ShaderStage, BoundCBuffer, ShaderReflection, ShaderConstantType, VarType

from .utils import PipelineStateUtils


class DynamicDataFormat(object):

	DataFormatMap = {
		VarType.UInt: "I",
		VarType.Float: "f",
		VarType.SInt: "i",
	}

	def __init__(self, fmt: str):
		assert(struct.calcsize(fmt) > 0)
		self._fmt = fmt
		pass

	@property
	def value(self):
		return self._fmt


class DataFormat(Enum):

	NONE = ""
	UINT = "I"
	UINT3 = "III"
	UINT4 = "IIII"
	FLOAT = "f"
	FLOAT3 = "fff"
	FLOAT4 = "ffff"
	UINT3_FLOAT1 = "IIIf"

	@classmethod
	def _missing_(cls, vartype: ShaderConstantType or str):
		# Userdefined data format
		if isinstance(vartype, str):
			return DynamicDataFormat(vartype)
		# Renderdoc shader constant data format
		elif isinstance(vartype, ShaderConstantType):
			num = vartype.columns * vartype.rows
			fmt = DynamicDataFormat.DataFormatMap[vartype.baseType] * num
			return DynamicDataFormat(fmt)
		else:
			raise ValueError()
		pass


class OperatorBase(object):

	PostInvokedCallback = Callable[[object], None]

	def __init__(self, post_invoke: PostInvokedCallback):
		super(OperatorBase, self).__init__()
		self.exception = None
		self._invoked = False
		self._prepared = False
		self._result: any = None
		self._post_invoke = post_invoke
		pass

	def reset(self):
		self._invoked = False
		self._prepared = False
		self._result = None
		self.exception = None
		pass

	def prepare(self, context: CaptureContext, event: int) -> bool:
		"""
		Do initialize for operator via. pipeline state or ect. and return if the operator is prepared.
		"""
		return True

	def invoke(self, controller: ReplayController) -> any:
		"""
		Do the operations to replay controller ( in another thread ), return the result latter might be get in UI.

		ONLY prepared operator got invoked, unprepared operator got ignored.
		"""
		raise NotImplemented

	def result(self):
		return self._result

	def invoked(self):
		return self._invoked

	def prepared(self):
		return self._prepared

	def do_prepare(self, context: CaptureContext, event: int):
		self._prepared = self.prepare(context, event)
		pass

	# noinspection PyBroadException
	def do_invoke(self, controller: ReplayController):
		if self._prepared is True:
			self._invoked = True
			try:
				self._result = self.invoke(controller)
				self.exception = None
			except Exception as _e:
				self.exception = traceback.format_exc()
		pass

	def do_post_invoked(self):
		if self._post_invoke is not None:
			self._post_invoke(self)
		pass


class OperatorBuffer(OperatorBase):

	def __init__(self, post_invoke: OperatorBase.PostInvokedCallback, fmt: DataFormat or DynamicDataFormat):
		super(OperatorBuffer, self).__init__(post_invoke)
		self.fmt = fmt
		self.index = 0
		self.resource_id = ResourceId.Null()
		self.resource_offset = 0
		self.keep_raw_buffer = False
		self._raw_buffer_data = None
		pass

	def reset(self):
		super(OperatorBuffer, self).reset()
		self.index = 0
		self.resource_id = ResourceId.Null()
		self.resource_offset = 0
		pass

	def raw_buffer(self):
		assert(self.keep_raw_buffer is True)
		return self._raw_buffer_data

	def prepare(self, context: CaptureContext, event: int) -> bool:
		if self.index < 0:
			return False
		return True

	def byte_offset(self):
		return struct.calcsize(self.fmt.value) * self.index

	def invoke(self, controller: ReplayController):
		# TODO: Do we really need to get all buffer data?
		raw_buffer_data = controller.GetBufferData(self.resource_id, self.resource_offset, 0)
		if self.keep_raw_buffer:
			self._raw_buffer_data = raw_buffer_data
		return struct.unpack_from(self.fmt.value, raw_buffer_data, self.byte_offset())


class OperatorMeshVsInput(OperatorBuffer):

	def __init__(self, post_invoke: OperatorBase.PostInvokedCallback, fmt: DataFormat, sematic: str, vtx: int):
		super(OperatorMeshVsInput, self).__init__(post_invoke, fmt)
		self.offset = vtx
		self.sematic = sematic
		pass

	def prepare(self, context: CaptureContext, event: int):
		if not super(OperatorMeshVsInput, self).prepare(context, event):
			return False
		state = context.CurPipelineState()
		if state is not None:
			attribs = state.GetVertexInputs()
			vbuffers = state.GetVBuffers()
			for attrib in attribs:
				if attrib.name == self.sematic:
					vbuffer: BoundVBuffer = vbuffers[attrib.vertexBuffer]
					self.resource_id = vbuffer.resourceId
					self.resource_offset = vbuffer.byteOffset
					return True
		return False


class OperatorResourceStructuredBuffer(OperatorBuffer):

	def __init__(self, post_invoke: OperatorBase.PostInvokedCallback, fmt: DataFormat, stage: ShaderStage, name: str):
		super(OperatorResourceStructuredBuffer, self).__init__(post_invoke, fmt)
		self._stage = stage
		self._resource_name = name
		pass

	def prepare(self, context: CaptureContext, event: int) -> bool:
		if not super(OperatorResourceStructuredBuffer, self).prepare(context, event):
			return False
		state = context.CurPipelineState()
		valid_buffer_id = []
		# Find in readonly resource
		valid_buffer_id.extend(PipelineStateUtils().find_readonly_resource(state, self._resource_name, self._stage))
		# Find in readwrite resource
		valid_buffer_id.extend(PipelineStateUtils().find_readwrite_resource(state, self._resource_name, self._stage))
		#
		if len(valid_buffer_id) == 1:
			self.resource_id = valid_buffer_id[0]
			return True
		return False


class OperatorResourceConstantBuffer(OperatorBuffer):

	def __init__(self, post_invoke: OperatorBase.PostInvokedCallback, stage: ShaderStage, buffer_name: str, uniform_name: str):
		super(OperatorResourceConstantBuffer, self).__init__(post_invoke, DataFormat.NONE)
		self._stage = stage
		self._byte_offset = 0
		self._buffer_name = buffer_name
		self._uniform_name = uniform_name
		pass

	def prepare(self, context: CaptureContext, event: int) -> bool:
		#
		if not super(OperatorResourceConstantBuffer, self).prepare(context, event):
			return False
		#
		state = context.CurPipelineState()
		shader = state.GetShaderReflection(self._stage)
		if shader is None:
			return False
		for slot in range(len(shader.constantBlocks)):
			block = shader.constantBlocks[slot]
			if block.name == self._buffer_name:
				buffer = state.GetConstantBuffer(self._stage, slot, 0)
				if context.GetResource(buffer.resourceId) is not None:
					for var in block.variables:
						if var.name == self._uniform_name:
							self.fmt = DataFormat(var.type)
							self.resource_id = buffer.resourceId
							self.resource_offset = buffer.byteOffset
							self._byte_offset = var.byteOffset
							return True
		return False

	def byte_offset(self):
		return self._byte_offset


class OperatorMeshVsOutput(OperatorBase):
	pass


class OperatorMeshGsOutput(OperatorBase):
	pass


class OperatorResourceTexture(OperatorBase):
	pass
