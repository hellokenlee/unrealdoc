# RenderDoc Python console, powered by python 3.6.4.
# The 'pyrenderdoc' object is the current CaptureContext instance.
# The 'renderdoc' and 'qrenderdoc' modules are available.
# Documentation is available: https://renderdoc.org/docs/python_api/index.html

# Local Path of Python36
LOCAL_PYTHON36_PATH = 'E:\\python3.6'

# Used to open exist rdc file
RDC_FILE = ""
ROOT_NAME = ""  # ROOT_NAME =""  =>  all passes in the same level of "Capture Start"
SHADER_RESOURCES_FOR_PASS = "None"  # "None","PrePass DDM_AllOpaque (Forced by DBuffer)", "CompositionBeforeBasePass", "BasePass", "Lights", "Translucency"
KEEP_PREVIOUS_SHADER_INFO = False

ONLY_STANDARD_DEFERRED_LIGHTING_VALID = True  # only "StandardDeferredLighting" of Lights valid when statistics ps invocation and shader resources
USE_FASTER_TRIANGLES_COUNTER = True
# Ways of HLSL: "Sample","Sample", "SampleBias", "SampleCmp", "SampleCmpLevelZero", "SampleGrad", "SampleLevel"
SHADER_SAMPLING_WAYS = [" sample", "=sample", "sample_b", "sample_c", "sample_c_lz", "sample_d", "sample_l"]


TRIANGLE_PERCENTAGE_THRESHOLD = 0.01  # 0.01%
TIME_PERCENTAGE_THRESHOLD = 0.01  # 0.01%
DC_PERCENTAGE_THRESHOLD = 0.01  # 0.01%
INVOCATION_THRESHOLD = 0.001
# config of pie chart
MAX_LEVEL_TO_SHOW = 10
MAX_ITEMS_TO_SHOW = 1000
LABEL_LENGTH_IN_VIEW = 90
LABEL_NUMBER_IN_VIEW = 55

g_absoulte = None
g_assetsfolder = None
g_detailfolder = None
g_shaderfolder = None
g_file_index = 0

from pathlib import WindowsPath
import sys
import os
import shutil
import math
import time

if __name__ == "__main__":
    # import pyechart
    pyechart_lib_path = LOCAL_PYTHON36_PATH + '\\lib'
    pyechart_package_path = LOCAL_PYTHON36_PATH + '\\lib\\site-packages'
    pyechart_dll_path = LOCAL_PYTHON36_PATH + '\\DLLs'
    if pyechart_lib_path not in sys.path:
        sys.path.append(pyechart_lib_path)
    if pyechart_package_path not in sys.path:
        sys.path.append(pyechart_package_path)
    if pyechart_dll_path not in sys.path:
        sys.path.append(pyechart_dll_path)

from pyecharts.charts import Pie
from pyecharts.charts import Tab
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode

# Import renderdoc if not already imported (e.g. in the UI)
if 'renderdoc' not in sys.modules and '_renderdoc' not in sys.modules:
    import renderdoc

# Alias renderdoc for legibility
# rd = renderdoc
rd = sys.modules["renderdoc"]

table_sort_function = '''
<script type="text/javascript" src="./thirdparty/jquery-1.7.2.min.js"></script>
    <script>
        var tag=1;
        function sortNumberAS(a, b)
        {
            return a - b
        }
        function sortNumberDesc(a, b)
        {
            return b-a
        }

        function SortTable(obj){
            var columnNum = COLUMN_NUM;
            var tdArrays=[];
            for(var i=0; i<columnNum; i++)
            {
                var tds=document.getElementsByName("td" + i);
                var tdArray = [];
                for(var j=0;j<tds.length;j++)
                {
                    tdArray.push(tds[j].innerHTML);
                }
                tdArrays.push(tdArray);
            }
            var tds=document.getElementsByName("td"+obj.id.substr(2));
            var columnArray=[];
            for(var i=0;i<tds.length;i++){
                columnArray.push(parseInt(tds[i].innerHTML));
            }
            var orginArray=[];
            for(var i=0;i<columnArray.length;i++){
                orginArray.push(columnArray[i]);
            }
            if(obj.className=="desc"){
                columnArray.sort(sortNumberDesc);               
                obj.className="as";
            }else{
                columnArray.sort(sortNumberAS);               
                obj.className="desc";
            }

            for(var i=0;i<columnArray.length;i++){
                for(var j=0;j<orginArray.length;j++){
                    if(orginArray[j]==columnArray[i]){
                        for(var k=0; k<columnNum; k++)
                        {
                            document.getElementsByName("td"+k)[i].innerHTML=tdArrays[k][j];
                        }
                        orginArray[j]=null;
                        break;
                    }
                }
            }
        }
    </script>
'''


# Format of Table Content:
# row1: ["TableHeaderName", "DataType", Data, "Hyperlink"]

class Table:
    def __init__(self):
        self.table_format = "<table border=1 cellpadding=10 cellspacing=0 align='center'>"
        self.table_end = "</table>"
        self.header_format = "<tr bgcolor= c0c0c0>"
        self.header_begin = "<tr>"
        self.header_end = "</tr>"
        self.new_line = "\n"
        self.html_padding = "<br/>"
        self.header = 0
        # A web page cannot have more than one table to be sorted
        self.need_sort = False

    def __printTableHeader(self, table_row0):
        # Table header
        content = self.table_format + self.new_line + self.header_format + self.new_line  # <table> and <tr>
        for table_element in table_row0:
            if self.need_sort and table_element[3] == "Y":
                table_element[0] += "(S)"
                content += ("<th id='th%d' onclick='SortTable(this)' class='desc'>" % table_row0.index(table_element))
            else:
                content += "<th>"
            content += table_element[0]  # header
            content += "</th>" + self.new_line
            self.header += 1
        content += self.header_end + self.new_line  # </tr>
        return content

    def __printTableContent(self, table_row, max_element_length):
        # Table content
        content = ""
        for table_element in table_row:
            index = table_row.index(table_element)
            td_format = ("<td name='td%d'>" % index) if self.need_sort else "<td>"
            if table_element[1] == "int":
                content += td_format + ("<a href=%s>%d</a></td>" % (table_element[4], table_element[2])) if \
                    table_element[4] != "" else (td_format + ("%d</td>" % (table_element[2])))
            elif table_element[1] == "string":
                content += td_format + ("<a href=%s>%s</a></td>" % (table_element[4], table_element[2])) if \
                    table_element[4] != "" else (td_format + ("%s</td>" % (table_element[2])))
            elif table_element[1] == "float":
                content += td_format + ("<a href=%s>%.3f</a></td>" % (table_element[4], table_element[2])) if \
                    table_element[4] != "" else (td_format + ("%.3f</td>" % (table_element[2])))
            elif table_element[1] == "percentage":
                content += td_format + ("<a href=%s>%.2f %%</a></td>" % (
                    table_element[4], table_element[2])) if table_element[4] != "" else (
                        td_format + ("%.2f %%</td>" % (table_element[2])))
        for i in range(len(table_row), max_element_length):
            td_format = ("<td name='td%d'>" % i) if self.need_sort else "<td>"
            content += td_format + "-1</td>"
        return content

    def printTable(self, obj_table, need_sort=False, max_element_row=0):
        content = ""
        self.need_sort = need_sort
        if len(obj_table) > 0:
            sort_function = table_sort_function.replace("COLUMN_NUM", str(len(obj_table[max_element_row]))) if self.need_sort else ""
            content = sort_function + self.__printTableHeader(obj_table[max_element_row])  # <table>
            max_element_length = len(obj_table[max_element_row])
            for table_row in obj_table:
                content += self.header_begin  # <tr>
                content += self.__printTableContent(table_row, max_element_length)
                content += self.header_end + self.new_line  # </tr>
            content += self.table_end + self.html_padding  # </table>
        return content


