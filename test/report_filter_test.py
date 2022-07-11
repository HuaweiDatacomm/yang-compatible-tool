import unittest
from report_filter import *
import file_tools
import json,time
class Report_filter_test(unittest.TestCase):

    def setUp(self):
        self.result = {'huawei-aaa.yang':'huawei-aaa sdfasdaf','huawei-aaa-action.yang':'revision',
                 'openconfig-interfaces.yang':'sdfasdf','ietf-interfaces.yang':'sadfasdfaasdfas',
                 'huawei-pub-type.yang':'jsadf must have a "description" substatement jasldfs\naaaa'+\
                                        'aaaaa\nbbbbbbbbb\ncccccccc\n'}

        self.filepath = 'resource/tag_report_filter.xml'

    def test_parse(self):
        parser = Report_filter_parse(self.filepath)
        try:
            parser.parse()
        except Exception as e:
            print(str(e))

        filter = parser.get_report_filter()

        self.assertEqual(filter.common_filter.filename_filter[0],'huawei-aaa*')
        self.assertEqual(filter.common_filter.filename_filter[1],'openconfig*')
        self.assertEqual(filter.common_filter.filename_filter[2],'ietf-*')
        print(filter.tool_filters['huaweiCheck'].filename_filter)

    def test_list_add(self):
        l2 = ['aa','bb','cc']
        l3 = ['ff','gg','cc']

        merge_l = l2 + l3
        self.assertEqual(merge_l, ['aa','bb','cc','ff','gg','cc'])

    def test_reg_file(self):
        _filter = Report_filter()
        _filter.do_filter(self.filepath,self.result)

        self.assertEqual(self.result,{'huawei-pub-type.yang': 'aaaaaaaaa\ncccccccc\n'})

    def test_reg_file_confd(self):
        _filter = Report_filter()
        _filter.do_filter(self.filepath, self.result, 'confd')

        self.assertEqual(self.result, {'huawei-pub-type.yang': 'aaaaaaaaa\nbbbbbbbbb\n'})

    def test_json(self):
        str_results = json.dumps(self.result)
        print(str_results)

    def test_write_json(self):
        str_results = json.dumps(self.result)
        output_dir = 'resource/'
        file_tools.write_json_to_output(str_results,output_dir)

    def test_time(self):
        now = time.time()
        print(now)
        print(int(now*1000000000))
