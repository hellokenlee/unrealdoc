# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import re
import renderdoc
import qrenderdoc


class GraphicPipelineStateObject(object):

	def __init__(self, context: qrenderdoc.CaptureContext, state: renderdoc.PipeState):
		super().__init__()
		self._schema_version = "1.0"
		self._num_input_layout_elements = 0
		self._input_layout = ""
		self._primitive_topology = "D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE"
		self._num_render_targets = 0
		self._render_target_formats = ""
		self.reset(context, state)
		pass

	def reset(self, context: qrenderdoc.CaptureContext, state: renderdoc.PipeState):
		# TODO: Verify these
		primitive_typology_map = {
			renderdoc.Topology.LineList: "D3D12_PRIMITIVE_TOPOLOGY_TYPE_LINE_LIST",
			renderdoc.Topology.LineList_Adj: "D3D12_PRIMITIVE_TOPOLOGY_LINE_LIST",
			renderdoc.Topology.LineLoop: "D3D12_PRIMITIVE_TOPOLOGY_LINE_LOOP",
			renderdoc.Topology.LineStrip: "D3D12_PRIMITIVE_TOPOLOGY_LINE_STRIP",
			renderdoc.Topology.LineStrip_Adj: "D3D12_PRIMITIVE_TOPOLOGY_LINE_STRIP",
			renderdoc.Topology.PointList: "D3D12_PRIMITIVE_TOPOLOGY_TYPE_POINT_LIST",
			renderdoc.Topology.TriangleFan: "D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE_FAN",
			renderdoc.Topology.TriangleList: "D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE",
			renderdoc.Topology.TriangleList_Adj: "D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE",
			renderdoc.Topology.TriangleStrip: "D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE_STRIP",
			renderdoc.Topology.TriangleStrip_Adj: "D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE_STRIP",
		}

		input_layout = state.GetVertexInputs()
		self._num_input_layout_elements = len(input_layout)
		self._input_layout = ""
		layouts_list = []
		for slot, layout in enumerate(input_layout):
			layouts_list.append(self._input_layout_dumps(slot, layout))
		self._input_layout = ",\n".join(layouts_list)
		self._primitive_topology = primitive_typology_map[state.GetPrimitiveTopology()]
		views = context.CurD3D12PipelineState().outputMerger.renderTargets
		self._num_render_targets = len(views)
		formats_list = []
		for view in views:
			formats_list.append("DXGI_FORMAT_%s" % view.viewFormat.Name())
		self._render_target_formats = "{ " + ", ".join(formats_list) + " }"
		pass

	@staticmethod
	def _input_layout_dumps(slot: int, layout: renderdoc.VertexInputAttribute) -> str:
		# {SemanticName, SemanticIndex, Format, InputSlot, AlignedByteOffset, InputSlotClass, InstanceDataStepRate}
		partten = re.compile('([A-Z]+)(\\d+)')
		semantic_name = partten.match(layout.name).group(1)
		semantic_index = partten.match(layout.name).group(2)
		slot_class = "D3D12_INPUT_CLASSIFICATION_PER_INSTANCE_DATA" if layout.perInstance else "D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA"
		content = "\"{0}\", {1}, {2}, {3}, {4}, {5}, {6}".format(
			semantic_name,
			semantic_index,
			"DXGI_FORMAT_%s" % layout.format.Name(),
			slot,
			layout.byteOffset,
			slot_class,
			layout.instanceRate,
		)
		return "{ %s }" % content

	def dumps(self) -> str:
		return \
			"# schemaVersion\n" \
			"{0}\n\n" \
			"# InputLayoutNumElements (the number of D3D12_INPUT_ELEMENT_DESC elements in the D3D12_INPUT_LAYOUT_DESC structure - must match the following \"InputLayout\" section)\n" \
			"{1}\n\n" \
			"# InputLayout ( {{SemanticName, SemanticIndex, Format, InputSlot, AlignedByteOffset, InputSlotClass, InstanceDataStepRate }} )\n" \
			"{2}\n\n" \
			"#PrimitiveTopologyType (the D3D12_PRIMITIVE_TOPOLOGY_TYPE value to be used when creating the PSO)\n" \
			"{3}\n\n" \
			"# NumRenderTargets (the number of formats in the upcoming RTVFormats section)\n" \
			"{4}\n\n" \
			"# RTVFormats (an array of DXGI_FORMAT-typed values for the render target formats - the number of items in the array should match the above NumRenderTargets section)\n" \
			"{5}\n".format(
				self._schema_version,
				self._num_input_layout_elements,
				str(self._input_layout),
				self._primitive_topology,
				self._num_render_targets,
				str(self._render_target_formats),
			)
		pass

	def dump(self, filepath: str):
		"""
		:param filepath:
		:return:
		"""
		with open(filepath, "w") as fp:
			fp.write(self.dumps())
		pass