class Texture(object):
    def __init__(self, tex, id, name):
        self.tex = tex
        self.id = id
        self.name = name
        tex_type = '%s' % rd.TextureType(tex.type)
        # remove prefix of type
        self.type = tex_type.replace('TextureType.', '').replace('Array', '[ ]')
        self.arraysize = tex.arraysize
        # remove prefix of creation flags
        usages = '%s' % rd.TextureCategory(tex.creationFlags)
        self.usages = usages.replace('TextureCategory.', '')
        self.width = tex.width
        self.height = tex.height
        self.depth = tex.depth
        self.format = rd.ResourceFormat(tex.format).Name()
        # texture table

    def getTextureInfo(self):
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


class Shader(object):
    def __init__(self, state, stage_type, pass_name):
        self.hash_value = ""
        self.stage_type = rd.ShaderStage.Pixel if stage_type == "Pixel" else rd.ShaderStage.Vertex
        self.show_type = stage_type
        self.pass_name = pass_name
        self.textures_num = 0
        self.shader_code = ""
        self.instructions_num = 0
        self.sampling_times = 0
        self.usage_list = {}
        self.bind_textures_list = []
        self.__collectShaderResources(state)

    def __collectShaderResources(self, state):
        # Binding textures
        self.__collectBindingTextures(state)
        # Shader instructions
        self.__calculateShaderInstructions(state)
        # Shader sampling times
        self.__calculateShaderSamplingTimes()
        pass

    def __collectBindingTextures(self, state):
        # Shader binding textures
        resource_array_list = state.GetReadOnlyResources(self.stage_type, True)
        tex_list = []
        for resource_array in resource_array_list:
            tex_list.extend(resource_array.resources)
        # set() :remove complex elements
        bind_textures_resources = []
        bind_textures_resources.extend(list(set(tex_list)))
        bind_textures_resources.sort(key=tex_list.index)
        for tex in bind_textures_resources:
            res_id = tex.resourceId
            if res_id in g_events_tree.resources_dict.keys():
                bind_resource = g_events_tree.resources_dict[res_id]
                if bind_resource.type == rd.ResourceType.Texture:
                    bind_texture = Texture(g_events_tree.textures_dict[res_id], bind_resource.resourceId,
                                           bind_resource.name)
                    texture_info = bind_texture.getTextureInfo()
                    self.bind_textures_list.append(texture_info)
                    self.textures_num += 1
        pass

    def __calculateShaderInstructions(self, state):
        targets = EventsTree.controller.GetDisassemblyTargets(True)
        target = targets[0]
        # For some APIs, it might be relevant to set the PSO id or entry point name
        pipe = state.GetGraphicsPipelineObject()

        # Get the reflection object of shader
        shader = state.GetShaderReflection(self.stage_type)
        self.shader_code = EventsTree.controller.DisassembleShader(pipe, shader, target)
        code_lines = self.shader_code.split("\n")
        first_line = code_lines[0]  # first one is shader hash
        if first_line.startswith("Shader hash "):
            whole_hash_value = first_line.replace("Shader hash ", "")
            hash_list = whole_hash_value.split("-", 1)
            self.hash_value = hash_list[0]
        last_line = code_lines[len(code_lines) - 2]  # last one is '\n'
        try:
            self.instructions_num = int(last_line.split(":", 1)[0]) + 1
        except ValueError:
            self.instructions_num = 0

    def __calculateShaderSamplingTimes(self):
        key_word_mode = "###("
        for way in SHADER_SAMPLING_WAYS:
            key_word = key_word_mode.replace("###", way)
            self.sampling_times += self.shader_code.count(key_word)
        pass

    def __writeShaderCodeHtml(self, shader_html):
        # shader code
        html = open(shader_html, 'w', encoding='utf-8')
        html.write('<h2>%s Shader Code:</h2>\n' % self.show_type)
        temp_code = self.shader_code.replace("\n", "<br/>\n")
        code = temp_code.replace("    ", "&emsp;&emsp;")
        html.write(code)
        html.write("<br/>")
        html.close()

    def getHandledHashValue(self):
        return self.hash_value + "_" + str(self.instructions_num) + "_" + str(self.sampling_times)

    def showBindingTextures(self):
        content = ""
        if len(self.bind_textures_list) > 0:
            content = ("<h4>%s shader textures</h4>\n" % self.show_type)
            texture_table = Table()
            content += texture_table.printTable(self.bind_textures_list)
        return content

    def getShaderInstructions(self, code_html):
        prefix = "vs_" if self.stage_type == rd.ShaderStage.Vertex else "ps_"
        relative_html = ""
        if code_html != "":
            html = g_detailfolder / (prefix + code_html)
            relative_html = str(html).replace(str(g_detailfolder), ".")
            self.__writeShaderCodeHtml(html)
        pass_shader_html = ("..\\Shader\\%s_%s.html" % (self.pass_name, self.show_type))
        shader_info = [
            ["Shader Stage", "string", self.show_type + " Shader", "N", relative_html],
            ["Pass Stage", "string", self.pass_name, "N", pass_shader_html],
            ["Shader Hash", "string", self.hash_value, "N", ""],
            ["Instructions Number", "int", self.instructions_num, "Y", ""],
            ["Sampling Times", "int", self.sampling_times, "Y", ""]
        ]
        return shader_info

    def getTexturesNum(self):
        return self.textures_num

    def addUsages(self, event_id, relative_html):
        self.usage_list[event_id] = relative_html

    def getUsages(self):
        usage = ""
        for event_id, relative_path in self.usage_list.items():
            # usage += str(event_id) + ", "
            usage += ("<a href=%s>%s</a>, " % (relative_path, event_id))
        return usage

    def getShaderInformation(self):
        return [self.stage_type, self.textures_num, self.instructions_num, self.sampling_times]


