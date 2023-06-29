# -*- coding:UTF-8 -*-

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


class Table(object):
	def __init__(self):
		super(Table, self).__init__()
		self.table_format = "<table border=1 cellpadding=10 cellspacing=0 align='center'>"
		self.table_end = "</table>"
		self.header_format = "<tr bgcolor= c0c0c0>"
		self.header_begin = "<tr>"
		self.header_end = "</tr>"
		self.new_line = "\n"
		self.html_padding = "<br/>"
		self.header = 0
		pass

	def print_table_header(self, table_row0, need_sort=False):
		# Table header
		content = self.table_format + self.new_line + self.header_format + self.new_line  # <table> and <tr>
		for table_element in table_row0:
			if need_sort and table_element[3] == "Y":
				content += ("<th id='th%d' onclick='SortTable(this)' class='desc'>" % table_row0.index(table_element))
			else:
				content += "<th>"
			content += table_element[0]  # header
			content += "</th>" + self.new_line
			self.header += 1
		content += self.header_end + self.new_line  # </tr>
		return content

	# noinspection PyMethodMayBeStatic
	def print_table_content(self, table_row):
		# Table content
		content = ""
		for table_element in table_row:
			index = table_row.index(table_element)
			if table_element[1] == "int":
				content += "<td name='td%d'><a href='%s'>%d</a></td>" % (index, table_element[4], table_element[2]) if table_element[4] != "" else ("<td name='td%d'>%d</td>" % (index, table_element[2]))
			elif table_element[1] == "string":
				content += "<td name='td%d'><a href='%s'>%s</a></td>" % (index, table_element[4], table_element[2]) if table_element[4] != "" else ("<td name='td%d'>%s</td>" % (index, table_element[2]))
			elif table_element[1] == "float":
				content += "<td name='td%d'><a href='%s'>%.3f</a></td>" % (index, table_element[4], table_element[2]) if table_element[4] != "" else ("<td name='td%d'>%.3f</td>" % (index, table_element[2]))
			elif table_element[1] == "percentage":
				content += "<td name='td%d'><a href='%s'>%.2f %%</a></td>" % (index, table_element[4], table_element[2]) if table_element[4] != "" else ("<td name='td%d'>%.2f %%</td>" % (index, table_element[2]))
		return content

	def print_table(self, obj_table, need_sort=False):
		content = ""
		if len(obj_table) > 0:
			sort_function = table_sort_function.replace("COLUMN_NUM", str(len(obj_table[0])))
			content = sort_function + self.print_table_header(obj_table[0], need_sort)  # <table>
			for table_row in obj_table:
				content += self.header_begin  # <tr>
				content += self.print_table_content(table_row)
				content += self.header_end + self.new_line  # </tr>
			content += self.table_end + self.html_padding  # </table>
		return content
