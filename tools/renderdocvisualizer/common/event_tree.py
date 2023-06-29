# -*- coding:UTF-8 -*-

from .table import Table
from renderdoc import TextureType, ResourceFormat, TextureCategory, ShaderStage, ActionFlags, Topology, ResourceType
MAX_LEVEL_TO_SHOW = 10

SHADER_RESOURCES_FOR_PASS = "None"  # "None","PrePass DDM_AllOpaque (Forced by DBuffer)", "CompositionBeforeBasePass", "BasePass", "Lights", "Translucency"
SHADER_SAMPLING_WAYS = [" sample", "=sample", "sample_b", "sample_c", "sample_c_lz", "sample_d", "sample_l"]
USE_FASTER_TRIANGLES_COUNTER = True

ONLY_STANDARD_DEFERRED_LIGHTING_VALID = True  # only "StandardDeferredLighting" of Lights valid when statistics ps invocation and shader resources
TRIANGLE_PERCENTAGE_THRESHOLD = 0.01  # 0.01%
TIME_PERCENTAGE_THRESHOLD = 0.01  # 0.01%
DC_PERCENTAGE_THRESHOLD = 0.01  # 0.01%
INVOCATION_THRESHOLD = 0.001


# noinspection DuplicatedCode
class Texture(object):
    def __init__(self, tex, res_id, name):
        self.tex = tex
        self.id = res_id
        self.name = name
        tex_type = '%s' % TextureType(tex.type)
        # remove prefix of type
        self.type = tex_type.replace('TextureType.', '').replace('Array', '[ ]')
        self.arraysize = tex.arraysize
        # remove prefix of creation flags
        usages = '%s' % TextureCategory(tex.creationFlags)
        self.usages = usages.replace('TextureCategory.', '')
        self.width = tex.width
        self.height = tex.height
        self.depth = tex.depth
        self.format = ResourceFormat(tex.format).Name()
        # texture table
        pass

    def get_texture_info(self):
        texture_info = [
            ["Resource ID", "int", self.id, "N", ""],
            ["Name", "string", self.name, "N", ""],
            ["Type", "string", self.type, "N", ""],
            ["Array Size", "int", self.arraysize, "N", ""],
            ["Usage", "string", self.usages, "N", ""],
            ["Width", "int", self.width, "N", ""],
            ["Height", "int", self.height, "N", ""],
            ["Depth", "int", self.depth, "N", ""],
            ["Format", "string", self.format, "N", ""]
        ]
        return texture_info


