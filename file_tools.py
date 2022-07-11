import os
from zipfile import *
import re
import time
import sys
import codecs
import traceback
import shutil
import rarfile
import json
import urllib.parse

sys.setrecursionlimit(1000000)
DEFAULT_CONFIG_NAME = 'DEFAULT_report_filter.xml'
pattern_import_yang_file = re.compile(r'^import\s*[\"\']*([\w-]*)[\"\']*\s*.*')
pattern_import_yin_file = re.compile(r'^<import\s*module\s*=\s*"(\S*)"\s*>*')
pattern_prefix_yang_file = re.compile(r'^.*prefix\s*[\"\']*([\w-]*)[\"\']*\s*;.*')
pattern_prefix_yin_file = re.compile(r'^<prefix\s*value\s*=\s*"(\S*)"\s*/>')
deviation_str_yang = 'deviation '
deviation_str_yin = '<deviation target-node='
revision_str_yang = 'revision '
revision_str_yin = '<revision '


def create_temp_workdir(user_data,empId):
    randomUuid = int(time.time() * 1000)
    tmpFileName = 'pyang-'+ empId + "-"+str(randomUuid)
    workdir = os.path.join(user_data,tmpFileName)
    return workdir

def parse_upload_files(workdir, yang_dir, uploaded_files):
    savedfiles = []
    for file in uploaded_files:
        name, ext = os.path.splitext(file.raw_filename)

        if ext in (".yang", ".yin"):
            file.save(os.path.join(yang_dir, file.raw_filename))

        elif ext == ".zip":
            zipfilename = os.path.join(workdir, urllib.parse.quote(file.raw_filename))
            file.save(zipfilename)
            zf = ZipFile(zipfilename, "r")
            zf.extractall(yang_dir)
            zf.close()
        elif ext == ".rar":
            rarfilename = os.path.join(workdir, urllib.parse.quote(file.raw_filename))
            file.save(rarfilename)
            rar_file = rarfile.RarFile(rarfilename)
            rar_file.extractall(yang_dir)
            rar_file.close()

    for root, dirs, files in os.walk(yang_dir):
        for filename in files:
            if (filename.endswith(".yang") or filename.endswith(".yin")) and filename not in savedfiles:
                savedfiles.append(filename)
                yang_file = os.path.join(root, filename)
                file_in_yang_dir = os.path.join(yang_dir, filename)
                if not os.path.exists(file_in_yang_dir):
                    try:
                        shutil.move(yang_file, yang_dir)
                    except:
                        print(traceback.format_exc())
                        continue

    return savedfiles

def get_filter_config(config_dir,request_tag):
    if not os.path.exists(config_dir):
        return None

    for file in os.listdir(config_dir):
        if request_tag+'_report_filter.xml' == file:
            return os.path.join(config_dir,file)

    file = DEFAULT_CONFIG_NAME
    if os.path.exists(os.path.join(config_dir, file)):
        return os.path.join(config_dir, file)
    return None

def write_json_to_output(str_results,output_dir):
    output_file = os.path.join(output_dir,'result.json')
    handle = None
    try:
        if sys.version < '3':
            handle = codecs.open(output_file, "w", encoding="utf-8")
        else:
            handle = open(output_file,"w", encoding="UTF-8")

        handle.write(str_results)
    except IOError:
        print(traceback.format_exc())
        return False
    except Exception as e:
        print(traceback.format_exc())
        return False
    finally:
        if handle is not None:
            handle.close()

    return True

def parse_filename_from_pyang_output(lineStr, filename):
    if lineStr is None or 0 == len(lineStr):
        if filename:
            return filename
        return None
    elif lineStr.find(".yang") != -1 or lineStr.find(".yin") != -1:
        return lineStr.split(':')[0]
    elif filename:
        return filename
    return lineStr.split(':')[0]


def read_file(deviation_yang_file):
    with open(deviation_yang_file, "r", encoding="utf-8") as fd:
        text_lines = fd.readlines()
    return text_lines


# 备注部分跳过
def check_if_remarks_in_yang(text_temp, text_lines, i):
    j = 0
    if not text_temp:
        return i
    if text_temp[j] == '/':
        if text_temp[j + 1] == '/':
            return i
        elif text_temp[j + 1] == '*':
            p = text_lines[i].find('*/')
            while p == -1:
                i += 1
                p = text_lines[i].find('*/')
            return i
    return False


# 防止循环引用导致排序死循环
def check_circular_reference(file, import_dict, import_module_name):
    file_name = file.split('.')[0].split('@')[0]
    if file_name in import_dict.keys():
        for sub_module_file in import_dict[file_name]:
            if sub_module_file.split('.')[0].split('@')[0] == import_module_name:
                return False
    return True


# 获取import关系，并判断是否需要改变排序
def get_import_and_sort(import_module, file, import_dict, no_deviation_list):
    import_module_name = import_module.group(1)
    if check_circular_reference(file, import_dict, import_module_name):
        if import_module_name not in import_dict.keys():
            import_dict[import_module_name] = [file]
        else:
            import_dict[import_module_name].append(file)
    change_index_if_need(file, import_module_name, no_deviation_list, import_dict)


