# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import renderdoc
import qrenderdoc

from typing import *


class RootParameterDescriptor(object):
	def __init__(self, reg: int, reg_space: int, flag: str, ptype: str):
		super().__init__()
		self.shader_register = reg
		self.register_space = reg_space
		self.flags = flag
		self._parameter_type = ptype
		pass

	def dumps(self):
		type_map = {
			"D3D12_ROOT_PARAMETER_TYPE_CBV": "b",
			"D3D12_ROOT_PARAMETER_TYPE_SRV": "t",
			"D3D12_ROOT_PARAMETER_TYPE_UAV": "u",
		}
		# eg. b0, space=1, flags=DATA_STATIC
		return "{0}{1}, space={2}, flags={3}".format(type_map[self._parameter_type], self.shader_register, self.register_space, self.flags.replace("D3D12_ROOT_DESCRIPTOR_FLAG_", ""))


class DescriptorRange(object):
	def __init__(self, range_type: str, num_desc: int, base_reg: int, reg_space: int, flag: str, offset: int):
		super().__init__()
		self.range_type = range_type
		self.num_descriptors = num_desc
		self.base_shader_register = base_reg
		self.register_space = reg_space
		self.flags = flag
		self.offset_in_descriptors_from_table_start = offset
		pass

	def dumps(self) -> str:
		type_map = {
			"D3D12_DESCRIPTOR_RANGE_TYPE_SRV": ("SRV", "t"),
			"D3D12_DESCRIPTOR_RANGE_TYPE_UAV": ("UAV", "u"),
			"D3D12_DESCRIPTOR_RANGE_TYPE_CBV": ("CBV", "b"),
			"D3D12_DESCRIPTOR_RANGE_TYPE_SAMPLER": ("Sampler", "s"),
		}
		# eg. CBV(b0, numDescriptors=1, space=0, offset=1, flags=DATA_STATIC_WHILE_SET_AT_EXECUTE )
		return "{0}({1}{2}, numDescriptors={3}, space={4}, offset={5}, flags={6})".format(
			type_map[self.range_type][0],
			type_map[self.range_type][1],
			self.base_shader_register,
			self.num_descriptors,
			self.register_space,
			self.offset_in_descriptors_from_table_start,
			self.flags.replace("D3D12_DESCRIPTOR_RANGE_FLAG_", "")
		)


class RootParameterDescriptorTable(object):
	def __init__(self, num_desc_table: int, desc_ranges: List[DescriptorRange]):
		super().__init__()
		self.num_descriptor_table = num_desc_table
		self.descriptor_ranges = desc_ranges
		pass

	def dumps(self) -> str:
		clauses = []
		for desc_range in self.descriptor_ranges:
			clauses.append(desc_range.dumps())
		return ", ".join(clauses)


class RootParameter(object):
	def __init__(self, ptype: str, param: RootParameterDescriptor or RootParameterDescriptorTable, vis: str):
		super().__init__()
		self.parameter_type = ptype
		self.parameter_content: RootParameterDescriptor or RootParameterDescriptorTable = param
		self.shader_visibility = vis
		pass

	def dumps(self) -> str:
		# {0}: Type; {1} Content; {2} visibility;
		fmt = "{0}({1}, visibility={2})"
		type_map = {
			"D3D12_ROOT_PARAMETER_TYPE_CBV": "CBV",
			"D3D12_ROOT_PARAMETER_TYPE_SRV": "SRV",
			"D3D12_ROOT_PARAMETER_TYPE_UAV": "UAV",
			"D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE": "DescriptorTable",
		}
		return fmt.format(type_map[self.parameter_type], self.parameter_content.dumps(), self.shader_visibility.replace("D3D12_", ""))