# noinspection DuplicatedCode
class BaseNode(object):
    # Struct of EventsTree:
    # root_rame(equal to 'FRAME' in RenderDoc event marker)
    #     Pass
    #         State(level = 2)
    #             State(level = 1)
    #                 State(level = 0) || Draw(Flag = DrawCall)

    def __getstate__(self):
        pickable = dict(self.__dict__)
        del pickable['draw']
        return pickable

    def __init__(self, draw, tree):
        self.draw = draw
        self.eventId = draw.eventId if draw else 0
        self.level = 0
        self.triangles_num = 0
        self.time = 0
        self.draw_call = 0
        self.ps_invocation = 0
        self.vs_invocation = 0
        self.resolution = 0  # Width x Height
        self.html_name = ""
        self.childs = []
        self.childsId = []
        self.tree = tree

    def get_name(self):
        name = self.draw.GetName(self.tree.controller.GetStructuredFile())
        return name

    def calculate_triangles_number(self):
        for s_child in self.childs:
            self.triangles_num += s_child.calculate_triangles_number()
        return self.triangles_num

    def calculate_time_overhead(self, event_id, val):
        if event_id in self.childsId:
            self.time += val
            for child in self.childs:
                child.calculate_time_overhead(event_id, val)
        return self.time

    def calculate_drawcall(self):
        return self.draw_call

    def calculate_invocation(self, event_id, val, is_vs=False):
        if (event_id in self.childsId) and (val > 0):
            if is_vs:
                self.vs_invocation += val
            else:
                self.ps_invocation += val
            for child in self.childs:
                child.calculate_invocation(event_id, val, is_vs)
        return self.vs_invocation if is_vs else self.ps_invocation

    def show_binding_textures(self):
        return ""

    def show_shader_instructions(self):
        return ""

    def get_event_info(self, relative_html, one_over_triangles, one_over_time, one_over_drawcall, one_over_resolution):
        name = self.draw.GetName(self.tree.controller.GetStructuredFile())
        event_info = [
            # [TableHeader,         DataType,        Data,                                     bNeedSorted,  linker]
            ["EventID", "int", self.eventId, "Y", ""],
            ["Pass/State", "string", name, "N", relative_html],
            ["Triangles Num", "int", self.triangles_num, "Y", ""],
            ["N Proportion", "percentage", self.triangles_num * one_over_triangles * 100, "N", ""],
            ["Time Overhead(us)", "float", self.time, "Y", ""],
            ["T Proportion", "percentage", self.time * one_over_time * 100, "N", ""],
            ["Draw Call", "int", self.draw_call, "Y", ""],
            ["DC Proportion", "percentage", self.draw_call * one_over_drawcall * 100, "N", ""],
            ["VS Invocation", "int", self.vs_invocation, "Y", ""],
            ["VSI Proportion", "float", self.vs_invocation * one_over_resolution, "N", ""],
            ["PS Invocation", "int", self.ps_invocation, "Y", ""],
            ["PSI Proportion", "float", self.ps_invocation * one_over_resolution, "N", ""]
        ]
        return event_info