# Struct of EventsTree:
# root_rame(equal to 'FRAME' in RenderDoc event marker)
#     Pass
#         State(level = 2)
#             State(level = 1)
#                 State(level = 0) || Draw(Flag = DrawCall)
class BaseNode(object):
    def __init__(self, draw):
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
        self.parent_path_dict = {}

    def getName(self):
        name = self.draw.GetName(EventsTree.controller.GetStructuredFile())
        return name

    def calculateTrianglesNumber(self):
        for s_child in self.childs:
            self.triangles_num += s_child.calculateTrianglesNumber()
        return self.triangles_num

    def calculateTimeOverhead(self, event_id, val):
        if event_id in self.childsId:
            self.time += val
            for child in self.childs:
                child.calculateTimeOverhead(event_id, val)
        return self.time

    def calculateDrawCall(self):
        return self.draw_call

    def calculateInvocation(self, event_id, val, is_vs=False):
        if (event_id in self.childsId) and (val > 0):
            if is_vs:
                self.vs_invocation += val
            else:
                self.ps_invocation += val
            for child in self.childs:
                child.calculateInvocation(event_id, val, is_vs)
        return self.vs_invocation if is_vs else self.ps_invocation

    def showShaderInformation(self):
        return ""

    def getEventInfo(self, relative_html, one_over_triangles, one_over_time, one_over_drawcall, one_over_resolution):
        name = self.getName()
        event_info = [
            # [TableHeader,         DataType,        Data,                                     bNeedSorted,  linker]
            ["EventID", "int", self.eventId, "Y", ""],
            ["Pass/State", "string", name, "N", relative_html],
            ["Triangles Num", "int", self.triangles_num, "Y", ""],
            ["N Proportion", "percentage", self.triangles_num * one_over_triangles * 100, "N", ""],
            ["Time Overhead_us", "float", self.time, "Y", ""],
            ["T Proportion", "percentage", self.time * one_over_time * 100, "N", ""],
            ["Draw Call", "int", self.draw_call, "Y", ""],
            ["DC Proportion", "percentage", self.draw_call * one_over_drawcall * 100, "N", ""],
            ["VS Invocation", "int", self.vs_invocation, "Y", ""],
            ["VSI Proportion", "float", self.vs_invocation * one_over_resolution, "N", ""],
            ["PS Invocation", "int", self.ps_invocation, "Y", ""],
            ["PSI Proportion", "float", self.ps_invocation * one_over_resolution, "N", ""]
        ]
        return event_info, False


class DrawNode(BaseNode):  # DrawCall action
    current = None

    def __init__(self, draw, parent):
        super().__init__(draw)
        self.draw_call = 1
        self.childsId.append(self.eventId)
        self.parent = parent
        self.is_last_level = True
        self.topology_type = None
        self.shaders = []
        if self.parent.first_draw_id < 0:
            self.parent.first_draw_id = self.eventId
        if self.parent.getName() == SHADER_RESOURCES_FOR_PASS:
            self.initializeShaderInformation()
            pass

    def __bindShader(self, state, shader_type, pass_name):
        shader = Shader(state, shader_type, pass_name)
        shader_hash = shader.getHandledHashValue()
        if shader_hash not in g_events_tree.shaders_hash_dict.keys():
            g_events_tree.shaders_hash_dict[shader_hash] = shader
        else:
            del shader
        return g_events_tree.shaders_hash_dict[shader_hash]

    def initializeShaderInformation(self):
        EventsTree.controller.SetFrameEvent(self.eventId, False)
        state = EventsTree.controller.GetPipelineState()
        # PrimitiveTopology
        self.topology_type = state.GetPrimitiveTopology()
        if len(self.shaders) == 0:
            # create vs shader for draw call
            vs_shader = self.__bindShader(state, "Vertex", self.parent.getName())
            # create ps shader for draw call
            ps_shader = self.__bindShader(state, "Pixel", self.parent.getName())
            self.shaders.extend([vs_shader, ps_shader])

    def updateShaderUsages(self):
        if self.parent.getName() == SHADER_RESOURCES_FOR_PASS:
            for shader in self.shaders:
                last_parent_path = list(self.parent_path_dict.values())[-1]
                ralative_path = last_parent_path.replace(".\\", "..\\Detail\\")
                shader.addUsages(self.eventId, ralative_path)

    def calculateInvocationForLights(self, event_id, val, is_valid=False, is_vs=False):
        if is_valid and (self.draw.flags & rd.ActionFlags.Drawcall) and event_id in self.childsId:
            if is_vs:
                self.vs_invocation += val
            else:
                self.ps_invocation += val
            return True
        return False

    def calculateTrianglesNumber(self):
        if USE_FASTER_TRIANGLES_COUNTER:
            # Faster way to counter triangles number
            name_str = self.getName()
            if "Indexed" in name_str:
                if "Instanced" in name_str:
                    self.triangles_num = self.draw.numIndices / 3 * self.draw.numInstances
                else:
                    self.triangles_num = self.draw.numIndices / 3
            elif "Instanced" in name_str:
                if not self.topology_type:
                    EventsTree.controller.SetFrameEvent(self.eventId, False)
                    state = EventsTree.controller.GetPipelineState()
                    self.topology_type = state.GetPrimitiveTopology()
                if self.topology_type == rd.Topology.TriangleStrip:
                    self.triangles_num = (self.draw.numIndices - 2) * max(self.draw.numInstances, 1)
                elif self.topology_type == rd.Topology.TriangleList:
                    self.triangles_num = self.draw.numIndices / 3 * max(self.draw.numInstances, 1)
            elif "Draw(" in name_str:
                self.triangles_num = (self.draw.numIndices - 2)
            else:
                self.triangles_num = 0
        # Generally
        else:
            if not self.topology_type:
                EventsTree.controller.SetFrameEvent(self.eventId, True)
                state = EventsTree.controller.GetPipelineState()
                self.topology_type = state.GetPrimitiveTopology()
            if self.topology_type == rd.Topology.TriangleStrip:
                self.triangles_num = (self.draw.numIndices - 2) * max(self.draw.numInstances, 1)
            elif self.topology_type == rd.Topology.TriangleList:
                self.triangles_num = self.draw.numIndices / 3 * max(self.draw.numInstances, 1)
            else:
                self.triangles_num = 0
        return self.triangles_num

    def outputLevel(self, markdown, indent):
        if self.level <= MAX_LEVEL_TO_SHOW and self.is_last_level:
            markdown.write(
                "<font color ='#00dd00'>%s %s &emsp; LEVEL:%d  &emsp; LAST: %d SECOND: %d (SHOW)</font>\n" % (
                    indent, self.getName(), self.level, self.is_last_level, False))
            markdown.write('<br/>')
        else:
            markdown.write('%s %u &emsp; LEVEL:%d &emsp; LAST: %d SECOND:%d\n' % (
                indent, self.getName(), self.level, self.is_last_level, False))
            markdown.write('<br/>')

    def getShadersInformation(self):
        shaders_info = []
        for shader in self.shaders:
            shaders_info.append(shader.getShaderInformation())
        return shaders_info

    def showShaderInformation(self):
        content = ""
        shader_table = Table()
        shaders_info = []
        for shader in self.shaders:
            content += shader.showBindingTextures()
            shader_info = shader.getShaderInstructions(self.html_name)
            shaders_info.append(shader_info)
        # A web page cannot have more than one table to be sorted
        content += shader_table.printTable(shaders_info, False)
        return content
        pass