class Pattern_or_Keyword():
    def __init__(self):
        self.pattern_import = pattern_import_yang_file
        self.str_deviation_start = revision_str_yang
        self.pattern_prefix = pattern_prefix_yang_file
        self.deviation_str = deviation_str_yang


def get_pattern_with_suffix(file):
    pattern_or_keyword = Pattern_or_Keyword()
    if not file.endswith('.yang'):
        pattern_or_keyword.pattern_import = pattern_import_yin_file
        pattern_or_keyword.str_deviation_start = revision_str_yin
        pattern_or_keyword.pattern_prefix = pattern_prefix_yin_file
        pattern_or_keyword.deviation_str = deviation_str_yin
    return pattern_or_keyword


# 先对非裁剪文件排序，结束后将裁剪文件插入到被裁减模块的位置即可
def get_import_from_deviation_yang(path, yangfile_list):
    import_dict = {}
    yangfile_list = [file for file in yangfile_list if file.endswith('.yang') or file.endswith('.yin')]
    no_deviation_list = [file for file in yangfile_list if file.find('-deviations') == -1]
    dev_list = [filename for filename in yangfile_list if filename.find('-deviations') != -1]
    for file in [file for file in no_deviation_list]:
        pattern_or_keyword = get_pattern_with_suffix(file)
        yang_file = os.path.join(path, file)
        text_lines = read_file(yang_file)
        if not text_lines:
            continue
        i = 0
        while True:
            if i >= len(text_lines):
                break
            text_temp = text_lines[i].strip()
            new_index = check_if_remarks_in_yang(text_temp, text_lines, i)
            if new_index:
                i = new_index
                i += 1
                continue
            if text_temp.startswith(pattern_or_keyword.str_deviation_start):
                break
            import_module = pattern_or_keyword.pattern_import.search(text_temp)
            if import_module:
                get_import_and_sort(import_module, file, import_dict, no_deviation_list)
            i += 1
    deal_with_deviation_index(dev_list, no_deviation_list, path)
    return no_deviation_list


def get_deviation_targets_module(deviation_file, path):
    pattern_or_keyword = get_pattern_with_suffix(deviation_file)
    module_prefix = {}
    import_module_name = ''
    yang_file = os.path.join(path, deviation_file)
    text_lines = read_file(yang_file)
    if not text_lines:
        return ''
    i = 0
    while True:
        if i >= len(text_lines):
            break
        text_temp = text_lines[i].strip()
        new_index = check_if_remarks_in_yang(text_temp, text_lines, i)
        if new_index:
            i = new_index
            i += 1
            continue
        import_module = pattern_or_keyword.pattern_import.search(text_temp)
        if import_module:
            import_module_name = import_module.group(1)
        prefix_module = pattern_or_keyword.pattern_prefix.search(text_temp)
        if prefix_module and import_module_name:
            prefix_name = prefix_module.group(1)
            module_prefix[prefix_name] = import_module_name
        if text_temp.startswith(pattern_or_keyword.deviation_str):
            deviation_xpath = text_temp[len(pattern_or_keyword.deviation_str):-1].strip()
            target_nodes = re.findall(r'(/[0-9a-zA-Z\_\-:]+)', deviation_xpath)
            node_path = target_nodes[-1]
            qnames = re.match(r'/([0-9a-zA-Z\_\-]+):.*', node_path)
            if qnames.group(1) in module_prefix.keys():
                return module_prefix[qnames.group(1)]
            break
        i += 1
    return ''


# 将裁剪文件插入到被裁剪主模块前面
def deal_with_deviation_index(dev_list, no_deviation_list, path):
    for deviation_file in dev_list:
        main_module = get_deviation_targets_module(deviation_file, path)
        module_match_in_list = [file for file in no_deviation_list if
                                file.split('.')[0].split('@')[0] == main_module]
        if not module_match_in_list:
            no_deviation_list.append(deviation_file)
            continue
        index_yang = no_deviation_list.index(module_match_in_list[0])
        no_deviation_list.insert(index_yang, deviation_file)


# A import B 则 A 在 B的前面
def change_index_if_need(file, import_module_name, no_deviation_list, import_dict):
    import_yangs = [file for file in no_deviation_list if
                    file.split('.')[0].split('@')[0] == import_module_name]
    for import_yang in import_yangs:
        index_yang = no_deviation_list.index(file)
        index_import = no_deviation_list.index(import_yang)
        if index_yang > index_import:
            del no_deviation_list[index_yang]
            no_deviation_list.insert(index_import, file)
            file_prefix = file.split('.')[0].split('@')[0]
            if file_prefix in import_dict.keys():
                for sub_need_import in import_dict[file_prefix]:
                    change_index_if_need(sub_need_import, file_prefix, no_deviation_list, import_dict)
    return


def read_file_to_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return_val = json.load(f)
        f.close()
    return return_val


def parse_white_lists_json(white_list_json_dir):
    json_file = os.path.join(white_list_json_dir, 'result.json')
    json_val = read_file_to_json(json_file)
    return json_val