class StaticSampler(object):
	def __init__(
		self, sfilter: str, saddress: Tuple[str, str, str],
		mip_bias: float, max_aniso: int, cmp_func: str, border_color: str,
		min_lod: float, max_lod: float, shader_reg: int, reg_space: int,
		shader_vis: str, flags: str
	):
		super().__init__()
		self.filter = sfilter
		self.address = saddress
		self.mip_lod_bias = mip_bias
		self.max_anisotropy = max_aniso
		self.comparison_func = cmp_func
		self.border_color = border_color
		self.min_lod = min_lod
		self.max_lod = max_lod
		self.shader_register = shader_reg
		self.register_space = reg_space
		self.shader_visibility = shader_vis
		self.flags = flags
		pass

	def dumps(self):
		return "StaticSampler(s{0}, filter={1}, addressU={2}, addressV={3}, addressW={4}, mipLODBias={5}, maxAnisotropy={6}, comparisonFunc={7}, borderColor={8}, minLOD={9}, maxLOD={10}, space={11}, visibility={12})".format(
			self.shader_register,
			self.filter.replace("D3D12_", ""),
			self.address[0].replace("D3D12_", "").replace("MODE_", ""), self.address[1].replace("D3D12_", "").replace("MODE_", ""), self.address[2].replace("D3D12_", "").replace("MODE_", ""),
			self.mip_lod_bias,
			self.max_anisotropy,
			self.comparison_func.replace("D3D12_", "").replace("FUNC_", ""),
			self.border_color.replace("D3D12_", ""),
			self.min_lod,
			self.max_lod,
			self.register_space,
			self.shader_visibility.replace("D3D12_", "")
		)


