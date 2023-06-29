# RenderDoc Python console, powered by python 3.6.4.
# The 'pyrenderdoc' object is the current CaptureContext instance.
# The 'renderdoc' and 'qrenderdoc' modules are available.
# Documentation is available: https://renderdoc.org/docs/python_api/index.html


# Local Path of Python36
LOCAL_PYTHON36_PATH = 'E:\\python3.6'

# ROOT_NAME =""  =>  all passes in the same level of "Capture Start"
ROOT_NAME = "Scene"    
# The name of 'Position' attribute in VSInput
VS_INPUT_POSITION_NAME = "ATTRIBUTE0"
# Whether to count drawcall which do not has name 
INCLUDE_CHILDREN_WITHOUT_NAME = False
PASSES_EXCLUDED = ["BeginOcclusionTests", "Lights"]

# Used to open exist rdc file
RDC_FILE = ""

# config of pie chart
DRAWCALL_THRESHOLD = 2 # Drawcall >= 2 will be show
MAX_ITEMS_TO_SHOW = 1000 
LABEL_LENGTH_IN_VIEW = 90
LABEL_NUMBER_IN_VIEW = 60  

from pathlib import WindowsPath
import sys
import os
import shutil
import math
import struct
import operator
import string
import re


#import pyechart 
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
            var td0s=document.getElementsByName("td0");
            var td1s=document.getElementsByName("td1");
            var td2s=document.getElementsByName("td2");
            var td3s=document.getElementsByName("td3");
            var tdArray0=[];
            var tdArray1=[];
            var tdArray2=[];
            var tdArray3=[];
            for(var i=0;i<td0s.length;i++){
                tdArray0.push(parseInt(td0s[i].innerHTML));
            }
            for(var i=0;i<td1s.length;i++){
                tdArray1.push(td1s[i].innerHTML);
            }
            for(var i=0;i<td2s.length;i++){
                tdArray2.push(parseInt(td2s[i].innerHTML));
            }
            for(var i=0;i<td3s.length;i++){
                tdArray3.push(td3s[i].innerHTML);
            }
            var tds=document.getElementsByName("td"+obj.id.substr(2,1));
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
                        document.getElementsByName("td0")[i].innerHTML=tdArray0[j];
                        document.getElementsByName("td1")[i].innerHTML=tdArray1[j];
                        document.getElementsByName("td2")[i].innerHTML=tdArray2[j];
                        document.getElementsByName("td3")[i].innerHTML=tdArray3[j];
                        orginArray[j]=null;
                        break;
                    }
                }
            }
        }
 
    </script>
'''


mesh_dc_table_head = '''
<tr bgcolor= c0c0c0>
    <th id='th0' onclick='SortTable(this)' class='desc'>EventID</th>
    <th>Mesh Name</th>
    <th id='th2' onclick='SortTable(this)' class='desc'>Draw Call</th>
    <th>T Proportion</th>
</tr>\n'''


mesh_detail_table_head ='''
<tr bgcolor= c0c0c0>
    <th>EventID</th>
    <th>Belong To</th>
