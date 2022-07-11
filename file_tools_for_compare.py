__author__ = 'zWX590506'
# -*- coding: utf-8 -*-
import os
import re
import sys
import codecs
import time
import traceback
import xmltodict
import base
from zipfile import *
import json
import rarfile
import urllib.parse

sys.setrecursionlimit(1000000)
config_dir = r"D:\11.yang白盒\CodeHub\yang-server-config\yinAndYangCompare"

def create_temp_workdir(user_data):
    randomUuid = int(time.time() * 1000)
    tmpFileName = 'yangcomyin-' + str(randomUuid)
    workdir = os.path.join(user_data, tmpFileName)
    return workdir
def parse_upload_files(workdir, uploaded_files):
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    for file in uploaded_files:
        name, ext = os.path.splitext(file.filename)
        if ext == ".zip" and 1 == len(uploaded_files):
            zipfilename = os.path.join(workdir, urllib.parse.quote(file.raw_filename))
            file.save(zipfilename)
            zf = ZipFile(zipfilename, "r")
            zf.extractall(workdir)
        elif ext == ".rar" and 1 == len(uploaded_files):
            rarfilename = os.path.join(workdir, urllib.parse.quote(file.raw_filename))
            file.save(rarfilename)
            rar_file = rarfile.RarFile(rarfilename)
            rar_file.extractall(workdir)
            rar_file.close()
    return

def get_out_main_module_yin_from_path(path, file_list):
    main_list = []
    for file in file_list:
        yin_file = os.path.join(path, file)
        cont_dict = open_xml_and_convert_to_dict(yin_file)
        if cont_dict:
            if base.module_key in cont_dict.keys():
                main_list.append(file)
    return main_list


def open_xml_and_convert_to_dict(file_name, en="UTF-8"):
    cont_dict = None
    handle = None
    try:
        if sys.version < '3':
            handle = codecs.open(file_name, 'r', encoding=en)
        else:
            handle = open(file_name, encoding=en)
        doc_file = handle.read()
        cont_dict = xmltodict.parse(doc_file)
    except IOError:
        print(traceback.format_exc())
    except Exception as e:
        print(traceback.format_exc())
    finally:
        if handle is not None:
            handle.close()
    return cont_dict


def get_out_main_module_yang_from_path(path, file_list):
    # path = options.yang_directory
    modulefiles = []
    pattern_module = re.compile(r'.*module\s*(\S*)\s*')
    pattern_submodule = re.compile(r'.*submodule\s*(\S*)\s*')
    r = re.compile(r"^(.*?)(\@(\d{4}-\d{2}-\d{2}))?\.(yang|yin)$")
    for file in file_list:
        if file.find("-deviations") != -1:
            continue
        m = None
        module_yang_file = os.path.join(path, file + '.yang')
        if os.path.isdir(module_yang_file):
            continue
        fd = None
        text_lines = []
        try:
            if sys.version < '3':
                fd = codecs.open(module_yang_file, "r", encoding="utf-8")
            else:
                fd = open(module_yang_file, "r", encoding="utf-8")

            text_lines = fd.readlines()
            m = r.search(module_yang_file)
        except Exception:
            print("can not open the file %s" % module_yang_file)
            # logger.error('can not open the file:%s', file)
        finally:
            if fd is not None:
                fd.close()

        if m is not None:
            i = 0
            while True:
                if i >= len(text_lines):
                    # logger.error('can not find module info in yang file:%s',file)
                    break
                j = 0
                text_temp = text_lines[i].strip()
                if not text_temp:
                    i += 1
                    continue
                if text_temp[j] == '/':
                    if text_temp[j + 1] == '/':
                        i += 1
                        continue
                    elif text_temp[j + 1] == '*':
                        p = text_lines[i].find('*/')
                        while p == -1:
                            i += 1
                            p = text_lines[i].find('*/')
                        i += 1
                        continue

                submodule = pattern_submodule.findall(text_temp)

                if submodule:
                    i += 1
                    break

                module = pattern_module.findall(text_temp)
                if module:
                    if file not in modulefiles:
                        modulefiles.append(file)
                    break
                i += 1
    return modulefiles


def open_xml_file(xml_name):
    file_obj = None
    try:
        if sys.version < '3':
            file_obj = codecs.open(xml_name, 'w+',encoding="utf-8")
        else:
            file_obj = open(xml_name,'w', encoding="UTF-8")
    except Exception:
        if file_obj is not None:
            file_obj.close()
    return file_obj

    
