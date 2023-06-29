# -*- coding:UTF-8 -*-
import math
import pickle
import os.path
import sys
from typing import Optional
from pyecharts.charts import Pie
from pyecharts.charts import Tab
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode
from event_tree import EventsTree
from table import Table

# Config of pie chart
MAX_LEVEL_TO_SHOW = 10
MAX_ITEMS_TO_SHOW = 1000
LABEL_LENGTH_IN_VIEW = 90
LABEL_NUMBER_IN_VIEW = 55

ONLY_STANDARD_DEFERRED_LIGHTING_VALID = True
TRIANGLE_PERCENTAGE_THRESHOLD = 0.01  # 0.01%
TIME_PERCENTAGE_THRESHOLD = 0.01  # 0.01%
DC_PERCENTAGE_THRESHOLD = 0.01  # 0.01%
INVOCATION_THRESHOLD = 0.001

SHADER_RESOURCES_FOR_PASS = "None"

# Globals load from pickle
g_file_index = 0
g_events_tree: Optional[EventsTree] = None
g_detailfolder: str = ""
g_assetsfolder: str = ""


# noinspection DuplicatedCode
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
		pie = Pie(init_opts=opts.InitOpts(theme='light', page_title="RenderDoc Analysis", renderer="svg", width=str(pie_width) + "px", height=str(pie_height) + "px"))
		pie.add("", name_value, radius=[100, 200], center=["50%", "50%"])
		pie.set_global_opts(
			title_opts=opts.TitleOpts(title=pie_title, subtitle=pie_subtitle, pos_top="5%"),
			legend_opts=opts.LegendOpts(is_show=False, orient="vertical", pos_left="left", pos_top="15%"),
			tooltip_opts=opts.TooltipOpts(trigger_on="click", formatter=(JsCode(tooltip_js)), )
		)
		# pie.set_series_opts(label_opts=opts.LabelOpts(position='top', color='black', font_family='Arial', font_size=14, formatter='{b}: {d}%'))
		pie.set_series_opts(label_opts=opts.LabelOpts(position='top', color='black', font_family='Arial', font_size=14, formatter=(JsCode(label_js)), ))
		return pie
	else:
		return None


# Render Pies with tab type
# noinspection DuplicatedCode
def render_tab_chart(html_path, action_array, is_pass=False):
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

	resolution = 0

	# Get data from each pass
	for single in action_array:
		pass_name = str(single.eventId) + "_" + single.get_name()
		filename = os.path.join(g_detailfolder, single.html_name)
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
		resolution = single.resolution

	# save total_time and total_triangles of pass
	if total_num > 0:
		one_over_num = 1 / total_num

	if time_overhead > 0.0:
		one_over_time = 1.0 / time_overhead

	if total_dc > 0:
		one_over_dc = 1 / total_dc

	single = action_array[-1]
	if total_psi > 0:
		one_over_resolution = 1.0 / resolution if single.resolution else (1.0 / total_psi)

	title = "Triangles Number"
	subtitle = ("total triangles = %d" % total_num)
	pie_triangles = render_pie_chart(pass_tri_list, one_over_num, TRIANGLE_PERCENTAGE_THRESHOLD / 100.0, True, title, subtitle)

	title = "Time Overhead"
	subtitle = ("total time = %.3f us" % time_overhead)
	pie_times = render_pie_chart(pass_time_list, one_over_time, TIME_PERCENTAGE_THRESHOLD / 100.0, True, title, subtitle)

	title = "Draw Call"
	subtitle = ("total drawcall = %d" % total_dc)
	pie_dc = render_pie_chart(pass_dc_list, one_over_dc, DC_PERCENTAGE_THRESHOLD / 100.0, True, title, subtitle)

	title = "VS Invocation"
	subtitle = ("total vs invocation = %d" % total_vsi) if not is_pass else ""
	use_percentage = False if single.resolution else True
	pie_vsi = render_pie_chart(pass_vsi_list, one_over_resolution, INVOCATION_THRESHOLD, use_percentage, title, subtitle)

	title = "PS Invocation"
	subtitle = ("total ps invocation = %d" % total_psi) if not is_pass else ""
	use_percentage = False if single.resolution else True
	pie_psi = render_pie_chart(pass_psi_list, one_over_resolution, INVOCATION_THRESHOLD, use_percentage, title, subtitle)

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
	pass