class StateNode(BaseNode):
    current = None  # State : self

    def __init__(self, draw, parent):
        super().__init__(draw)
        self.parent = parent
        self.is_last_level = False
        self.is_second_last_level = True
        self.__fillinChilds()

    def __fillinChilds(self):
        if len(self.draw.children) < 1:
            self.is_last_level = True
            self.is_second_last_level = True
        for s_d in self.draw.children:
            if s_d.flags & rd.ActionFlags.Clear \
                    or s_d.flags & rd.ActionFlags.PopMarker \
                    or (s_d.flags & rd.ActionFlags.PassBoundary
                        and s_d.flags & rd.ActionFlags.CommandBufferBoundary):
                continue
            if s_d.flags & rd.ActionFlags.Drawcall:
                new_child_draw = DrawNode(s_d, self.parent)
                g_events_tree.draw_call_dict[new_child_draw.eventId] = new_child_draw
                self.draw_call += 1
                new_child_draw.level = self.level + 1
                self.is_second_last_level = False if not (
                        self.is_second_last_level and new_child_draw.is_last_level) else True
                self.childs.append(new_child_draw)
                self.childsId.append(s_d.eventId)
            else:
                new_child_state = StateNode(s_d, self.parent)
                self.childs.append(new_child_state)
                new_child_state.level = self.level + 1
                if s_d.flags & rd.ActionFlags.Dispatch \
                        or s_d.flags & rd.ActionFlags.MultiAction \
                        or s_d.flags & rd.ActionFlags.Copy:
                    # Collect children's ID
                    self.childsId.append(s_d.eventId)
                    new_child_state.is_last_level = True
                else:
                    for s_id in new_child_state.childsId:
                        self.childsId.append(s_id)
                self.draw_call += new_child_state.draw_call
                self.is_second_last_level = False if not (
                        self.is_second_last_level and new_child_state.is_last_level) else True
        self.childsId.append(self.eventId)

    def calculateInvocation(self, event_id, val, is_vs=False):
        if event_id in self.childsId:
            if is_vs:
                self.vs_invocation += val
            else:
                self.ps_invocation += val
            for child in self.childs:
                child.calculateInvocation(event_id, val, is_vs)

    def calculateInvocationForLights(self, event_id, val, is_valid=False, is_vs=False):
        result = False
        if event_id in self.childsId:
            for child in self.childs:
                if not is_valid and self.getName() != "StandardDeferredLighting":
                    result |= child.calculateInvocationForLights(event_id, val, False, is_vs)
                else:
                    result |= child.calculateInvocationForLights(event_id, val, True, is_vs)
                if result:
                    if is_vs:
                        self.vs_invocation += val
                    else:
                        self.ps_invocation += val
                    return True
        return result

    def outputLevel(self, markdown, indent):
        if self.level <= MAX_LEVEL_TO_SHOW and self.is_last_level:
            markdown.write(
                "<font color ='#00dd00'>%s %s &emsp; LEVEL:%d  &emsp; LAST: %d SECOND: %d (SHOW)</font>\n" % (
                    indent, self.getName(), self.level, self.is_last_level, self.is_second_last_level))
            markdown.write('<br/>')
        elif self.level <= MAX_LEVEL_TO_SHOW:
            markdown.write("<font>%s %s &emsp; LEVEL:%d  &emsp; LAST: %d SECOND:%d (SHOW)</font>\n" % (
                indent, self.getName(), self.level, self.is_last_level, self.is_second_last_level))
            markdown.write('<br/>')
        else:
            markdown.write('%s %u &emsp; LEVEL:%d &emsp; LAST: %d SECOND:%d\n' % (
                indent, self.getName(), self.level, self.is_last_level, self.is_second_last_level))
            markdown.write('<br/>')
        for child in self.childs:
            child.outputLevel(markdown, indent + '&emsp;&emsp;&emsp;')

    def getEventInfo(self, relative_html, one_over_triangles, one_over_time, one_over_drawcall, one_over_resolution):
        event_info, need_shader_summary_link = super().getEventInfo(relative_html, one_over_triangles, one_over_time,
                                                                    one_over_drawcall,
                                                                    one_over_resolution)
        if self.is_second_last_level and (self.parent.getName() == SHADER_RESOURCES_FOR_PASS):
            if len(self.childs) == 1 and isinstance(self.childs[0], DrawNode):
                need_shader_summary_link = True
                total_vs_textures = 0
                total_ps_textures = 0
                total_vs_instructions = 0
                total_ps_instructions = 0
                total_vs_sampling_times = 0
                total_ps_sampling_times = 0
                shaders_info = self.childs[0].getShadersInformation()
                for info in shaders_info:
                    if info[0] == rd.ShaderStage.Vertex:
                        total_vs_textures += info[1]
                        total_vs_instructions += info[2]
                        total_vs_sampling_times += info[3]
                    elif info[0] == rd.ShaderStage.Pixel:
                        total_ps_textures += info[1]
                        total_ps_instructions += info[2]
                        total_ps_sampling_times += info[3]
                event_info.extend([
                    # TableHeader      DataType    Data      bNeedSorted     linker
                    ["VS Instructions", "int", total_vs_instructions, "Y", ""],
                    ["PS Instructions", "int", total_ps_instructions, "Y", ""],
                    ["VS Sampling Times", "int", total_vs_sampling_times, "Y", ""],
                    ["PS Sampling Times", "int", total_ps_sampling_times, "Y", ""],
                    ["VS Textures", "int", total_vs_textures, "Y", ""],
                    ["PS Textures", "int", total_ps_textures, "Y", ""]
                ])
        return event_info, need_shader_summary_link


class PassNode(BaseNode):
    current = None

    def __init__(self, draw):
        super().__init__(draw)
        self.resolution_width = 0
        self.resolution_height = 0
        self.resolution_depth = 0
        self.first_draw_id = -1
        self.is_second_last_level = True
        if draw:
            self.__fillinChildren()

    def __fillinChildren(self):
        self.childsId.append(self.eventId)
        for child in self.draw.children:
            if child.flags & rd.ActionFlags.Clear \
                    or child.flags & rd.ActionFlags.PopMarker \
                    or (child.flags & rd.ActionFlags.PassBoundary
                        and child.flags & rd.ActionFlags.CommandBufferBoundary):
                continue
            if child.flags & rd.ActionFlags.Drawcall:
                self.addDraw(child)
            else:
                self.addState(child)

    def addState(self, draw):
        new_state = StateNode(draw, self)
        self.childs.append(new_state)
        self.is_second_last_level = False if not (self.is_second_last_level and new_state.is_last_level) else True
        self.draw_call += new_state.draw_call
        for c_id in new_state.childsId:
            self.childsId.append(c_id)

    def addDraw(self, draw):
        new_draw = DrawNode(draw, self)
        g_events_tree.draw_call_dict[new_draw.eventId] = new_draw
        self.is_second_last_level = False if not (self.is_second_last_level and new_draw.is_last_level) else True
        self.draw_call += 1
        self.childsId.append(draw.eventId)
        self.childs.append(new_draw)

    def calculateInvocation(self, result, invocation_desc, is_vs=False):
        pass_name = self.getName()
        if invocation_desc.resultByteWidth == 4:
            val = result.value.u32
        else:
            val = result.value.u64
        if (result.eventId in self.childsId) and (val > 0):
            if pass_name == "Lights" and ONLY_STANDARD_DEFERRED_LIGHTING_VALID:
                for child in self.childs:
                    if child.calculateInvocationForLights(result.eventId, val, is_vs):
                        if is_vs:
                            self.vs_invocation += val
                        else:
                            self.ps_invocation += val
            else:
                super().calculateInvocation(result.eventId, val, is_vs)
        return self.vs_invocation if is_vs else self.ps_invocation

    def getName(self):
        name = ""
        if self.draw:
            name = self.draw.GetName(EventsTree.controller.GetStructuredFile())
        else:
            name = "OthersPass"

        return name