def check_task_id(task_dict, sub_task, if_product):
    task_id = sub_task['@id'].zfill(4)
    if task_id not in task_dict.keys() or if_product:
        task_dict[task_id] = sub_task['@name']
    elif task_dict[task_id] != sub_task['@name']:
        print("error in id")
    
def get_task_dict(xml_dict, task_dict, if_product):
    try:
        task_list = xml_dict['TASK_DEFINE']['task']
        if type(task_list) == list:
            for sub_task in task_list:
                check_task_id(task_dict, sub_task,if_product)
        else:
        # 当文件XXX_cli_task.xml中只有一个task时，task_list的类型不是list，是<class 'collections.OrderedDict'>
            check_task_id(task_dict, task_list, if_product)
    except:
        return task_dict
    return task_dict


def get_all_task_module_and_id(xml_dir):
    if not os.path.isdir(xml_dir) or not os.listdir(xml_dir):
        xml_dir = config_dir
    task_dict = {}
    for xml_file in os.listdir(xml_dir):
        if_product = False
        if xml_file.endswith('cli_task.xml'):
            xml = os.path.join(xml_dir, xml_file)
            xml_dict = open_xml_and_convert_to_dict(xml, "gb2312")
            if not xml_dict:
                xml_dict = open_xml_and_convert_to_dict(xml, "utf-8")
            if xml_dict:
                if xml_file.find('product') != -1:
                    if_product = True
                task_dict = get_task_dict(xml_dict, task_dict, if_product)
    return task_dict

def read_file_to_json(file_path):
    return_val = None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return_val = json.load(f)
            f.close()
    except IOError:
        print(traceback.format_exc())
    except Exception as e:
        print(traceback.format_exc())
    return return_val


def read_file(deviation_yang_file):
    fd = None
    text_lines = []
    try:
        fd = open(deviation_yang_file, "r", encoding="utf-8")
        text_lines = fd.readlines()
    except Exception:
        print("can not open the file %s" % deviation_yang_file)
    finally:
        if fd is not None:
            fd.close()
    return text_lines


def get_import_from_deviation_yang(path, deviation_list, if_need_add=False):
    pattern_import = re.compile(r'^import\s*(\S*)\s*{.*')
    import_dict = {}
    for file in[file for file in deviation_list]:
        if if_need_add:
            file = file + '.yang'
        if not file.endswith('.yang'):
            continue
        deviation_yang_file = os.path.join(path, file)
        text_lines = read_file(deviation_yang_file)
        if text_lines:
            i = 0
            while True:
                if i >= len(text_lines):
                    break
                j = 0
                text_temp = text_lines[i].strip()
                if not text_temp:
                    i += 1
                    continue
                if text_temp[j] == '/':
                    if text_temp[j + 1] == '/':
                        i += 1
                        continue
                    elif text_temp[j + 1] == '*':
                        p = text_lines[i].find('*/')
                        while p == -1:
                            i += 1
                            p = text_lines[i].find('*/')
                        i += 1
                        continue
                if text_temp.startswith('deviation '):
                    break
                import_module = pattern_import.search(text_temp)
                if import_module:
                    import_module_name = import_module.group(1)
                    if file.startswith(import_module_name + '-deviations'):
                        i += 1
                        continue
                    tag = True
                    if file.split('-deviations')[0] in import_dict.keys():
                        for sub_module_file in import_dict[file.split('-deviations')[0]]:
                            if sub_module_file.split('-deviations')[0] == import_module_name:
                                tag = False
                                break
                    if tag:
                        if import_module_name not in import_dict.keys():
                            import_dict[import_module_name] = [file]
                        else:
                            import_dict[import_module_name].append(file)
                    change_index_if_need(file, import_module_name, deviation_list, import_dict)
                i += 1
    return deviation_list


def change_index_if_need(file, import_module_name, deviation_list, import_dict):
    import_deviation = [file for file in deviation_list if file.startswith(import_module_name + '-deviations')]
    file = file.split('.yang')[0]
    for import_deviation_yang in import_deviation:
        import_deviation_yang = import_deviation_yang.split('.yang')[0]
        index_yang = deviation_list.index(file)
        index_import = deviation_list.index(import_deviation_yang)
        if index_yang > index_import:
            del deviation_list[index_yang]
            deviation_list.insert(index_import, file)
            print(index_yang, file, ': ', import_module_name, ': ', import_deviation_yang, index_import)
            file_prefix = file.split('-deviations')[0]
            if file_prefix in import_dict.keys():
                for sub_need_import in import_dict[file_prefix]:
                    change_index_if_need(sub_need_import, file_prefix, deviation_list, import_dict)
    return