class RootSignature(object):
	Name_D3D12_Create = "ID3D12Device::CreateRootSignature"
	Name_D3D12_UnpackSignature = "UnpackedSignature"

	def __init__(self, context: qrenderdoc.CaptureContext, resource: renderdoc.ResourceDescription):
		super().__init__()
		self._valid = False
		self._root_flags: str = ""
		self._root_parameters: List[RootParameter] = []
		self._static_samplers: List[StaticSampler] = []
		self._init_from_initialization_parameters_(context, resource.initialisationChunks)
		pass

	def valid(self) -> bool:
		return self._valid

	def dumps(self) -> str:
		lines: List[str] = ["\"RootFlags(%s)" % self._root_flags.replace("D3D12_ROOT_SIGNATURE_FLAG_", "")]
		for parameter in self._root_parameters:
			lines.append("\"" + parameter.dumps())
		for sampler in self._static_samplers:
			lines.append("\"" + sampler.dumps())
		return ",\"\\\n\t".join(lines) + "\""

	def dump(self, macro: str, filepath: str):
		"""
		Dump rootsignature to hlsl.
		See: https://learn.microsoft.com/en-us/windows/win32/direct3d12/specifying-root-signatures-in-hlsl
		:param macro:
		:param filepath:
		:return:
		"""
		with open(filepath, "w") as fp:
			fp.writelines([
				"// Do Not Modify This File Directly.\n",
				"// Auto Root Signature Source Generated By Unrealdoc.\n",
				"\n\n",
			])
			fp.writelines(["#define %s %s" % (macro, self.dumps()), "\n"])
		pass

	def _init_from_initialization_parameters_(self, context: qrenderdoc.CaptureContext, chunks: List[int]):
		"""
		Serialize root signature from create func.
		See: https://learn.microsoft.com/en-us/windows/win32/api/d3d12/nf-d3d12-id3d12device-createrootsignature
		:param context:
		:param chunks:
		:return:
		"""
		for idx in chunks:
			chunk = context.GetStructuredFile().chunks[idx]
			if chunk.name != self.Name_D3D12_Create:
				continue
			if chunk.NumChildren() != 6:
				continue
			# CreateRootSignature()
			#   0: int                  nodeMaks;
			#   1: void*                pBlobWithRootSignature;
			#   2: size_t               blobLengthInBytes;
			#   3: REFIID               riid;
			#   4: void*                pRootSignature;
			#   5: D3DRootSignature     UnpackedSignature;
			unpacked_signature = chunk.GetChild(5)
			# D3DRootSignature()
			#   0: D3D12_ROOT_SIGNATURE_FLAGS   Flags;
			#   1: D3D12RootSignatureParameter  Parameters[];
			#   2: D3D12_STATIC_SAMPLER_DESC1   StaticSamplers[];
			if unpacked_signature.NumChildren() != 3:
				continue

			# Fill Root Flags
			self._root_flags = unpacked_signature.GetChild(0).AsString()
			parameters = unpacked_signature.GetChild(1)

			# Fill Root Parameters
			for param_idx in range(0, parameters.NumChildren()):
				# D3D12RootSignatureParameter()
				#   0: D3D12_ROOT_PARAMETER_TYPE        ParameterType;
				#   1: D3D12_ROOT_DESCRIPTOR_TABLE1     DescriptorTable;
				#  or  D3D12_ROOT_DESCRIPTOR1           Descriptor;
				#   2: D3D12_SHADER_VISIBILITY          ShaderVisibility;
				parameter = parameters.GetChild(param_idx)
				assert (parameter.NumChildren() == 3)
				parameter_type = parameter.GetChild(0)
				shader_visibility = parameter.GetChild(2)
				if parameter_type.AsString() == "D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE":
					# D3D12_ROOT_DESCRIPTOR_TABLE1
					#   0: int                      NumDescriptorRange;
					#   1: D3D12_DESCRIPTOR_RANGE1  DescriptorRanges[];
					desc_table = parameter.GetChild(1)
					self._root_parameters.append(
						RootParameter(
							parameter_type.AsString(),
							RootParameterDescriptorTable(desc_table.GetChild(0).AsInt(), []),
							shader_visibility.AsString()
						)
					)
					# D3D12_DESCRIPTOR_RANGE1
					#   ...
					desc_ranges = desc_table.GetChild(1)
					for range_idx in range(0, desc_ranges.NumChildren()):
						desc_range = desc_ranges.GetChild(range_idx)
						self._root_parameters[-1].parameter_content.descriptor_ranges.append(
							DescriptorRange(
								desc_range.GetChild(0).AsString(),
								desc_range.GetChild(1).AsInt(),
								desc_range.GetChild(2).AsInt(),
								desc_range.GetChild(3).AsInt(),
								desc_range.GetChild(4).AsString(),
								desc_range.GetChild(5).AsInt(),
							)
						)
				elif parameter_type.AsString() in {"D3D12_ROOT_PARAMETER_TYPE_CBV", "D3D12_ROOT_PARAMETER_TYPE_SRV", "D3D12_ROOT_PARAMETER_TYPE_UAV"}:
					# D3D12_ROOT_DESCRIPTOR1
					#   ...
					desc = parameter.GetChild(1)
					self._root_parameters.append(
						RootParameter(
							parameter_type.AsString(),
							RootParameterDescriptor(
								desc.GetChild(0).AsInt(),
								desc.GetChild(1).AsInt(),
								desc.GetChild(2).AsString(),
								parameter_type.AsString()
							),
							shader_visibility.AsString()
						)
					)
				else:
					raise TypeError("Unsupported parameter type: %s" % parameter.GetChild(0).AsString())

			# Fill Static Samplers
			static_samplers = unpacked_signature.GetChild(2)
			for sampler_idx in range(0, static_samplers.NumChildren()):
				static_sampler = static_samplers.GetChild(sampler_idx)
				self._static_samplers.append(
					StaticSampler(
						static_sampler.GetChild(0).AsString(),
						(static_sampler.GetChild(1).AsString(), static_sampler.GetChild(2).AsString(), static_sampler.GetChild(3).AsString()),
						static_sampler.GetChild(4).AsFloat(),
						static_sampler.GetChild(5).AsInt(),
						static_sampler.GetChild(6).AsString(),
						static_sampler.GetChild(7).AsString(),
						static_sampler.GetChild(8).AsFloat(),
						static_sampler.GetChild(9).AsFloat(),
						static_sampler.GetChild(10).AsInt(),
						static_sampler.GetChild(11).AsInt(),
						static_sampler.GetChild(12).AsString(),
						static_sampler.GetChild(13).AsString(),
					)
				)
		pass