# noinspection DuplicatedCode
class DrawNode(BaseNode):  # DrawCall action
    current = None

    def __getstate__(self):
        pickable = super().__getstate__()
        del pickable["topology_type"]
        del pickable["bind_textures_resources"]
        return pickable

    def __init__(self, draw, parent, tree):
        super().__init__(draw, tree)
        self.draw_call = 1
        self.childsId.append(self.eventId)
        self.parent = parent
        self.is_last_level = True
        self.parent_path_dict = {}
        self.topology_type = None
        self.bind_textures_resources = []
        self.bind_textures_list = []
        self.textures_num = 0
        self.vs_shader_code = ""
        self.ps_shader_code = ""
        self.vs_instructions_num = 0
        self.ps_instructions_num = 0
        self.vs_sampling_times = 0
        self.ps_sampling_times = 0
        if self.parent.first_draw_id < 0:
            self.parent.first_draw_id = self.eventId
        if self.parent.get_name() == SHADER_RESOURCES_FOR_PASS:
            self.collect_draw_call_info()
            pass

    def collect_draw_call_info(self):
        self.tree.controller.SetFrameEvent(self.eventId, False)
        state = self.tree.controller.GetPipelineState()
        # PrimitiveTopology
        self.topology_type = state.GetPrimitiveTopology()
        # Binding textures
        self.collect_binding_textures(state)
        # Shader instructions
        self.calculate_shader_instructions(state)
        # Shader sampling times
        self.calculate_shader_sampling_times()

    def collect_binding_textures(self, state):
        # Shader binding textures
        resource_array_list = state.GetReadOnlyResources(ShaderStage.Pixel, True)
        tex_list = []
        for resource_array in resource_array_list:
            tex_list.extend(resource_array.resources)
        # set() :remove complex elements
        self.bind_textures_resources.extend(list(set(tex_list)))
        self.bind_textures_resources.sort(key=tex_list.index)
        pass

    # noinspection DuplicatedCode
    def calculate_shader_instructions(self, state):
        targets = self.tree.controller.GetDisassemblyTargets(True)
        target = targets[0]
        # For some APIs, it might be relevant to set the PSO id or entry point name
        pipe = state.GetGraphicsPipelineObject()

        # Get the pixel shader's reflection object
        vs = state.GetShaderReflection(ShaderStage.Vertex)
        self.vs_shader_code = self.tree.controller.DisassembleShader(pipe, vs, target)
        code_lines = self.vs_shader_code.split("\n")
        last_line = code_lines[len(code_lines) - 2]  # last one is '\n'
        self.vs_instructions_num = int(last_line.split(":", 1)[0]) + 1

        # Get the pixel shader's reflection object
        ps = state.GetShaderReflection(ShaderStage.Pixel)
        self.ps_shader_code = self.tree.controller.DisassembleShader(pipe, ps, target)
        code_lines = self.ps_shader_code.split("\n")
        last_line = code_lines[len(code_lines) - 2]  # last one is '\n'
        self.ps_instructions_num = int(last_line.split(":", 1)[0]) + 1

    def calculate_shader_sampling_times(self):
        key_word_mode = "###("
        for way in SHADER_SAMPLING_WAYS:
            key_word = key_word_mode.replace("###", way)
            self.vs_sampling_times += self.vs_shader_code.count(key_word)
            self.ps_sampling_times += self.ps_shader_code.count(key_word)

    def calculate_invocation_for_lights(self, event_id, val, is_valid=False, is_vs=False):
        if is_valid and (self.draw.flags & ActionFlags.Drawcall) and event_id in self.childsId:
            if is_vs:
                self.vs_invocation += val
            else:
                self.ps_invocation += val
            return True
        return False

    def calculate_triangles_number(self):
        if USE_FASTER_TRIANGLES_COUNTER:
            # Faster way to counter triangles number
            name_str = self.get_name()
            if "Indexed" in name_str:
                if "Instanced" in name_str:
                    self.triangles_num = self.draw.numIndices / 3 * self.draw.numInstances
                else:
                    self.triangles_num = self.draw.numIndices / 3
            elif "Instanced" in name_str:
                if not self.topology_type:
                    self.tree.controller.SetFrameEvent(self.eventId, False)
                    state = self.tree.controller.GetPipelineState()
                    self.topology_type = state.GetPrimitiveTopology()
                if self.topology_type == Topology.TriangleStrip:
                    self.triangles_num = (self.draw.numIndices - 2) * max(self.draw.numInstances, 1)
                elif self.topology_type == Topology.TriangleList:
                    self.triangles_num = self.draw.numIndices / 3 * max(self.draw.numInstances, 1)
            elif "Draw(" in name_str:
                self.triangles_num = (self.draw.numIndices - 2)
            else:
                self.triangles_num = 0
        # Generally
        else:
            if not self.topology_type:
                self.tree.controller.SetFrameEvent(self.eventId, True)
                state = self.tree.controller.GetPipelineState()
                self.topology_type = state.GetPrimitiveTopology()
            if self.topology_type == Topology.TriangleStrip:
                self.triangles_num = (self.draw.numIndices - 2) * max(self.draw.numInstances, 1)
            elif self.topology_type == Topology.TriangleList:
                self.triangles_num = self.draw.numIndices / 3 * max(self.draw.numInstances, 1)
            else:
                self.triangles_num = 0
        return self.triangles_num

    def output_level(self, markdown, indent):
        if self.level <= MAX_LEVEL_TO_SHOW and self.is_last_level:
            markdown.write(
                "<font color ='#00dd00'>%s %s &emsp; LEVEL:%d  &emsp; LAST: %d SECOND: %d (SHOW)</font>\n" % (
                    indent, self.get_name(), self.level, self.is_last_level, False))
            markdown.write('<br/>')
        else:
            markdown.write('%s %u &emsp; LEVEL:%d &emsp; LAST: %d SECOND:%d\n' % (
                indent, self.get_name(), self.level, self.is_last_level, False))
            markdown.write('<br/>')

    def handle_binding_textures(self):
        for tex in self.bind_textures_resources:
            res_id = tex.resourceId
            if res_id in self.tree.resources_dict.keys():
                bind_resource = self.tree.resources_dict[res_id]
                if bind_resource.type == ResourceType.Texture:
                    bind_texture = Texture(self.tree.textures_dict[res_id], bind_resource.resourceId,
                                           bind_resource.name)
                    texture_info = bind_texture.get_texture_info()
                    self.bind_textures_list.append(texture_info)
                    self.textures_num += 1
        pass

    def show_binding_textures(self):
        content = ""
        if len(self.bind_textures_list) > 0 or len(self.bind_textures_resources) > 0:
            texture_table = Table()
            if len(self.bind_textures_list) == 0:
                self.handle_binding_textures()
            content = texture_table.print_table(self.bind_textures_list)
        return content

    def write_shader_code_html(self, shader_html, is_vs=False):
        # shader code
        html = open(shader_html, 'w', encoding='utf-8')
        if is_vs:
            html.write('<h2>Vertex Shader Code:</h2>\n')
            temp_code = self.vs_shader_code.replace("\n", "<br/>\n")
        else:
            html.write('<h2>Pixel Shader Code:</h2>\n')
            temp_code = self.ps_shader_code.replace("\n", "<br/>\n")
        code = temp_code.replace("    ", "&emsp;&emsp;")
        html.write(code)
        html.write("<br/>")
        html.close()

    def show_shader_instructions(self):
        content = ""
        content += "<table border=1 cellpadding=10 cellspacing=0 align='center'>\n"
        content += (
            "<tr  bgcolor= c0c0c0><td>Shader Stage</td><td>Instruvtions Number</td><td>Sampling Times</td></tr>")

        if self.vs_shader_code != "" or self.ps_shader_code != "":
            # Write html for shader code
            vs_html = self.tree.deitail_dirpath / ("vs_" + self.html_name)
            self.write_shader_code_html(vs_html, True)
            content += ("<tr><td ><a href='%s'>%s</a></td><td>%d</td><td>%d</td></tr>" % (vs_html, "Vertex Shader", self.vs_instructions_num, self.vs_sampling_times))

            ps_html = self.tree.deitail_dirpath / ("ps_" + self.html_name)
            self.write_shader_code_html(ps_html)
            content += ("<tr><td><a href='%s'>%s</a></td><td>%d</td><td>%d</td></tr>" % (ps_html, "Pixel Shader", self.ps_instructions_num, self.ps_sampling_times))
        else:
            content += ("<tr><td >%s</td><td>%d</td><td>%d</td></tr>" % ("Vertex Shader", self.vs_instructions_num, self.vs_sampling_times))
            content += ("<tr><td>%s</td><td>%d</td><td>%d</td></tr>" % ("Pixel Shader", self.ps_instructions_num, self.ps_sampling_times))
        content += "</table>\n"
        return content


