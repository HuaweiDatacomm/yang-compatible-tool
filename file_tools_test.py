import unittest
import file_tools
import os,sys,codecs,traceback

class Report_filter_test(unittest.TestCase):

    def test_parse_filename_from_pyang_output(self):
        lines = self.open_file('resource/pyang_all_check_output.txt')
        for lineStr in lines:
            filename = file_tools.parse_filename_from_pyang_output(lineStr)
            print(filename)
        pass

    def test_basename(self):
        lines = self.open_file('resource/pyang_all_check_output.txt')
        for lineStr in lines:
            filename =  lineStr
            print(filename)

    def open_file(self,filepath):
        handle = None
        lines = ''
        try:
            if sys.version < '3':
                handle = codecs.open(filepath, "r", encoding="utf-8")
            else:
                handle = open(filepath, "r", encoding="UTF-8")

            lines = handle.readlines()
        except IOError:
            print(traceback.format_exc())
        except Exception as e:
            print(traceback.format_exc())
        finally:
            if handle is not None:
                handle.close()
        return lines