# noinspection DuplicatedCode
def fillin_excel_table(html_path, html_title, table_content, is_top_level, action):
	html_head = "<h1 style='background-color:#5cc27d; color: #FFFFFF; font-size: 40px; padding: 20px 0 5px 5px;'>%s</h1>\n" % html_title
	if not is_top_level:
		for i, j in action.parent_path_dict.items():
			html_head += ("<font style='font-size:20px' > > <a href = %s> %s</a></font>" % (j, i))
		html_head += "<br/><br/>"

	html_table = ("<h2 align='center'>Analysis Data of %s:</h2>\n" % html_title)
	if is_top_level:
		html_table += ("<h4 align='center'>Total Triangles Number:%d &emsp;&emsp; Total Time:%.3f us &emsp;&emsp; Total Draw Call:%d </h4>\n" % (action.triangles_num, action.time, action.draw_call))
	else:
		one_over_resolution = 1.0 / action.resolution if action.resolution > 0 else 0
		vsi_proportion = action.vs_invocation * one_over_resolution
		psi_proportion = action.ps_invocation * one_over_resolution
		html_table += ("<h4 align='center'>Total Triangles Number:%d &emsp;&emsp; Total Time:%.3f us &emsp;&emsp; Total Draw Call:%d &emsp;&emsp; VS Invocation Proportion:%.3f &emsp;&emsp; PS Invocation Proportion:%.3f </h4>\n" % (action.triangles_num, action.time, action.draw_call, vsi_proportion, psi_proportion))
	html_table += "<h4 align='center'>Tips: You can click <i>'EnentID'</i>, <i>'Triangles Num'</i>, <i>'Time Overhead(us)'</i> and <i>'Draw Call'</i>to sort the table.</h4>\n"
	html_table += table_content

	# Combine pie chart with table
	if os.path.exists(html_path):
		chart_content = open(html_path, encoding='utf-8').read()
		chart_start = chart_content.find('<body>') + 6
		chart_end = chart_content.find('</body>')
		html_content = chart_content[:chart_start] + html_head + chart_content[chart_start:chart_end] + html_table + chart_content[chart_end:]
	else:
		html_content = html_head + html_table
	html = open(html_path, "w", encoding='utf-8')
	html.write(html_content)
	html.close()


# Write top-level(Pass Level) frame······
# noinspection DuplicatedCode
def write_top_level_frame(html_name):
	global g_file_index
	html_top_path = os.path.join(g_assetsfolder, html_name)

	# Calculate html and table_content
	one_over_triangles = 1.0 / g_events_tree.triangles_num if g_events_tree.triangles_num else 0
	one_over_time = 1.0 / g_events_tree.time if g_events_tree.time else 0
	one_over_dcs = 1.0 / g_events_tree.draw_call if g_events_tree.draw_call else 0

	filenames = []
	passes_table = Table()
	passes_info = []
	for p in g_events_tree.passes:
		if len(p.childs) < 1:
			continue
		# resolution
		p.resolution = p.resolution_width * p.resolution_height * p.resolution_depth
		one_over_resolution = 1.0 / p.resolution if p.resolution else 0

		# filename
		detail_name = str(p.eventId)
		detail_html_name = (detail_name + '.html')
		filename = os.path.join(g_detailfolder, detail_html_name)
		if os.path.exists(filename) or filename in filenames:
			detail_html_name = (detail_name + str(g_file_index) + '.html')
			filename = os.path.join(g_detailfolder, detail_html_name)
			g_file_index += 1
		p.html_name = detail_html_name
		filenames.append(filename)
		relative_filename = str(filename).replace(str(g_assetsfolder), ".")
		# table
		event_info = p.get_event_info(relative_filename, one_over_triangles, one_over_time, one_over_dcs, one_over_resolution)
		passes_info.append(event_info)
	table_content = passes_table.print_table(passes_info, True)
	# Render chart
	render_tab_chart(html_top_path, g_events_tree.passes, True)
	# Fillin excel table
	fillin_excel_table(html_top_path, "Top Level", table_content, True, g_events_tree)


def write_detail_passes():
	html_name = 'TopLevelAnalysis.html'
	for single in g_events_tree.passes:
		if len(single.childs) < 1:
			continue
		to_top_path = "../" + html_name
		resolution = single.resolution_width * single.resolution_height * single.resolution_depth
		write_detail_frame(single, to_top_path, resolution)
	pass