class StateNode(BaseNode):
    current = None  # State : self

    def __init__(self, draw, parent, tree):
        super().__init__(draw, tree)
        self.parent = parent
        self.is_last_level = False
        self.is_second_last_level = True
        self.parent_path_dict = {}
        self.fillin_childs()

    def fillin_childs(self):
        if len(self.draw.children) < 2:
            self.is_last_level = True
            self.is_second_last_level = True
        for s_d in self.draw.children:
            if s_d.flags & ActionFlags.Drawcall:
                new_childdraw = DrawNode(s_d, self.parent, self.tree)
                self.tree.draw_call_dict[new_childdraw.eventId] = new_childdraw
                self.draw_call += 1
                new_childdraw.level = self.level + 1
                self.is_second_last_level = False if not (
                            self.is_second_last_level and new_childdraw.is_last_level) else True
                self.childs.append(new_childdraw)
                self.childsId.append(s_d.eventId)
            else:
                new_childstate = StateNode(s_d, self.parent, self.tree)
                self.childs.append(new_childstate)
                new_childstate.level = self.level + 1
                if s_d.flags & ActionFlags.Dispatch \
                        or s_d.flags & ActionFlags.MultiAction \
                        or s_d.flags & ActionFlags.Clear \
                        or s_d.flags & ActionFlags.Copy:
                    # Collect children's ID
                    self.childsId.append(s_d.eventId)
                    new_childstate.is_last_level = True
                else:
                    for childid in new_childstate.childsId:
                        self.childsId.append(childid)
                self.draw_call += new_childstate.draw_call
                self.is_second_last_level = False if not (
                            self.is_second_last_level and new_childstate.is_last_level) else True
        self.childsId.append(self.eventId)

    def calculate_invocation(self, event_id, val, is_vs=False):
        if event_id in self.childsId:
            if is_vs:
                self.vs_invocation += val
            else:
                self.ps_invocation += val
            for child in self.childs:
                child.calculate_invocation(event_id, val, is_vs)

    def calculate_invocation_for_lights(self, event_id, val, is_valid=False, is_vs=False):
        result = False
        if event_id in self.childsId:
            for child in self.childs:
                if not is_valid and self.get_name() != "StandardDeferredLighting":
                    result |= child.calculate_invocation_for_lights(event_id, val, False, is_vs)
                else:
                    result |= child.calculate_invocation_for_lights(event_id, val, True, is_vs)
                if result:
                    if is_vs:
                        self.vs_invocation += val
                    else:
                        self.ps_invocation += val
                    return True
        return result

    def output_level(self, markdown, indent):
        # markdown.write('%s %s &emsp; PARENT:%s &emsp; LEVEL:%d\n' % (indent, self.getName(), self.parent.getName(), self.level))
        if self.level <= MAX_LEVEL_TO_SHOW and self.is_last_level:
            markdown.write(
                "<font color ='#00dd00'>%s %s &emsp; LEVEL:%d  &emsp; LAST: %d SECOND: %d (SHOW)</font>\n" % (
                    indent, self.get_name(), self.level, self.is_last_level, self.is_second_last_level))
            markdown.write('<br/>')
        elif self.level <= MAX_LEVEL_TO_SHOW:
            markdown.write("<font>%s %s &emsp; LEVEL:%d  &emsp; LAST: %d SECOND:%d (SHOW)</font>\n" % (
                indent, self.get_name(), self.level, self.is_last_level, self.is_second_last_level))
            markdown.write('<br/>')
        else:
            markdown.write('%s %u &emsp; LEVEL:%d &emsp; LAST: %d SECOND:%d\n' % (
                indent, self.get_name(), self.level, self.is_last_level, self.is_second_last_level))
            markdown.write('<br/>')
        for child in self.childs:
            child.output_level(markdown, indent + '&emsp;&emsp;&emsp;')

    def get_event_info(self, relative_html, one_over_triangles, one_over_time, one_over_drawcall, one_over_resolution):
        event_info = super().get_event_info(relative_html, one_over_triangles, one_over_time, one_over_drawcall,
                                            one_over_resolution)
        if self.is_second_last_level and (self.parent.get_name() == SHADER_RESOURCES_FOR_PASS) and len(
                self.childs) == 2:
            total_textures = 0
            total_vs_instructions = 0
            total_ps_instructions = 0
            total_vs_sampling_times = 0
            total_ps_sampling_times = 0
            for child in self.childs:
                if isinstance(child, DrawNode):
                    if len(child.bind_textures_list) == 0 and len(child.bind_textures_resources) > 0:
                        child.handle_binding_textures()
                    total_textures += child.textures_num
                    total_vs_instructions += child.vs_instructions_num
                    total_ps_instructions += child.ps_instructions_num
                    total_vs_sampling_times += child.vs_sampling_times
                    total_ps_sampling_times += child.ps_sampling_times
            event_info.extend([
                # TableHeader               DataType         Data                              bNeedSorted     linker
                ["Binding Textures", "int", total_textures, "Y", ""],
                ["VS Instructions", "int", total_vs_instructions, "Y", ""],
                ["PS Instructions", "int", total_ps_instructions, "Y", ""],
                ["VS Sampling Times", "int", total_vs_sampling_times, "Y", ""],
                ["PS Sampling Times", "int", total_ps_sampling_times, "Y", ""]
            ])
        return event_info


