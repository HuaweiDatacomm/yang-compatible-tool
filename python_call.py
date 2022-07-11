__author__ = 'zWX590506'
# -*- coding: utf-8 -*-
import sys
import json
import yin_com_yang
import file_tools


if __name__ == '__main__':
    yang_dir = r"D:\11.yang白盒\问题定位\20220420_yinyang\yang"
    out_dir = r"D:\11.yang白盒\问题定位\20220420_yinyang"
    yin_dir = r"D:\11.yang白盒\问题定位\20220420_yinyang\yin"
    task_dir = ""
    rely_dir = ""
    tag_request = ""
    cd = yin_com_yang.Compare_Data(yang_dir, out_dir, yin_dir, rely_dir, task_dir)
    cd.get_compare_filelist()
    results = cd.compare_files(tag_request)
    for file in results.keys():
        message_end = ''
        for message in results[file]:
            message_end += message.target + ':' + str(message.line) + ':' + message.level + ': ' + message.info + '\n'
        results[file] = message_end[:-1]
    str_results = json.dumps(results)
    write_success = file_tools.write_json_to_output(str_results, out_dir)
    sys.stdout.write(str(write_success))