# noinspection DuplicatedCode
def write_detail_frame(detail, to_top_path, resolution, is_pass=True):
	global g_file_index
	# Detail html filename
	detail_name = detail.get_name()
	filename = os.path.join(g_detailfolder, detail.html_name)
	relative_parent_path = str(filename).replace(str(g_detailfolder), ".")

	# path of parent to return
	detail.parent_path_dict["Top_Level"] = to_top_path
	for s in detail.childs:
		s.parent_path_dict.update(detail.parent_path_dict)
		s.parent_path_dict[str(detail.eventId) + "_" + detail_name] = relative_parent_path

	# resolution
	one_over_resolution = 1.0 / resolution if resolution else 0

	threshold = MAX_LEVEL_TO_SHOW
	condition = True if is_pass else not detail.is_last_level
	if detail.level <= threshold and condition:
		states_table = Table()
		states_info = []
		# Fillin excel table
		filenames = []
		for s in detail.childs:
			child_name = str(s.eventId)
			child_html_name = (child_name + '.html')
			child_filename = os.path.join(g_detailfolder, child_html_name)
			if os.path.exists(child_filename) or child_filename in filenames:
				child_html_name = (child_name + str(g_file_index) + '.html')
				child_filename = os.path.join(g_detailfolder, child_html_name)
				g_file_index += 1
			s.html_name = child_html_name
			filenames.append(child_filename)
			relative_filename = str(child_filename).replace(str(g_detailfolder), ".")
			s.resolution = resolution
			one_over_triangles = 1 / detail.triangles_num if detail.triangles_num > 0 else 0
			one_over_time = 1 / detail.time if detail.time > 0 else 0
			one_over_dcs = 1 / detail.draw_call if detail.draw_call > 0 else 0
			if s.is_last_level or len(s.childs) < 2:
				relative_filename = ""
			# table
			event_info = s.get_event_info(relative_filename, one_over_triangles, one_over_time, one_over_dcs, one_over_resolution)
			states_info.append(event_info)
		table_content = states_table.print_table(states_info, True)
		if not detail.is_second_last_level:
			render_tab_chart(filename, detail.childs)
		else:
			shader_title = "<h2 align='center'>Shader Resources Infomation</h2>"
			shader_info = ""
			for s in detail.childs:
				if s.parent.get_name() == SHADER_RESOURCES_FOR_PASS:
					texture_info = s.show_binding_textures()
					instruction_info = s.show_shader_instructions()
					if texture_info != "" or instruction_info != "":
						shader_info += ("<h3>%d %s:</h3>" % (
							s.eventId, s.get_name())) + texture_info + "<br/>" + instruction_info + "<br/><br/>"
			table_content += "<br/>"
			if shader_info != "":
				table_content += shader_title + shader_info
		fillin_excel_table(filename, ("%s" % detail_name), table_content, False, detail)
		for s in detail.childs:
			write_detail_frame(s, to_top_path, resolution, False)


def write_events_tree_frame():
	test_path = os.path.join(g_assetsfolder, 'EntireEventsTree.html')
	html = open(test_path, 'w', encoding='utf-8')
	html.write('<h2>Show the entire events tree:</h2>\n')
	for single_pass in g_events_tree.passes:
		html.write('<br/>')
		if single_pass.level <= MAX_LEVEL_TO_SHOW:
			html.write("<h4>%s &emsp; LEVEL:%d SECOND:%d(SHOW)\n</h4>" % (
				single_pass.get_name(), single_pass.level, single_pass.is_second_last_level))
		else:
			html.write('<h4>%s  LEVEL:%d</h4>\n' % (single_pass.get_name(), single_pass.level))
		html.write('<br/>')
		for single_state in single_pass.childs:
			single_state.output_level(html, '&emsp;&emsp;&emsp;')
		html.write('<br/>')
	html.close()


def main(output_dirpath: str):
	# Load
	global g_events_tree
	global g_detailfolder
	global g_assetsfolder
	#
	g_assetsfolder = output_dirpath
	g_detailfolder = os.path.join(output_dirpath, "Detail/")
	with open(os.path.join(output_dirpath, "EventTree.bin"), "rb") as fp:
		g_events_tree = pickle.load(fp)
	# Path of frame
	html_name = 'TopLevelAnalysis.html'
	#
	write_top_level_frame(html_name)
	#
	write_detail_passes()
	# Output events tree frame
	write_events_tree_frame()
	pass


if __name__ == "__main__":
	import sys
	main(sys.argv[1])
	pass