class PassNode(BaseNode):
    current = None

    def __init__(self, draw, tree):
        super().__init__(draw, tree)
        self.resolution_width = 0
        self.resolution_height = 0
        self.resolution_depth = 0
        self.first_draw_id = -1
        self.is_second_last_level = True
        self.parent_path_dict = {}
        if draw:
            self.fillin_children()

    def add_state(self, draw):
        new_state = StateNode(draw, self, self.tree)
        self.childs.append(new_state)
        self.is_second_last_level = False if not (self.is_second_last_level and new_state.is_last_level) else True
        self.draw_call += new_state.draw_call
        for childid in new_state.childsId:
            self.childsId.append(childid)

    def add_draw(self, draw):
        new_draw = DrawNode(draw, self, self.tree)
        self.tree.draw_call_dict[new_draw.eventId] = new_draw
        self.is_second_last_level = False if not (self.is_second_last_level and new_draw.is_last_level) else True
        self.draw_call += 1
        self.childsId.append(draw.eventId)
        self.childs.append(new_draw)

    def fillin_children(self):
        self.childsId.append(self.eventId)
        for child in self.draw.children:
            if child.flags & ActionFlags.Drawcall:
                self.add_draw(child)
            else:
                self.add_state(child)

    def calculate_invocation(self, result, invocation_desc, is_vs=False):
        pass_name = self.get_name()
        if invocation_desc.resultByteWidth == 4:
            val = result.value.u32
        else:
            val = result.value.u64
        if (result.eventId in self.childsId) and (val > 0):
            if pass_name == "Lights" and ONLY_STANDARD_DEFERRED_LIGHTING_VALID:
                for child in self.childs:
                    if child.calculate_invocation_for_lights(result.eventId, val, is_vs):
                        if is_vs:
                            self.vs_invocation += val
                        else:
                            self.ps_invocation += val
            else:
                super().calculate_invocation(result.eventId, val, is_vs)
        return self.vs_invocation if is_vs else self.ps_invocation

    def get_name(self):
        if self.draw:
            name = self.draw.GetName(self.tree.controller.GetStructuredFile())
        else:
            name = "OthersPass"
        return name