# Value returned by GetRootActions()
#     GetRootActions()[0] : EndEvent
#     GetRootActions()[1] : EndEvent
#     GetRootActions()[2] : Frame XXXX
class EventsTree:
    root_frame = None
    controller = None

    def __init__(self):
        self.passes = []
        self.triangles_num = 0
        self.time = 0.0
        self.draw_call = 0
        self.ps_invocation = 0
        self.vs_invocation = 0
        self.textures_dict = {}
        self.resources_dict = {}
        self.draw_call_dict = {}
        self.shaders_hash_dict = {}

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
        self.shaders_hash_dict.clear()

    # Handle resources and collect draw call information
    def collectFrameResources(self):
        textures = EventsTree.controller.GetTextures()
        for tex in textures:
            g_events_tree.textures_dict[tex.resourceId] = tex
        resources = EventsTree.controller.GetResources()
        for res in resources:
            g_events_tree.resources_dict[res.resourceId] = res

    def addPass(self, draw):
        new_pass = PassNode(draw)
        self.passes.append(new_pass)
        PassNode.current = self.passes[-1]


g_events_tree = EventsTree()


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
def find_events_tree_entry(root):
    name = root.GetName(EventsTree.controller.GetStructuredFile())
    if str(name) == ROOT_NAME:
        return root
    for child in root.children:
        entry = find_events_tree_entry(child)
        if entry:
            return entry


def initialize_event_tree(controller):
    global g_events_tree
    # reset global events tree for tool_pass_analysis
    EventsTree.controller = controller
    g_events_tree.reset()
    g_events_tree.collectFrameResources()
    g_events_tree.root_frame = EventsTree.controller.GetRootActions()
    pass_list = []
    if ROOT_NAME == "":
        pass_list = g_events_tree.root_frame
    else:
        entry = "None"
        for item in g_events_tree.root_frame:
            entry = find_events_tree_entry(item)
            if entry:
                break
        if str(entry) == 'None':
            print("[Error] ROOT_FRAME: '%s' do not exist!Please ensure!\n" % ROOT_NAME)
            return
        pass_list = entry.children

    # Maybe some draw call in RootActions, move this events into Others
    g_events_tree.addPass(None)
    for item in pass_list:
        if len(item.children) > 1:
            g_events_tree.addPass(item)
        elif item.flags & rd.ActionFlags.Drawcall:
            g_events_tree.passes[0].addDraw(item)


def calculate_passes_attributes():
    # get counter result
    results_duration = EventsTree.controller.FetchCounters([rd.GPUCounter.EventGPUDuration])
    GPUDurationDesc = EventsTree.controller.DescribeCounter(rd.GPUCounter.EventGPUDuration)
    GPUDurationDesc.Counter = rd.CounterUnit.Seconds
    for result_d in results_duration:
        for single_pass in g_events_tree.passes:
            if result_d.eventId in single_pass.childsId:
                # change second(s) to microsecond(us)
                val = result_d.value.d * 1000000
                single_pass.calculateTimeOverhead(result_d.eventId, val)
                g_events_tree.time += val

    result_invocation = EventsTree.controller.FetchCounters([rd.GPUCounter.PSInvocations])
    PSInvocationDesc = EventsTree.controller.DescribeCounter(rd.GPUCounter.PSInvocations)
    for result_i in result_invocation:
        for single_pass in g_events_tree.passes:
            if result_i.eventId in single_pass.childsId:
                g_events_tree.ps_invocation += single_pass.calculateInvocation(result_i, PSInvocationDesc)

    result_invocation = EventsTree.controller.FetchCounters([rd.GPUCounter.VSInvocations])
    VSInvocationDesc = EventsTree.controller.DescribeCounter(rd.GPUCounter.VSInvocations)
    for result_i in result_invocation:
        for single_pass in g_events_tree.passes:
            if result_i.eventId in single_pass.childsId:
                g_events_tree.vs_invocation += single_pass.calculateInvocation(result_i, VSInvocationDesc, True)

    # Calculate other attributes of passes
    for single_pass in g_events_tree.passes:
        g_events_tree.triangles_num += single_pass.calculateTrianglesNumber()
        g_events_tree.draw_call += single_pass.calculateDrawCall()
        # get resolution of each pass
        if single_pass.first_draw_id > 0:
            EventsTree.controller.SetFrameEvent(single_pass.first_draw_id, False)
            state = EventsTree.controller.GetPipelineState()
            targets = state.GetOutputTargets()
            if len(targets) > 0:
                targetId = targets[0].resourceId
            else:
                depth_target = state.GetDepthTarget()
                targetId = depth_target.resourceId
            if targetId in g_events_tree.textures_dict.keys():
                single_pass.resolution_width = g_events_tree.textures_dict[targetId].width
                single_pass.resolution_height = g_events_tree.textures_dict[targetId].height
                single_pass.resolution_depth = g_events_tree.textures_dict[targetId].depth


def render_pie_chart(name_value_list, total_value, threshold, use_percentage, pie_title="", pie_subtitle=""):
    # Sort according to triangles number
    name_value_pair = sorted(name_value_list, key=lambda x: x[1])

    base_width = 1800
    base_height = 800
    # Remove the proportion that less than TRIANGLE_PERCENTAGE_THRESHOLD %
    i = 0
    max_length = 0
    for item in name_value_pair:
        name_length = len(item[0])
        if name_length > max_length:
            max_length = name_length
        if item[1] * total_value <= threshold:
            i += 1
    del name_value_pair[:i]
    current_length = len(name_value_pair)
    if current_length > MAX_ITEMS_TO_SHOW:
        index = current_length - MAX_ITEMS_TO_SHOW
        del name_value_pair[:index]
        pie_subtitle += ("\nToo much items!Only show top %d items." % MAX_ITEMS_TO_SHOW)

    # Resize canvas
    hscale = len(name_value_pair) / LABEL_NUMBER_IN_VIEW
    wscale = max_length / LABEL_LENGTH_IN_VIEW
    wscale = math.ceil(len(name_value_pair) / 100) * 0.25 + wscale
    pie_width = max(base_width * wscale, base_width)
    pie_height = max(base_height * hscale, base_height)

    name_value = []
    data_string = ""
    for item in name_value_pair:
        temp = [item[0], item[1]]
        name_value.append(temp)
        data_string += "'" + str(item[0]) + "':'" + str(item[2]) + "',\n"
    if use_percentage:
        label_js = r'''
        function(param){
            var total = +(__MARKER__);
            var value = param.value * total * 100.0;
            return param.name + ': ' + param.value + '\t' + value.toFixed(2) + '%';
        }
        '''.replace('__MARKER__', str(total_value))
    else:
        label_js = r'''
        function(param){
            var total = +(__MARKER__);
            var value = param.value * total;
            return param.name + ': ' + param.value + '\t' + value.toFixed(3);
        }
        '''.replace('__MARKER__', str(total_value))

    tooltip_js = r'''
    function(param){
        var dict = {
            __DATA__
        };
        var link = dict[param.name];
        window.location.href = link;
    }
    '''.replace('__DATA__', data_string)

    if len(name_value_pair) > 0:
        # Render Pie
        pie = Pie(init_opts=opts.InitOpts(theme='light',
                                          page_title="RenderDoc Analysis",
                                          renderer="svg",
                                          width=str(pie_width) + "px",
                                          height=str(pie_height) + "px"))
        pie.add("", name_value, radius=[100, 200], center=["50%", "50%"])
        pie.set_global_opts(
            title_opts=opts.TitleOpts(title=pie_title, subtitle=pie_subtitle, pos_top="5%"),
            legend_opts=opts.LegendOpts(is_show=False, orient="vertical", pos_left="left", pos_top="15%"),
            tooltip_opts=opts.TooltipOpts(trigger_on="click", formatter=(JsCode(tooltip_js)), )
        )
        # pie.set_series_opts(label_opts=opts.LabelOpts(position='top', color='black', font_family='Arial', font_size=14, formatter='{b}: {d}%'))
        pie.set_series_opts(label_opts=opts.LabelOpts(position='top', color='black', font_family='Arial', font_size=14,
                                                      formatter=(JsCode(label_js)), ))
        return pie
    else:
        return None


