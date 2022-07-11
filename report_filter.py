import xmltodict
import os
import logging
import sys
import traceback
import codecs
import re

class Report_filter():
    def __init__(self):
         self.common_filter = None
         self.tool_filters = {}
         self.tag = None

    def get_common_filter(self):
        return self.common_filter

    def get_filter_by_tool(self,tool):
        return self.tool_filters[tool]

    def filter_reg_match(self, target_str, reg_list):
        # print(len(reg_white_list))
        if len(target_str) == 0:
            return True
        for reg_str in reg_list:
            # print("reg_str:%s" %reg_str)
            # print("line:%s" %line)
            if re.match(r'''(%s)''' % reg_str, target_str):
                # print("True")
                return True
        # print("False")
        return False

    def parse_file(self,filter_file):
        parser = Report_filter_parse(filter_file)
        try:
            parser.parse()
        except Exception as e:
            print(str(e))

        filter = parser.get_report_filter()
        return filter

    def do_filter(self,filter_file,report_result,tool='pyang'):
        filter = self.parse_file(filter_file)
        files_in_report = report_result.keys()
        filter_files = []
        # check common file
        common_filter = filter.common_filter
        tool_filter = filter.tool_filters[tool]
        all_file_to_filter = common_filter.get_filename_filter() + \
                             tool_filter.get_filename_filter()

        for filename in files_in_report:
            if self.filter_reg_match(filename,all_file_to_filter):
                filter_files.append(filename)

        #delete filter files
        for file in filter_files:
             print("delete file: %s" % file)
             del(report_result[file])

        # check common file
        message_in_report = report_result.keys()
        all_message_to_filter = common_filter.get_errorinfo_filter() + \
                                tool_filter.get_errorinfo_filter()
        # for filename in message_in_report:
        for filename in [filename for filename in message_in_report]:
            newMesssage = ''
            filter_flag =False
            # print(report_result[filename])
            messages = report_result[filename]
            if 0 == len(messages):
                del (report_result[filename])
                continue

            for error_info in messages.split('\n'):
                if self.filter_reg_match(error_info, all_message_to_filter):
                    filter_flag = True
                    continue
                newMesssage +=error_info+'\n'

            # delete if message is empty
            if 0 == len(newMesssage):
                del (report_result[filename])
                continue

            if filter_flag:
                report_result[filename] = newMesssage






class Filteritem():
    def __init__(self):
        self.filename_filter = []
        self.errorinfo_filter = []

    def get_filename_filter(self):
        if not self.filename_filter:
            self.filename_filter = []
        elif type(self.filename_filter) != list:
            filename_filter_tem = []
            filename_filter_tem.append(self.filename_filter)
            self.filename_filter = filename_filter_tem
        return self.filename_filter

    def get_errorinfo_filter(self):
        if not self.errorinfo_filter:
            self.errorinfo_filter = []
        elif type(self.errorinfo_filter) != list:
            errorinfo_filter_tem = []
            errorinfo_filter_tem.append(self.errorinfo_filter)
            self.errorinfo_filter = errorinfo_filter_tem
        return self.errorinfo_filter

class Report_filter_parse():
    def __init__(self,file_name):
        self._report_filter = Report_filter()
        self.file_name =file_name

    def get_report_filter(self):
        return self._report_filter

    def open_xml_and_convert_to_dict(self,file_name, logger=None):
        cont_dict = None
        try:
            if sys.version < '3':
                handle = codecs.open(file_name, 'r+', encoding="utf-8")
            else:
                handle = open(file_name, encoding="UTF-8")
            doc_file = handle.read()
            cont_dict = xmltodict.parse(doc_file)
        except IOError:
            traceback.format_exc()
        except Exception as e:
            print(traceback.format_exc())
        return cont_dict

    def parseItemFilter(self,item_filter_element):
        tempfilter = Filteritem()
        filename_filter_element = item_filter_element['filename-filter']
        if filename_filter_element is not None:
            matchs = filename_filter_element['reg-match']['match']
            tempfilter.filename_filter = matchs

        errorinfo_filter_element = item_filter_element['errorinfo-filter']
        if errorinfo_filter_element is not None:
            matchs = errorinfo_filter_element['reg-match']['match']
            tempfilter.errorinfo_filter = matchs
        return tempfilter

    def parseCommonFilter(self, commonFilter):
        self._report_filter.common_filter = self.parseItemFilter(commonFilter)

    def parseFilterItems(self, toolsFilterItems):
        if toolsFilterItems is None:
            return
        for item in toolsFilterItems['filter-item']:
            toolname = item['@tool-name']
            if toolname is None:
                continue

            item_filter = self.parseItemFilter(item)
            self._report_filter.tool_filters[toolname] = item_filter

    def parse(self):

        if self.file_name is None or \
           not os.path.exists(self.file_name) or \
           not os.path.isfile(self.file_name):
            print(self.file_name)
            raise Exception('invalid input param file_name.')

        if self.file_name.endswith('report_filter.xml'):
            filter_dict = self.open_xml_and_convert_to_dict(self.file_name)
            if filter_dict is None:
                raise Exception('Parse report_filter.xml error.')

            whiteboxfilter = filter_dict['white-box-filter']
            if whiteboxfilter is not None:
                whiteboxfiltertag = whiteboxfilter['@tag']
                if whiteboxfiltertag is not None:
                    self._report_filter.tag = whiteboxfiltertag

                commonFilter = whiteboxfilter['common-filter']
                if commonFilter is not None:
                    self.parseCommonFilter(commonFilter)

                filterItems = whiteboxfilter['filter-items']
                if filterItems is not None:
                    self.parseFilterItems(filterItems)