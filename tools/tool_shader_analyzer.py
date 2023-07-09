# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

import os.path
import tempfile
import subprocess
import renderdoc

from typing import *
from enum import Enum
from .utils import Utils
from .tool_base import ToolBase
from .utils import PipelineStateUtils

from .shaderanalyzer.rootsignature import RootSignature
from .shaderanalyzer.graphic_pipeline_state import GraphicPipelineStateObject


class ShaderStageName(Enum):
	Vertex = "vs"
	Pixel = "ps"
	Compute = "cs"
	pass


class ShaderModel(Enum):
	SM_5_0 = "5_0"
	SM_5_1 = "5_1"
	SM_6_0 = "6_0"
	SM_6_1 = "6_1"
	SM_6_2 = "6_2"
	SM_6_3 = "6_3"
	SM_6_4 = "6_4"
	SM_6_5 = "6_5"
	SM_6_6 = "6_6"


class RGAMode(Enum):
	IsaDissambly = "ISA Dissambly"
	LiveRegister = "Live Register"


class ToolShaderAnalyzer(ToolBase):
	ROOT_SIGNATURE_MACRO = "UnrealdocAutoGen"
	ROOT_SIGNATURE_FILENAME = "UnrealdocRootSignature.rs.hlsl"
	GPSO_FILENAME = "Unrealdoc.gpso"

	RGA_PATH = "RadeonGpuAnalyzerExePath"

	shader_stage_map = {
		ShaderStageName.Compute.value: renderdoc.ShaderStage.Compute,
		ShaderStageName.Vertex.value: renderdoc.ShaderStage.Vertex,
		ShaderStageName.Pixel.value: renderdoc.ShaderStage.Pixel,
	}

	def __init__(self, *args):
		super(ToolShaderAnalyzer, self).__init__(*args)
		#
		self._temp_dir = tempfile.gettempdir()
		# Debug Temp Path
		# self._temp_dir = "C:\\Users\\gzlixiaoliang\\Desktop\\ShaderPlay\\"
		#
		self.add_config(self.RGA_PATH, os.path.join(self.plugin_dir_path, "_bin_", "rga", "rga.exe"))
		#
		self.set_title("Shader Analyzer")
		self._mode = self.add_combo_box("Mode", [e.value for e in RGAMode])
		self._asic = self.add_combo_box("ASIC", self._init_rpa_attributes_())
		self._shader_stage = self.add_combo_box("Stage", [e.value for e in ShaderStageName], self.on_change_shader_stage)
		self._shader_model = self.add_combo_box("Model", [e.value for e in ShaderModel])
		self._shader_entry = self.add_input("Entry", "")
		self._compiler_args = self.add_input("DXC Args", "")
		self.show_eveluate_button(True)
		pass

	def eveluate(self):
		#
		dxcarg_fileptah = self._write_temp_dxc_arg()
		source_filepath = self._write_temp_hlsl_source(self._shader_stage.get_value())
		rootsig_filepath = self._write_temp_root_sig_source()
		#
		out_isa_filepath = os.path.join(self._temp_dir, "isa.txt")
		out_livereg_filepath = os.path.join(self._temp_dir, "livereg.txt")
		if self._mode.get_value() == RGAMode.IsaDissambly.value:
			mode_arg = "--isa %s" % out_isa_filepath
			open_filepath = self._get_actual_output_filepath(RGAMode.IsaDissambly, "isa.txt")
		elif self._mode.get_value() == RGAMode.LiveRegister.value:
			mode_arg = "--isa %s --livereg %s" % (out_isa_filepath, out_livereg_filepath)
			open_filepath = self._get_actual_output_filepath(RGAMode.LiveRegister, "livereg.txt")
		else:
			print("[Error] Unknown run mode.")
			return
		#
		if self.get_config(self.RGA_PATH) and os.path.exists(self.get_config(self.RGA_PATH)):
			if self._shader_model and self._shader_stage and self._shader_entry:
				#
				rhi_arg = "-s dx12 --offline"
				#
				asic_arg = "-c %s" % self._asic.get_value().split(" ")[0]
				# --cs {source} --cs-entry {entry} --cs-model cs_6_6
				source_arg = "--{0} {1} --{0}-entry {2} --{0}-model {0}_{3}".format(
					self._shader_stage.get_value(),
					source_filepath,
					self._shader_entry.get_value(),
					self._shader_model.get_value()
				)
				#
				dxc_arg = "--dxc-opt-file %s" % dxcarg_fileptah
				#
				rootsig_arg = "--rs-macro %s --rs-macro-version rootsig_1_1 --rs-hlsl %s" % (self.ROOT_SIGNATURE_MACRO, rootsig_filepath)
				# Additional Parameter For Graphics Pipeline
				is_vertex_stage = ShaderStageName.Vertex.value == self._shader_stage.get_value()
				is_pixel_stage = ShaderStageName.Pixel.value == self._shader_stage.get_value()
				is_graphics_pipeline = is_pixel_stage or is_vertex_stage
				gpso_arg = ""
				if is_graphics_pipeline:
					gpso_filepath = self._write_temp_gpso_source()
					gpso_arg = "--gpso %s" % gpso_filepath
				opt_source_arg = ""
				if is_pixel_stage:
					# We need to dump vertex shader when we are analysising pixel shader
					opt_source_filepath = self._write_temp_hlsl_source("vs")
					opt_source_arg = "--vs {0} --vs-entry {1} --vs-model vs_{2}".format(
						opt_source_filepath,
						self._get_shader_entry("vs"),
						self._shader_model.get_value()
					)
				#
				command = [
					self.get_config(self.RGA_PATH),
					rhi_arg,
					asic_arg,
					source_arg,
					opt_source_arg,
					dxc_arg,
					rootsig_arg,
					gpso_arg,
					mode_arg,
				]
				print("RGA Run: %s" % " ".join(command))
				result = subprocess.run(" ".join(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, shell=True)
				print(result.stdout.decode())
				print(open_filepath)
				if os.path.exists(open_filepath):
					Utils().startfile(open_filepath)
				else:
					self.message(result.stdout.decode())
			else:
				print("[Error] Unknown args.")
		else:
			self.message(
				"Unable to find RGA in: \n"
				"%s\n"
				"Please download from: \n"
				"https://github.com/GPUOpen-Tools/radeon_gpu_analyzer/release\n\n"
				"Then config via. [Tools]-[Settings]-[Unrealdoc]" % self.get_config(self.RGA_PATH),
				"Error")
		pass

	def update(self):
		state = self.context.CurPipelineState()
		action = self.context.CurAction()
		if action is not None:
			# Compute
			if action.flags & renderdoc.ActionFlags.Dispatch:
				if state.GetShaderReflection(renderdoc.ShaderStage.Compute):
					self._shader_stage.set_value(ShaderStageName.Compute.value)
			# Draw
			elif action.flags & renderdoc.ActionFlags.Drawcall:
				if state.GetShaderReflection(renderdoc.ShaderStage.Vertex):
					self._shader_stage.set_value(ShaderStageName.Vertex.value)
		self._refresh_shader_infos()
		pass

	def save_layout(self, pdict: dict):
		self.save_item(pdict, self._mode)
		self.save_item(pdict, self._asic)
		pass

	def load_layout(self, pdict: dict):
		self.load_item(pdict, self._mode, "")
		self.load_item(pdict, self._asic, "")
		pass

	def on_change_shader_stage(self, _context, _widget, _text):
		self._refresh_shader_infos()
		pass

	@classmethod
	def _init_rpa_attributes_(cls) -> List[str]:
		asics = [""]
		if cls.get_config(cls.RGA_PATH) and os.path.exists(cls.get_config(cls.RGA_PATH)):
			command = [cls.get_config(cls.RGA_PATH), "-s dx12", "-l"]
			print("Listing all asic: %s", " ".join(command))
			result = subprocess.run(" ".join(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, shell=True)
			lines = result.stdout.decode().split("\n")
			for line in lines:
				if line.startswith("gfx"):
					if line.endswith("\r"):
						line = line[:-1]
					asics.append(line)
		return asics

	def _write_temp_dxc_arg(self) -> str:
		dxc_arg_filepath = os.path.join(self._temp_dir, "dxc_arg.txt")
		with open(dxc_arg_filepath, "w") as fp:
			fp.write(self._compiler_args.get_value())
		return dxc_arg_filepath

	def _write_temp_hlsl_source(self, stage_str: str) -> str:
		state = self.context.CurPipelineState()
		stage = self.shader_stage_map[stage_str]
		reflection = state.GetShaderReflection(stage)
		if reflection is not None:
			name: str = reflection.debugInfo.files[0].filename
			source: str = reflection.debugInfo.files[0].contents
			if name.endswith(".hlsl"):
				name = name[0:-5]
			name = name + (".%s" % stage_str)
			name = name + ".hlsl"
			filepath = os.path.join(self._temp_dir, name)
			with open(filepath, "w") as fp:
				fp.write(source)
			print("Dump hlsl source: %s" % filepath)
			return filepath
		return ""

	def _write_temp_root_sig_source(self) -> str:
		filepath = "C://ErrorOnGenerateRootSignature"
		root_sig_resource = PipelineStateUtils().get_root_signature_resource(self.context.CurPipelineState())
		if root_sig_resource is not None:
			root_sig = RootSignature(self.context, self.context.GetResource(root_sig_resource))
			filepath = os.path.join(self._temp_dir, self.ROOT_SIGNATURE_FILENAME)
			root_sig.dump(self.ROOT_SIGNATURE_MACRO, filepath)
		return filepath

	def _write_temp_gpso_source(self) -> str:
		filepath = "C://ErrorOnGenerateGraphicPipelineObject"
		if self.context.CurPipelineState() is not None:
			gpso = GraphicPipelineStateObject(self.context, self.context.CurPipelineState())
			filepath = os.path.join(self._temp_dir, self.GPSO_FILENAME)
			gpso.dump(filepath)
		return filepath

	def _get_actual_output_filepath(self, mode, arg_filepath) -> str:
		stage_short_names = {
			"Vertex": "vert",
			"Pixel": "pix",
			"Compute": "comp",
			"Mesh": "mesh",
			"Amplification": "ampl",
		}
		asic = self._asic.get_value().split(" ")[0]
		name = arg_filepath.split(".")[0]
		ext = arg_filepath.split(".")[1]
		stage = ShaderStageName(self._shader_stage.get_value()).name if mode == RGAMode.LiveRegister else stage_short_names[ShaderStageName(self._shader_stage.get_value()).name]
		stage = stage.lower()
		filename = "%s_%s_%s.%s" % (asic, name, stage, ext)
		return os.path.join(self._temp_dir, filename)

	def _refresh_shader_infos(self):
		state = self.context.CurPipelineState()
		reflection = state.GetShaderReflection(self.shader_stage_map[self._shader_stage.get_value()])
		if reflection is not None:
			self._shader_entry.set_value(reflection.entryPoint)
			if len(reflection.debugInfo.compileFlags.flags) > 0:
				flags = reflection.debugInfo.compileFlags.flags[0].value.split(" ")
				if "-HV" in flags:
					hv = flags[flags.index("-HV") + 1]
					self._compiler_args.set_value("-HV %s" % hv)
				if "/T" in flags:
					# "cs_4_0"
					model = flags[flags.index("/T") + 1]
					self._shader_model.set_value(model[3:])
		else:
			self._shader_entry.set_value("")
		pass

	def _get_shader_entry(self, stage_str) -> str:
		state = self.context.CurPipelineState()
		reflection = state.GetShaderReflection(self.shader_stage_map[stage_str])
		if reflection is not None:
			return reflection.entryPoint
		return ""