# Render Pies with tab type
def render_tab_chart(html_path, action_array, is_pass=False):
    global g_events_tree
    pass_time_list = []
    time_overhead = 0.0
    one_over_time = 0.0

    pass_tri_list = []
    total_num = 0
    one_over_num = 0

    pass_dc_list = []
    total_dc = 0
    one_over_dc = 0

    pass_psi_list = []
    total_psi = 0
    pass_vsi_list = []
    total_vsi = 0
    one_over_resolution = 0
    resolution = 0.001

    # Get data from each pass
    for single in action_array:
        pass_name = str(single.eventId) + "_" + single.getName()
        filename = g_detailfolder / single.html_name
        folder = g_assetsfolder if is_pass else g_detailfolder
        relative_filename = str(filename).replace(str(folder), ".")

        tup_tri = [pass_name, single.triangles_num, relative_filename]
        pass_tri_list.append(tup_tri)
        total_num += single.triangles_num

        temp_time = round(single.time, 3)
        tup_time = [pass_name, temp_time, relative_filename]
        pass_time_list.append(tup_time)
        time_overhead += temp_time

        tup_dc = [pass_name, single.draw_call, relative_filename]
        pass_dc_list.append(tup_dc)
        total_dc += single.draw_call

        if single.resolution > 0:
            tup_psi = [pass_name, single.ps_invocation, relative_filename]
            pass_psi_list.append(tup_psi)
            tup_vsi = [pass_name, single.vs_invocation, relative_filename]
            pass_vsi_list.append(tup_vsi)

        total_psi += single.ps_invocation
        total_vsi += single.vs_invocation
        resolution = single.resolution if single.resolution else total_psi

    # save total_time and total_triangles of pass
    if total_num > 0:
        one_over_num = 1 / total_num

    if time_overhead > 0.0:
        one_over_time = 1.0 / time_overhead

    if total_dc > 0:
        one_over_dc = 1 / total_dc

    if total_psi > 0:
        one_over_resolution = 1.0 / resolution

    title = "Triangles Number"
    subtitle = ("total triangles = %d" % total_num)
    pie_triangles = render_pie_chart(pass_tri_list, one_over_num, TRIANGLE_PERCENTAGE_THRESHOLD / 100.0, True, title,
                                     subtitle)

    title = "Time Overhead"
    subtitle = ("total time = %.3f us" % time_overhead)
    pie_times = render_pie_chart(pass_time_list, one_over_time, TIME_PERCENTAGE_THRESHOLD / 100.0, True, title,
                                 subtitle)

    title = "Draw Call"
    subtitle = ("total drawcall = %d" % total_dc)
    pie_dc = render_pie_chart(pass_dc_list, one_over_dc, DC_PERCENTAGE_THRESHOLD / 100.0, True, title, subtitle)

    title = "VS Invocation"
    subtitle = ("total vs invocation = %d" % total_vsi) if not is_pass else ""
    use_percentage = False if resolution else True
    pie_vsi = render_pie_chart(pass_vsi_list, one_over_resolution, INVOCATION_THRESHOLD, use_percentage, title,
                               subtitle)

    title = "PS Invocation"
    subtitle = ("total ps invocation = %d" % total_psi) if not is_pass else ""
    use_percentage = False if resolution else True
    pie_psi = render_pie_chart(pass_psi_list, one_over_resolution, INVOCATION_THRESHOLD, use_percentage, title,
                               subtitle)

    tab = Tab(page_title="RenderDoc Analysis")
    if pie_triangles:
        tab.add(pie_triangles, "Triangles")
    if pie_times:
        tab.add(pie_times, "Time")
    if pie_dc:
        tab.add(pie_dc, "DrawCall")
    if pie_vsi:
        tab.add(pie_vsi, "VS Invocation")
    if pie_psi:
        tab.add(pie_psi, "PS Invocation")
    tab.render(html_path)


# Fillin excel table
def fillin_web_page(html_path, html_title, table_content, is_top_level, action, exist_pie, need_shader_summary_link):
    html_head = (
            "<h1 style='background-color:#5cc27d; color: #FFFFFF; font-size: 40px; padding: 20px 0 5px 5px;'>%s</h1>\n" % html_title)
    if not is_top_level:
        html_head += "<font style='font-size:20px' >"
        for i, j in action.parent_path_dict.items():
            html_head += (" > <a href = %s> %s</a>" % (j, i))
        html_head += "</font>"
        html_head += "<br/><br/>"

    shader_summary_link = ""
    if need_shader_summary_link:
        if is_top_level:
            shader_summary_link = ("<h3><a href=ShaderInformation_Vertex.html>Summary of vertex shader information</a></h3>\n")
            shader_summary_link += ("<h3><a href=ShaderInformation_Pixel.html>Summary of pixel shader information</a></h3>\n")
        else:
            prefix = action.parent.getName() if isinstance(action, StateNode) else action.getName()
            shader_summary_link = ("<h3><a href=..\\Shader\\%s_Vertex.html>Vertex shader information of %s</a></h3>\n" % (prefix, prefix))
            shader_summary_link += ("<h3><a href=..\\Shader\\%s_Pixel.html>Pixel shader information of %s</a></h3>\n" % (prefix, prefix))
    html_table = ("<h2 align='center'>Analysis Data of %s:</h2>\n" % html_title)
    if is_top_level:
        html_table += (
                "<h4 align='center'>Total Triangles Number:%d &emsp;&emsp; Total Time:%.3f us &emsp;&emsp; Total Draw Call:%d </h4>\n" % (
            action.triangles_num, action.time, action.draw_call))
    else:
        one_over_resolution = 1.0 / action.resolution if action.resolution > 0 else 0
        vsi_proportion = action.vs_invocation * one_over_resolution
        psi_proportion = action.ps_invocation * one_over_resolution
        html_table += (
                "<h4 align='center'>Total Triangles Number:%d &emsp;&emsp; Total Time:%.3f us &emsp;&emsp; Total Draw Call:%d &emsp;&emsp; VS Invocation Proportion:%.3f &emsp;&emsp; PS Invocation Proportion:%.3f </h4>\n" % (
            action.triangles_num, action.time, action.draw_call, vsi_proportion, psi_proportion))
    html_table += "<h4 align='center'>Tips: You can click <i>'EnentID'</i>, <i>'Triangles Num'</i>, <i>'Time Overhead(us)'</i> and <i>'Draw Call'</i>to sort the table.</h4>\n"
    html_table += table_content

    # Combine pie chart with table
    html_content = ""
    if os.path.exists(html_path) and exist_pie:
        chart_content = open(html_path, encoding='utf-8').read()
        chart_start = chart_content.find('<body>') + 6
        chart_end = chart_content.find('</body>')
        html_content = chart_content[:chart_start] + html_head + chart_content[chart_start:chart_end] \
                       + shader_summary_link + html_table + chart_content[chart_end:]
    else:
        html_content = html_head + html_table
    html = open(html_path, "w", encoding='utf-8')
    html.write(html_content)
    html.close()