</tr>\n'''


class DrawCall:
    def __init__(self, draw, name, pass_name):
        self.draw = draw
        self.eventId = draw.eventId
        self.numIndices = self.draw.numIndices
        self.numInstances = self.draw.numInstances
        self.parent_name = name
        self.pass_name = pass_name
        self.actor_name = ""
        self.mesh_name = ""
        self.dealWithName()
    
    def dealWithName(self):
        #Calculate actor_name
        start_idx = 0
        end_idx = 0
        if self.parent_name !=  "":
            start_idx = self.parent_name.find(' ') + 1
            if start_idx > 0 and start_idx < len(self.parent_name):
                end_idx = self.parent_name.find(' ', start_idx)
                if end_idx > 0:
                    self.actor_name = self.parent_name[start_idx:end_idx]
                    self.parent_name = self.parent_name[:end_idx]
                else:
                    self.actor_name = self.parent_name[start_idx:] 
                # if actor_name = 1080x1920(resolution) or '(PS)'
                matchObj = re.match( r'^([0-9]+)x([0-9]+)', self.actor_name, re.I)
                if matchObj is not None or self.actor_name == "(PS)":
                    self.actor_name = self.parent_name 
                #Remove the influence of Actorname's ID  (exp:Actor's IDname is Actor_1) 
                self.mesh_name = self.actor_name.rstrip(string.digits)
                last_index = len(self.mesh_name) -1
                if self.mesh_name[last_index] == "_":
                    num = len(self.mesh_name)
                    self.mesh_name = self.mesh_name[:num-1]
            else:
               self.actor_name = self.parent_name  
               self.mesh_name = self.parent_name
            
        #Remove illegal character in parent_name
        intab = '\/:*?"<>| '
        outtab = '__________'
        name = self.actor_name
        trantab = name.maketrans(intab, outtab)
        self.actor_name = name.translate(trantab)   


class MeshData(rd.MeshFormat):
    indexOffset = 0
    name = ''


class Mesh:
    def __init__(self, drawcall, name):
        self.name = name
        self.mesh_name = drawcall.mesh_name
        self.show_name = drawcall.parent_name + " (" + str(drawcall.numIndices) + ")"
        self.mesh_data = []    #List of vertex attribute (value: SV_POSITION)
        self.indices_data = []    #List of vertex attribute (value: SV_POSITION)
        self.eventId = drawcall.eventId #First Appear Action's EventId
        self.IDs = []
        self.IDs.append(self.eventId)
        self.passes_name = [drawcall.pass_name]
        self.drawcall = 1
        self.draw = drawcall.draw
        self.html_name = str(self.eventId) + ".html"
        self.relative_filename = str(self.eventId) + ".html"
    def __lt__(self,other):
        return self.drawcall > other.drawcall

    def updateMeshData(self, item):
        self.drawcall += 1
        self.IDs.append(item.eventId)
        self.passes_name.append(item.pass_name)


# ============ Global Values =================================
dc_list = [] #all drawcall actions
name_meshes_dict = {} #{ name_numIndices : [Meshes] }
mesh_list = []
total_drawcall = 0
g_file_index = 0
filenames = []
# ============================================================


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
def find_events_tree_entry(controller, root):
    name = root.GetName(controller.GetStructuredFile())
    if str(name) == ROOT_NAME:
        return root
    for child in root.children:
        entry = find_events_tree_entry(controller, child)
        if entry:
            return entry


def iterator_actions(item, controller, pass_name):
    global dc_list    
    global total_drawcall    
    for child in item.children:  
        if child.flags & rd.ActionFlags.Drawcall:
            total_drawcall += 1
            condition = True
            if not INCLUDE_CHILDREN_WITHOUT_NAME:
                condition = len(item.children) < 3
            if condition:
                parent_name = item.GetName(controller.GetStructuredFile())
                new_dc = DrawCall(child, parent_name, pass_name)
                dc_list.append(new_dc)
        iterator_actions(child, controller, pass_name)   


def collect_drawcall_actions(controller):
    global dc_list  
    global total_drawcall    
    root_frame = controller.GetRootActions()
    root_list = []
    entry =""
    if ROOT_NAME == "":
        root_list = root_frame
    else:
        for item in root_frame:
            entry = find_events_tree_entry(controller, item)  
            if entry:
                break
        if str(entry) == 'None':
            print("[Error] ROOT_FRAME: '%s' do not exist!Please ensure!\n" % ROOT_NAME)
            return
        root_list = entry.children

    for child in root_list:                            #?TODO? remove some passes that do not focus     
        pass_name = child.GetName(controller.GetStructuredFile())
        if child.flags & rd.ActionFlags.Drawcall:
            total_drawcall += 1
            condition = True
            if not INCLUDE_CHILDREN_WITHOUT_NAME:
                condition = len(root_list) < 3
            if condition:
                new_dc = DrawCall(child, "OthersPass", "OthersPass")
                dc_list.append(new_dc)
        iterator_actions(child, controller, pass_name)


# Get a list of MeshData objects describing the vertex inputs at this draw
def get_mesh_inputs(controller, mesh):
    controller.SetFrameEvent(mesh.eventId, False)
    state = controller.GetPipelineState()
    draw = mesh.draw

    # Get the index & vertex buffers, and fixed vertex inputs
    ib = state.GetIBuffer()
    vbs = state.GetVBuffers()
    attrs = state.GetVertexInputs()
    meshInputs = []

    for attr in attrs:
        # We don't handle instance attributes
        if attr.perInstance:
            #raise RuntimeError("Instanced properties are not supported!")
            return meshInputs

        meshInput = MeshData()
        meshInput.indexResourceId = ib.resourceId
        meshInput.indexByteOffset = ib.byteOffset
        meshInput.indexByteStride = ib.byteStride
        meshInput.baseVertex = draw.baseVertex
        meshInput.indexOffset = draw.indexOffset
        meshInput.numIndices = draw.numIndices

        # If the draw doesn't use an index buffer, don't use it even if bound
        if not (draw.flags & rd.ActionFlags.Indexed):
            meshInput.indexResourceId = rd.ResourceId.Null()

        # The total offset is the attribute offset from the base of the vertex
        meshInput.vertexByteOffset = attr.byteOffset + vbs[attr.vertexBuffer].byteOffset + draw.vertexOffset * vbs[attr.vertexBuffer].byteStride
        meshInput.format = attr.format
        meshInput.vertexResourceId = vbs[attr.vertexBuffer].resourceId
        meshInput.vertexByteStride = vbs[attr.vertexBuffer].byteStride
        meshInput.name = attr.name
        meshInputs.append(meshInput)
    return meshInputs


def get_indices(controller, mesh):
    # Get the character for the width of index
    indexFormat = 'B'
    if mesh.indexByteStride == 2:
        indexFormat = 'H'
    elif mesh.indexByteStride == 4:
        indexFormat = 'I'
    # Duplicate the format by the number of indices
    indexFormat = str(mesh.numIndices) + indexFormat
    # If we have an index buffer
    if mesh.indexResourceId != rd.ResourceId.Null():
        # Fetch the data
        ibdata = controller.GetBufferData(mesh.indexResourceId, mesh.indexByteOffset, 0)
        # Unpack all the indices, starting from the first index to fetch
        offset = mesh.indexOffset * mesh.indexByteStride
        indices = struct.unpack_from(indexFormat, ibdata, offset)
        # Apply the baseVertex offset
        return [i + mesh.baseVertex for i in indices]
    else:
        # With no index buffer, just generate a range
        return tuple(range(mesh.numIndices))
    pass


def unpack_data(fmt, data):
    # We don't handle 'special' formats - typically bit-packed such as 10:10:10:2
    if fmt.Special():
        raise RuntimeError("Packed formats are not supported!")

    formatChars = {}
    #                                 012345678
    formatChars[rd.CompType.UInt]  = "xBHxIxxxL"
    formatChars[rd.CompType.SInt]  = "xbhxixxxl"
    formatChars[rd.CompType.Float] = "xxexfxxxd" # only 2, 4 and 8 are valid

    # These types have identical decodes, but we might post-process them
    formatChars[rd.CompType.UNorm] = formatChars[rd.CompType.UInt]
    formatChars[rd.CompType.UScaled] = formatChars[rd.CompType.UInt]
    formatChars[rd.CompType.SNorm] = formatChars[rd.CompType.SInt]
    formatChars[rd.CompType.SScaled] = formatChars[rd.CompType.SInt]

    # We need to fetch compCount components
    vertexFormat = str(fmt.compCount) + formatChars[fmt.compType][fmt.compByteWidth]

    # Unpack the data
    value = struct.unpack_from(vertexFormat, data, 0)

    # If the format needs post-processing such as normalisation, do that now
    if fmt.compType == rd.CompType.UNorm:
        divisor = float((2 ** (fmt.compByteWidth * 8)) - 1)
        value = tuple(float(i) / divisor for i in value)
    elif fmt.compType == rd.CompType.SNorm:
        maxNeg = -float(2 ** (fmt.compByteWidth * 8)) / 2
        divisor = float(-(maxNeg-1))
        value = tuple((float(i) if (i == maxNeg) else (float(i) / divisor)) for i in value)

    # If the format is BGRA, swap the two components
    if fmt.BGRAOrder():
        value = tuple(value[i] for i in [2, 1, 0, 3])
    return value


def compare_mesh_data(controller, indicesA, indicesB, dataA, dataB):
    if len(indicesA) != len(indicesB):
        return False

    # Compare vertex0 ~ vertex3(The First Triangle)
    for i in range(0, 3):
        idxA = indicesA[i]
        idxB = indicesB[i]
        if idxA != idxB:
            return False
        for attr1 in dataA: 
            if attr1.name == VS_INPUT_POSITION_NAME:
                offset1 = attr1.vertexByteOffset + attr1.vertexByteStride * idxA
                data1 = controller.GetBufferData(attr1.vertexResourceId, offset1, 0)
                # Get the value from the data
                valueA = unpack_data(attr1.format, data1)
                for attr2 in dataB: 
                    if attr2.name == VS_INPUT_POSITION_NAME:
                        offset2 = attr2.vertexByteOffset + attr2.vertexByteStride * idxB
                        data2 = controller.GetBufferData(attr2.vertexResourceId, offset2, 0)
                        # Get the value from the data
                        valueB = unpack_data(attr2.format, data2)
                        result = operator.eq(valueA, valueB)
                        if not result:
                            return False
    return True


def calculate_mesh_drawcall(controller):
    instances_list = []
    remain_isntances ={}
    for item in dc_list:
        if item.pass_name in PASSES_EXCLUDED:
            continue
        # Handled actions(numInstances >1) later
        if item.numInstances > 1:
            instances_list.append(item)
            continue

        name = item.actor_name + " (" + str(item.numIndices) + ")"
        # Both name and numIndices of mesh are the same, compare their 'Position' in VS_Input
        if name in name_meshes_dict.keys():
            meshes_list = name_meshes_dict[name]
            new_mesh_data = get_mesh_inputs(controller, item)
            new_mesh_indices = get_indices(controller, new_mesh_data[0])  #Save indices data
            b_handled = False
            for mesh in meshes_list:
                # mesh_data of mesh is null, attach mesh_data!
                if len(mesh.mesh_data) == 0: 
                    mesh_data = get_mesh_inputs(controller, mesh)
                    mesh_indices = get_indices(controller, mesh_data[0])  #Save indices data
                    mesh.mesh_data = mesh_data
                    mesh.indices_data = mesh_indices
                if compare_mesh_data(controller, new_mesh_indices, mesh.indices_data, new_mesh_data, mesh.mesh_data):
                    mesh.updateMeshData(item)
                    b_handled = True
            if not b_handled:
                new_mesh = Mesh(item, name)
                new_mesh.mesh_data = new_mesh_data 
                new_mesh.indices_data = new_mesh_indices
                name_meshes_dict.get(name).append(new_mesh)
                mesh_list.append(new_mesh) 
        else: 
            new_mesh = Mesh(item, name)
            name_meshes_dict[name] = [new_mesh] 
            mesh_list.append(new_mesh)

    # Handled actions whose numInstances >1
    name_instances_dict = {}
    for instance in instances_list:       
        b_handled = False
        name = instance.actor_name + " (" + str(instance.numIndices) + ")"
        if name in name_meshes_dict.keys() or name in name_instances_dict.keys():
            new_mesh_data = get_mesh_inputs(controller, instance)
            new_mesh_indices = get_indices(controller, new_mesh_data[0])  #Save indices data
            list = name_meshes_dict[name] if name in name_meshes_dict.keys() else name_instances_dict[name]
            for mesh in list:
                if len(mesh.mesh_data) == 0: 
                    mesh_data = get_mesh_inputs(controller, mesh)
                    mesh_indices = get_indices(controller, mesh_data[0])  #Save indices data
                    mesh.mesh_data = mesh_data
                    mesh.indices_data = mesh_indices
                    if compare_mesh_data(controller, new_mesh_indices, mesh.indices_data, new_mesh_data, mesh.mesh_data):
                        mesh.updateMeshData(instance)
                        instance.numInstances -= mesh.draw.numInstances
                        if instance.numInstances < 0:                         
                            print("Something wrong in instance: %s, EventId: %d" % (name, instance.eventId))
                        b_handled = True
        else:
            for dict_name, dict_meshes in name_meshes_dict.items(): 
                if instance.mesh_name in dict_name:
                    for mesh in dict_meshes:
                        num_index_name = "(" + str(instance.numIndices) + ")"
                        # A mesh cannot execute both drawIndexed and drawInstanced in the same Pass
                        #[TODO]:need stricter rules 
                        if mesh.name.endswith(num_index_name) and mesh.mesh_name.startswith(instance.mesh_name) and instance.pass_name not in mesh.passes_name:
                            mesh.updateMeshData(instance)
                            instance.numInstances -= 1
                            b_handled = True
                            if instance.numInstances < 0:
                                print("Something wrong in instance: %s, EventId: %d\n\n" % (name, instance.eventId))
            if instance.numInstances>0 and b_handled:
                remain_isntances[instance] = instance.numInstances
        if not b_handled:
            new_mesh = Mesh(instance, name)
            name_instances_dict[name] = [new_mesh] 
            mesh_list.append(new_mesh)

    # Special case 2: drawInstanced(2) in some passes, others drawIndexed(1)、 drawIndexed(1) and drawInstanced(2)
    for remain_instance in remain_isntances.keys():
        for name, instance_meshes in name_instances_dict.items():
            for instance_mesh in instance_meshes:
                if remain_instance.mesh_name in name and remain_instance.numIndices == instance_mesh.draw.numIndices and remain_isntances[remain_instance] >= instance_mesh.draw.numInstances:
                    instance_mesh.updateMeshData(remain_instance)
                    remain_isntances[remain_instance] -= instance_mesh.draw.numInstances


def render_pie_chart(name_value_list, total_value, mesh_dc_path):
    # Sort according to triangles number
    name_value_pair = sorted(name_value_list, key=lambda x:x[1])
    base_width = 1800
    base_height = 800

    # Remove the proportion that less than TRIANGLE_PERCENTAGE_THRESHOLD % 
    i = 0
    max_length = 0

    title = "mesh drawcall"
    subtitle = ("Total drawcall = %d\nOnly show drawcall >= %d" % (total_drawcall, DRAWCALL_THRESHOLD))
 
    for item in name_value_pair:
        name_length = len(item[0])
        if name_length > max_length:
            max_length = name_length
        if(item[1] < DRAWCALL_THRESHOLD):
            i+= 1
    del name_value_pair[:i]
    current_length = len(name_value_pair)
    if current_length > MAX_ITEMS_TO_SHOW:
        index = current_length - MAX_ITEMS_TO_SHOW
        del name_value_pair[:index]
        subtitle +=("\nToo much items!Only show top %d items." % MAX_ITEMS_TO_SHOW)
    
    # Resize canvas
    hscale= len(name_value_pair) / LABEL_NUMBER_IN_VIEW
    wscale= max_length / LABEL_LENGTH_IN_VIEW
    wscale = math.ceil(len(name_value_pair) / 100) * 0.25 + wscale
    pie_width = max(base_width * wscale, base_width)
    pie_height = max(base_height * hscale, base_height)
    
    name_value = []
    data_string = ""
    for item in name_value_pair:
        temp= []
        temp.append(item[0])
        temp.append(item[1])
        name_value.append(temp)
        data_string += "'" + str(item[0]) + "':'" + str(item[2]) + "',\n"
        
    label_js = r'''
    function(param){
        var total = +(__MARKER__);
        var value = param.value * total * 100.0;
        return param.name + ': ' + param.value + '\t' + value.toFixed(2) + '%';
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
    
    if len(name_value_pair)>0:
        # Render Pie
        pie = Pie(init_opts=opts.InitOpts(theme='light',
                                          page_title="RenderDoc Analysis",
                                          renderer="svg",
                                          width=str(pie_width) + "px",
                                          height=str(pie_height) + "px"))
        pie.add("", name_value, radius=[100, 200], center=["50%", "50%"])
        pie.set_global_opts(
            title_opts=opts.TitleOpts(title=title, subtitle=subtitle, pos_top="5%"),
            legend_opts=opts.LegendOpts(is_show=False, orient="vertical", pos_left="left", pos_top = "15%"),
            tooltip_opts=opts.TooltipOpts(trigger_on = "click", formatter=(JsCode(tooltip_js)),)
        )
        pie.set_series_opts(label_opts=opts.LabelOpts(position='top', color='black', font_family='Arial', font_size=14, formatter=(JsCode(label_js)), ))
        pie.render(mesh_dc_path) 


# Fillin excel table 
def fillin_excel_table(html_path, html_title, table_content, is_top_level, total_drawcall):
    html_head = ("<h1 style='background-color:#5cc27d; color: #FFFFFF; font-size: 40px; padding: 20px 0 5px 5px;'>%s</h1>\n" % html_title)
           
    html_table = ("<h3 align='center'>Analysis Data of %s:</h3>\n" % html_title)
    if is_top_level:
        html_table += ("<h4 align='center'>Total Drawcall:%d</h4>\n" % (total_drawcall))
    else:
        html_table += ("<h4 align='center'>Mesh Name:%s &emsp;&emsp; Total Draw Call:%d </h4>\n" % (html_title, total_drawcall))
    html_table += "<h4 align='center'>Tips: You can click <i>'EnentID'</i> or <i>'Draw Call'</i>to sort the table.</h4>\n" if is_top_level else ""
    html_table += table_sort_function if is_top_level else ""
    html_table += "<table border=1 cellpadding=10 cellspacing=0 align='center'>\n"
    html_table += mesh_dc_table_head if is_top_level else mesh_detail_table_head
    html_table += table_content

    # Combine pie chart with table
    html_content = ""
    if os.path.exists(html_path):
        chart_content = open(html_path, encoding='utf-8').read()
        chart_start = chart_content.find('<body>') + 6  
        chart_end = chart_content.find('</body>')
        html_content = chart_content[:chart_start]+ html_head + chart_content[chart_start:chart_end]+ html_table + chart_content[chart_end:]
    else:
        html_content = html_head + html_table 
    html = open(html_path, "w",encoding='utf-8')
    html.write(html_content)
    html.close()


def calculate_relative_html_name(item):
    global filenames
    global g_file_index
    detail_name = str(item.eventId)
    detail_html_name = (detail_name + '.html')
    filename = g_detailfolder / detail_html_name
    if os.path.exists(filename) or filename in filenames:  
        detail_html_name = (detail_name + "_" + str(g_file_index) + '.html')
        filename = g_detailfolder / detail_html_name
        g_file_index += 1
    item.html_name = filename
    filenames.append(filename)
    relative_filename = str(filename).replace(str(g_assetsfolder), ".")
    return relative_filename


def write_mesh_data_frame():
    mesh_dc_path = g_assetsfolder /'MeshDrawCall.html'
    one_over_drawcall = 0
    if total_drawcall > 0:
        one_over_drawcall = 1 / total_drawcall

    name_dc_list = []
    table_content = ''
    #Sort mesh list according to drawcall
    mesh_list.sort()

    for mesh in mesh_list:
        #Calculate html link
        mesh.relative_filename = calculate_relative_html_name(mesh)
        table_content += ("<tr><td name='td0'>%d</td><td name='td1'><a href='%s'>%s</a></td><td name='td2'>%d</td><td name='td3'>%.2f %%</td>\n" %
                           (mesh.eventId, mesh.relative_filename, mesh.show_name, mesh.drawcall, (mesh.drawcall * one_over_drawcall *100)))
     
        #Collect information of mesh
        temp = []
        label_name = str(mesh.eventId) + " " + mesh.show_name
        temp.append(label_name)
        temp.append(mesh.drawcall)
        temp.append(mesh.relative_filename)
        name_dc_list.append(temp)

    # Render pie chart
    render_pie_chart(name_dc_list, one_over_drawcall, mesh_dc_path)
    # Fillin excel table
    fillin_excel_table(mesh_dc_path, "Mesh Drawcall Analysis", table_content, True, total_drawcall)


def write_mesh_detail_frame(detail):
    global g_file_index
    filename = detail.html_name

    table_content = ""
    index = 0
    for id in detail.IDs:
        pass_name = detail.passes_name[index]
        index += 1
        table_content += ("<tr><td>%d</td><td>%s</td></tr>\n" % (id, pass_name))
    fillin_excel_table(filename, ("%s" % detail.show_name), table_content, False, detail.drawcall)


# Write variable htmls
def write_frame_overview(controller):
    # collect all drawcall actions
    collect_drawcall_actions(controller)
    # calculate mesh drawcall
    calculate_mesh_drawcall(controller)
    
    write_mesh_data_frame()
    for mesh in mesh_list:
        write_mesh_detail_frame(mesh)
    # Ending tip
    print("Finished!")


def create_result_folder():
    global g_absoulte
    global g_assetsfolder
    global g_detailfolder
    g_absoulte = WindowsPath(RDC_FILE).absolute()
    file_name = g_absoulte.stem + "_MeshReport"
    g_assetsfolder = g_absoulte.parent / file_name
    print("File Path:%s\n" % g_assetsfolder)
    g_assetsfolder.mkdir(parents=True, exist_ok=True)
    g_detailfolder = g_assetsfolder / 'Detail'
    if os.path.exists(g_detailfolder):
        shutil.rmtree(g_detailfolder)
    g_detailfolder.mkdir(parents=True, exist_ok=True)


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
    result,controller = cap.OpenCapture(rd.ReplayOptions(), None)
    if result != rd.ResultCode.Succeeded:
        raise RuntimeError("Couldn't initialise replay: " + str(result))
    return cap,controller


def main():
    global RDC_FILE
    if 'pyrenderdoc' in globals():
        if RDC_FILE == "":
            RDC_FILE = pyrenderdoc.GetCaptureFilename()
        else:
            pyrenderdoc.LoadCapture(RDC_FILE, rd.ReplayOptions(), RDC_FILE, False, True)
        create_result_folder()
        pyrenderdoc.Replay().BlockInvoke(write_frame_overview)
    else:
        if len(sys.argv) <= 1:
            print('Usage: python3 {} filename.rdc'.format(sys.argv[0]))
            sys.exit(0)
        create_result_folder()
        cap, controller = load_capture(sys.argv[1])  # sys.argv[1] == filePath
        write_frame_overview(controller)

        controller.Shutdown()
        cap.Shutdown()
        rd.ShutdownReplay()


if __name__ == "__main__":
    main()
    pass