# noinspection DuplicatedCode
class EventsTree(object):
    # Value returned by GetRootActions()
    #     GetRootActions()[0] : EndEvent
    #     GetRootActions()[1] : EndEvent
    #     GetRootActions()[2] : Frame XXXX

    def __getstate__(self):
        pickable = dict(self.__dict__)
        del pickable["resources_dict"]
        del pickable["textures_dict"]
        del pickable["root_frame"]
        return pickable

    def __init__(self, root_frame, deitail_dirpath, controller):
        self.passes = []
        self.triangles_num = 0
        self.time = 0.0
        self.draw_call = 0
        self.ps_invocation = 0
        self.vs_invocation = 0
        self.textures_dict = {}
        self.resources_dict = {}
        self.draw_call_dict = {}
        self.root_frame = root_frame
        self.controller = controller
        self.deitail_dirpath = deitail_dirpath
        pass

    def reset(self):
        self.passes.clear()
        self.triangles_num = 0
        self.time = 0.0
        self.draw_call = 0
        self.ps_invocation = 0
        self.vs_invocation = 0
        self.textures_dict.clear()
        self.resources_dict.clear()
        self.draw_call_dict.clear()

    def add_pass(self, draw):
        new_pass = PassNode(draw, self)
        self.passes.append(new_pass)
        PassNode.current = self.passes[-1]
        pass