# Write top-level(Pass Level) frame······
def generate_top_level_web_page(html_name):
    global g_file_index
    html_top_path = g_assetsfolder / html_name

    # Calculate html and table_content
    one_over_triangles = 1.0 / g_events_tree.triangles_num if g_events_tree.triangles_num else 0
    one_over_time = 1.0 / g_events_tree.time if g_events_tree.time else 0
    one_over_dcs = 1.0 / g_events_tree.draw_call if g_events_tree.draw_call else 0

    # filenames = []
    passes_table = Table()
    passes_info = []
    max_event_info_len = 0
    max_event_info_row = 0
    need_shader_summary_link = False
    for p in g_events_tree.passes:
        if len(p.childs) == 0:
            continue
        # resolution
        p.resolution = p.resolution_width * p.resolution_height * p.resolution_depth
        one_over_resolution = 1.0 / p.resolution if p.resolution else 0

        # filename
        detail_name = str(p.eventId)
        detail_html_name = (detail_name + '.html')
        filename = g_detailfolder / detail_html_name
        p.html_name = detail_html_name
        relative_filename = str(filename).replace(str(g_assetsfolder), ".")
        # table
        event_info, need_link = p.getEventInfo(relative_filename, one_over_triangles, one_over_time, one_over_dcs,
                                               one_over_resolution)
        need_shader_summary_link = True
        if len(event_info) > max_event_info_len:
            max_event_info_len = len(event_info)
            max_event_info_row = g_events_tree.passes.index(p)
        passes_info.append(event_info)
    table_content = passes_table.printTable(passes_info, True, max_event_info_row)
    # Render chart
    render_tab_chart(html_top_path, g_events_tree.passes, True)
    # Fillin excel table
    fillin_web_page(html_top_path, "Top Level", table_content, True, g_events_tree, True, need_shader_summary_link)


def generate_detail_web_page(detail, to_top_path, resolution, is_pass=True):
    global g_file_index
    # Detail html filename
    detail_name = detail.getName()
    filename = g_detailfolder / detail.html_name
    relative_parent_path = str(filename).replace(str(g_detailfolder), ".")

    # path of parent to return
    detail.parent_path_dict["Top_Level"] = to_top_path
    for s in detail.childs:
        s.parent_path_dict.update(detail.parent_path_dict)
        s.parent_path_dict[str(detail.eventId) + "_" + detail_name] = relative_parent_path
        if isinstance(s, DrawNode):
            s.updateShaderUsages()

    # resolution
    one_over_resolution = 1.0 / resolution if resolution else 0

    threshold = MAX_LEVEL_TO_SHOW
    condition = True if is_pass else not detail.is_last_level
    table_content = ""
    if detail.level <= threshold and condition:
        states_table = Table()
        states_info = []
        max_event_info_len = 0
        max_event_info_row = 0
        need_shader_summary_link = False
        # Fillin excel table
        for s in detail.childs:
            child_name = str(s.eventId)
            child_html_name = (child_name + '.html')
            child_filename = g_detailfolder / child_html_name
            s.html_name = child_html_name
            relative_filename = str(child_filename).replace(str(g_detailfolder), ".")
            s.resolution = resolution
            one_over_triangles = 1 / detail.triangles_num if detail.triangles_num > 0 else 0
            one_over_time = 1 / detail.time if detail.time > 0 else 0
            one_over_dcs = 1 / detail.draw_call if detail.draw_call > 0 else 0
            if s.is_last_level or len(s.childs) == 0:
                relative_filename = ""
            # table
            event_info, need_link = s.getEventInfo(relative_filename, one_over_triangles, one_over_time, one_over_dcs,
                                                   one_over_resolution)
            need_shader_summary_link |= need_link
            if len(event_info) > max_event_info_len:
                max_event_info_len = len(event_info)
                max_event_info_row = detail.childs.index(s)
            states_info.append(event_info)
        table_content = states_table.printTable(states_info, True, max_event_info_row)
        exist_pie = False
        if not detail.is_second_last_level:
            render_tab_chart(filename, detail.childs)
            exist_pie = True
        else:
            shader_title = "<h2 align='center'>Shader Resources Infomation</h2>"
            shader_content = ""
            for s in detail.childs:
                if s.parent.getName() == SHADER_RESOURCES_FOR_PASS:
                    shader_info = s.showShaderInformation()
                    if shader_info != "":
                        shader_content += ("<h3>%d %s:</h3>" % (s.eventId, s.getName())) + shader_info + "<br/><br/>"
            table_content += "<br/>"
            if shader_content != "":
                table_content += shader_title + shader_content
        fillin_web_page(filename, ("%s" % detail_name), table_content, False, detail, exist_pie,
                           need_shader_summary_link)
        for s in detail.childs:
            generate_detail_web_page(s, to_top_path, resolution, False)


def fillin_events_tree_web_page():
    test_path = g_assetsfolder / 'EntireEventsTree.html'
    html = open(test_path, 'w', encoding='utf-8')
    html.write('<h2>Show the entire events tree:</h2>\n')
    for single_pass in g_events_tree.passes:
        html.write('<br/>')
        if single_pass.level <= MAX_LEVEL_TO_SHOW:
            html.write("<h4>%s &emsp; LEVEL:%d SECOND:%d(SHOW)\n</h4>" % (
                single_pass.getName(), single_pass.level, single_pass.is_second_last_level))
        else:
            html.write('<h4>%s  LEVEL:%d</h4>\n' % (single_pass.getName(), single_pass.level))
        html.write('<br/>')
        for single_state in single_pass.childs:
            single_state.outputLevel(html, '&emsp;&emsp;&emsp;')
        html.write('<br/>')
    html.close()


def collect_current_shader(vs_shaders_info, ps_shaders_info):
    for shader in g_events_tree.shaders_hash_dict.values():
        if shader.pass_name == SHADER_RESOURCES_FOR_PASS:
            shader_info_append = [
                ["Textures Num", "int", shader.getTexturesNum(), "Y", ""],
                ["Usage", "string", shader.getUsages(), "N", ""]
            ]
            info = shader.getShaderInformation()
            shader_info = shader.getShaderInstructions("")
            shader_info.extend(shader_info_append)
            if info[0] == rd.ShaderStage.Vertex:
                vs_shaders_info.append(shader_info)
            elif info[0] == rd.ShaderStage.Pixel:
                ps_shaders_info.append(shader_info)
    pass


def fillin_current_shader_web_page(shaders_info, shader_type):
    shader_table = Table()
    curr_content = shader_table.printTable(shaders_info, True)
    # save shader information of current pass into "Shader" folder
    pass_html_path = g_shaderfolder / ("%s_%s.html" % (SHADER_RESOURCES_FOR_PASS, shader_type))
    pass_html = open(pass_html_path, 'w', encoding='utf-8')
    pass_html.write(
            "<h1 style='background-color:#5cc27d; color: #FFFFFF; font-size: 40px; padding: 20px 0 5px 5px;'>%s_%s Shader Information</h1>\n" % (SHADER_RESOURCES_FOR_PASS, shader_type))
    pass_html.write("<h3><a href=..\\ShaderInformation_%s.html>Summary of shader information</a></h3>\n" % shader_type)
    pass_html.write(curr_content)
    pass_html.close()
    return curr_content


# Read content of file in "Shader" folder
def read_reserved_shader_file(shader_type):
    files = os.listdir(g_shaderfolder)
    reserved_content = ""
    for file in files:
        if not os.path.isdir(file) and file.endswith("_%s.html" % shader_type):
            f = open(str(g_shaderfolder) + "/" + file, "r")
            iter_f = iter(f)
            file_str = ""
            for line in iter_f:
                if line.startswith("<tr><td "):
                    line_handle = line.replace("<a href=..\Detail", "<a href=Detail")
                    line_handle2 = line_handle.replace("<a href=..\Shader", "<a href=Shader")
                    file_str = file_str + line_handle2
            reserved_content += file_str
    return reserved_content


# Write summary of shaders information implement
def fillin_top_shader_web_page(shaders_info, shader_type):
    # Update shader information of current pass
    current_content = fillin_current_shader_web_page(shaders_info, shader_type)
    # Read htmls in "Shader" folder
    reserved_content = read_reserved_shader_file(shader_type)

    # Insert reserved_content into row1 of table
    start_pos = current_content.find("</tr>\n") + 6
    end_pos = current_content.rfind("</tr>")
    content = current_content[:start_pos] + reserved_content + current_content[end_pos:]
    # fillin summary shader information into ShaderInformation_Vertex/Pixel.html
    html_path = g_assetsfolder / ("ShaderInformation_%s.html" % shader_type)
    html = open(html_path, 'w', encoding='utf-8')
    html.write(
        "<h1 style='background-color:#5cc27d; color: #FFFFFF; font-size: 40px; padding: 20px 0 5px 5px;'>%s Shader Information</h1>\n" % shader_type)
    html.write('<h2>Show the %s shader information:</h2>\n' % shader_type.lower())
    html.write(content)
    html.close()


# Write summary of shaders information
def generate_shader_web_pages():
    # Collect current shader information
    vs_shaders_info = []
    ps_shaders_info = []
    collect_current_shader(vs_shaders_info, ps_shaders_info)
    # fillin htmls of shader information
    fillin_top_shader_web_page(vs_shaders_info, "Vertex")
    fillin_top_shader_web_page(ps_shaders_info, "Pixel")


def update_shader_information_for_pass():
    to_top_path = "../" + 'TopLevelAnalysis.html'
    for single in g_events_tree.passes:
        if single.getName() == SHADER_RESOURCES_FOR_PASS:
            resolution = single.resolution_width * single.resolution_height * single.resolution_depth
            if isinstance(single, PassNode):
                for child_id in single.childsId:
                    if child_id in g_events_tree.draw_call_dict.keys():
                        child_draw = g_events_tree.draw_call_dict[child_id]
                        child_draw.initializeShaderInformation()
            generate_detail_web_page(single, to_top_path, resolution)
    generate_shader_web_pages()
    pass


# Write variable htmls
def generate_web_page_overview(controller):
    # Build events tree
    initialize_event_tree(controller)
    # Collect attributes of passes
    calculate_passes_attributes()

    # Path of frame
    html_name = 'TopLevelAnalysis.html'
    # Print frame's information
    generate_top_level_web_page(html_name)
    for single in g_events_tree.passes:
        if len(single.childs) == 0:
            continue
        to_top_path = "../" + html_name
        resolution = single.resolution_width * single.resolution_height * single.resolution_depth
        generate_detail_web_page(single, to_top_path, resolution)

    # Print shaders' information
    generate_shader_web_pages()
    # Output events tree frame
    fillin_events_tree_web_page()
    print("Finished!")


def create_result_folder():
    global g_absoulte
    global g_assetsfolder
    global g_detailfolder
    global g_shaderfolder
    g_absoulte = WindowsPath(RDC_FILE).absolute()
    file_name = g_absoulte.stem + "_Report"
    g_assetsfolder = g_absoulte.parent / file_name
    print("File Path:%s\n" % g_assetsfolder)
    g_assetsfolder.mkdir(parents=True, exist_ok=True)
    g_detailfolder = g_assetsfolder / 'Detail'
    # Create folder to save shader information
    g_shaderfolder = g_assetsfolder / 'Shader'
    if not KEEP_PREVIOUS_SHADER_INFO:
        if os.path.exists(g_detailfolder):
            shutil.rmtree(g_detailfolder)
        if os.path.exists(g_shaderfolder):
            shutil.rmtree(g_shaderfolder)
    g_detailfolder.mkdir(parents=True, exist_ok=True)
    g_shaderfolder.mkdir(parents=True, exist_ok=True)


def load_capture(filename):
    rd.InitialiseReplay(rd.GlobalEnvironment(), [])
    # Open a capture file handle
    cap = rd.OpenCaptureFile()
    # Open a particular file - see also OpenBuffer to load from memory
    result = cap.OpenFile(filename, '', None)
    # Make sure the file opened successfully
    if result != rd.ResultCode.Succeeded:
        raise RuntimeError("Couldn't open file: " + str(result))
    # Make sure we can replay
    if not cap.LocalReplaySupport():
        raise RuntimeError("Capture cannot be replayed")
    # Initialise the replay
    result, controller = cap.OpenCapture(rd.ReplayOptions(), None)
    if result != rd.ResultCode.Succeeded:
        raise RuntimeError("Couldn't initialise replay: " + str(result))
    return cap, controller


def main():
    global RDC_FILE
    if 'pyrenderdoc' in globals():
        if RDC_FILE == "":
            RDC_FILE = pyrenderdoc.GetCaptureFilename()
        else:
            pyrenderdoc.LoadCapture(RDC_FILE, rd.ReplayOptions(), RDC_FILE, False, True)
        create_result_folder()
        pyrenderdoc.Replay().BlockInvoke(generate_web_page_overview)
    else:
        if len(sys.argv) <= 1:
            print('Usage: python3 {} filename.rdc'.format(sys.argv[0]))
            sys.exit(0)
        create_result_folder()
        cap, controller = load_capture(sys.argv[1])  # sys.argv[1] == filePath
        generate_web_page_overview(controller)

        controller.Shutdown()
        cap.Shutdown()
        rd.ShutdownReplay()


if __name__ == "__main__":
    main()
    pass
