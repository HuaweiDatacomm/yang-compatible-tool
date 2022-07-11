#!/usr/bin/env python

import os, sys, cgi, argparse
from subprocess import call, check_output, CalledProcessError
from tempfile import *
from shutil import *
from datetime import datetime
from functools import wraps
import logging
import bottle
import file_tools
import pyang
from bottle import route, run, install, template, request, response, static_file, error
import threading
import traceback
from report_filter import Report_filter
import json
import copy
import yin_com_yang
import file_tools_for_compare
import zipfile as zip
# requests.packages.urllib3.disable_warnings()

__author__ = 'meijun'
__copyright__ = "Copyright (c) 2018-2020, meijun, huawei@com"
__license__ = "New-style BSD"
__email__ = "meijun@huawei.com"
__version__ = "0"


pyang_cmd = '/usr/local/bin/pyang'
user_data_dir = "/user_data"
confog_dir = "/config"
overtime_time = 1800
debug = False
maximum_lenth_exe = 2097052
repeat_max_run_time = 3

abs_dir = os.path.dirname(os.path.abspath(__file__))
abs_view_dir = os.path.join(abs_dir, 'views')
bottle.TEMPLATE_PATH.insert(0, abs_view_dir)

logger = logging.getLogger('bottle-pyang')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('bottle-pyang.log')
formatter = logging.Formatter('%(msg)s')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_to_logger(fn):
    '''
    Wrap a Bottle request so that a log line is emitted after it's handled.
    (This decorator can be extended to take the desired logger as a param.)
    '''
    @wraps(fn)
    def _log_to_logger(*args, **kwargs):
        request_time = datetime.now()
        actual_response = fn(*args, **kwargs)
        # modify this to log exactly what you need:
        logger.info('%s %s %s %s %s' % (request.remote_addr,
                                        request_time,
                                        request.method,
                                        request.url,
                                        response.status))
        return actual_response
    return _log_to_logger




def validate_yangfile(infilename, yangdir,tmp_file_pyang_output):

    pyang_stderr =  ""
    infile = os.path.join(yangdir, infilename)
    pyang_resfile = str(os.path.join(tmp_file_pyang_output, infilename) + '.pres')
    presfp = open(pyang_resfile, 'w+')
    try:
        call([pyang_cmd, '-p', yangdir, infile], stderr=presfp)
    except:
        print(traceback.format_exc())
        pyang_stderr += traceback.format_exc()
        return  pyang_stderr

    presfp.seek(0)

    info_list = []
    for line in presfp.readlines():
        if line.find('/yang/') != -1:
            if line.split('/yang/')[1] not in info_list:
                pyang_stderr += line.split('/yang/')[1]
                info_list.append(line.split('/yang/')[1])
        elif os.path.basename(line) not in info_list:
            pyang_stderr += os.path.basename(line)
            info_list.append(os.path.basename(line))

    presfp.close()

    return pyang_stderr


def yangfile_treeview(infilename, workdir):
    pyang_output = ""
    infile = os.path.join(workdir, infilename)
    pyang_outfile = str(os.path.join(workdir, infilename) + '.pout')
    pyang_resfile = str(os.path.join(workdir, infilename) + '.pres')

    presfp = open(pyang_resfile, 'w+')
    try:
        status = call([pyang_cmd, '-p', workdir, '-f', 'tree', infile, '-o', pyang_outfile],
                  stderr=presfp)
    except Exception as e:
        pyang_output = traceback.format_exc()
        return  pyang_output

    if os.path.isfile(pyang_outfile):
        outfp = open(pyang_outfile, 'r')
        pyang_output = str(outfp.read())
    else:
        pyang_output = 'No tree output.'
        pass
    presfp.close()
    return pyang_output



def pyang_check_to_result(pyang_resfile, run_time, yang_dir, cmd, results):
    info = None
    presfp = open(pyang_resfile, 'w+')
    try:
        lock = threading.Lock()
        lock.acquire()
        os.chdir(yang_dir)
        call(cmd, stderr=presfp, timeout=overtime_time)
        lock.release()
    except Exception as e:
        if traceback.format_exc().find('TimeoutExpired') != -1:
            info = 'Timeout'
        else:
            info = traceback.format_exc()
        return results ,info

    presfp.seek(0)
    presfp_t = presfp
    filename = ''
    result_for_repeat = []
    for line in presfp:
        if not line.strip():
            continue
        if line.find('Traceback') != -1:
            info = presfp_t.read()
            break

        if line.find('No such file or directory') != -1:
            pyang_error_file = os.path.join(yang_dir, 'pyang_error')
            pwd = os.getcwd()
            with open(pyang_error_file, 'a+') as f:
                f.write(pwd)
                f.write(str(cmd))
            if run_time < repeat_max_run_time:
                run_time += 1
                return pyang_check_to_result(pyang_resfile, run_time, yang_dir, cmd, results)
            else:
                return {'code': '213', 'info': ' pyang run failed no such file or directory','result_dir': 'NULL'}
        else:
            if line in result_for_repeat:
                continue
            result_for_repeat.append(line)
            filename = file_tools.parse_filename_from_pyang_output(line, filename)
            filename = os.path.basename(filename)
            # results[filename] = line
            if filename in results:
                results[filename] += '\n' + line
            else:
                results[filename] = line
    presfp.close()
    return results, info


def get_no_vs_cmd(cmd_ini, no_dev_list, dev_no_vs_list):
    if not no_dev_list and not dev_no_vs_list:
        return '', False

    filenames = ''
    cmd = copy.deepcopy(cmd_ini)
    for filename in no_dev_list:
        filenames += '\'' + filename + '\','
        if maximum_lenth_exe < len(filenames):
            logger.error("The maximum length of linux execution commands is 2097152, it has now passed.")
            break
        cmd.append(filename)

    for filename in dev_no_vs_list:
        filenames += '\'' + filename + '\','
        if maximum_lenth_exe < len(filenames):
            logger.error("The maximum length of linux execution commands is 2097152, it has now passed.")
            break
        cmd.append(filename)
    return cmd, True


def get_vs_cmd(cmd_ini, dev_vs_list, yang_dir):
    if not dev_vs_list:
        return '', False

    filenames_vs = ''
    cmd_vs = copy.deepcopy(cmd_ini)
    cmd_vs.append('-p')
    cmd_vs.append(yang_dir)

    for filename in dev_vs_list:
        filenames_vs += '\'' + filename + '\','
        if maximum_lenth_exe < len(filenames_vs):
            logger.error("The maximum length of linux execution commands is 2097152, it has now passed.")
            break
        cmd_vs.append(filename)
    return cmd_vs, True


def diff_yang_and_vs_files(yang_dir, cmd_check):
    yangfile_list = cmd_check[1]
    dev_list = [filename for filename in yangfile_list if filename.find('-deviations') != -1]
    no_dev_list = [filename for filename in yangfile_list if filename not in dev_list]

    dev_module_list = [module_name.split('-deviations')[0] for module_name in dev_list]
    dev_module_list_set = set(dev_module_list)
    if len(dev_module_list_set) == len(dev_module_list):
        dev_no_vs_list = dev_list
        dev_vs_list = []
    else:
        #get -vs and no vs in deviations files
        dev_vs_list = [filename for filename in dev_list if
                       filename.endswith('-deviations-vs.yang') or
                       filename.endswith('-deviations-vs.yin')
                       or filename.find('-deviations-vs-') != -1]
        dev_no_vs_list = [filename for filename in dev_list if filename not in dev_vs_list]

    cmd, flag_no_vs = get_no_vs_cmd(cmd_check[0], no_dev_list, dev_no_vs_list)
    cmd_vs, flag_vs = get_vs_cmd(cmd_check[0], dev_vs_list, yang_dir)
    return cmd_vs, cmd, flag_vs, flag_no_vs


def check_and_make_dir(workdir):
    if not os.path.exists(workdir):
        os.makedirs(workdir)


def get_check_list_with_validator_full(yang_list):
    waite_for_check_files = []
    waite_for_check_files_public = []
    for file in yang_list:
        basename = os.path.basename(file)
        if (basename.endswith('.yang') or basename.endswith('.yin')) and basename.startswith('huawei-'):
            waite_for_check_files.append(os.path.basename(file))
        elif basename.endswith('.yang') or basename.endswith('.yin'):
            waite_for_check_files_public.append(basename)
    return waite_for_check_files, waite_for_check_files_public

def get_check_cmd_tuple(waite_for_check_files, waite_for_check_files_public, cmd_ini_public, cmd_ini):
    if waite_for_check_files and waite_for_check_files_public:
        return ((cmd_ini_public, waite_for_check_files_public), (cmd_ini, waite_for_check_files))
    elif waite_for_check_files:
        return ((cmd_ini, waite_for_check_files),)
    elif waite_for_check_files_public:
        return ((cmd_ini_public, waite_for_check_files_public),)
    else:
        return ()


@route('/')
@route('/validator')
def validator():
    return template('main', results = {}, return_code="",versions = versions)



@route('/validator', method="POST")
def upload_file():
    results = {}
    uploaded_files = request.files.getlist("data")
    if not uploaded_files:
        # return {'code': '209', 'info': 'please upload yang files or a yang zip', 'result_dir': 'NULL'}
        return template('main', results={}, return_code="209",versions=versions)
    empId = request.forms.get("empId")
    workdir = file_tools.create_temp_workdir(user_data_dir, empId)
    logger.info(empId + "," + workdir)
    check_and_make_dir(workdir)
    yang_dir = os.path.join(workdir,'yang')
    check_and_make_dir(yang_dir)
    savedfiles = file_tools.parse_upload_files(workdir, yang_dir, uploaded_files)
    if not savedfiles:
        # return {'code': '210', 'info': 'upload files should be yang files or a yang zip', 'result_dir': 'NULL'}
        return template('main', results={}, return_code="210", versions=versions)

    tmp_output = create_tmp_file_dir(yang_dir)
    for file in savedfiles:
        print(file)
        pyang_stderr = validate_yangfile(file, yang_dir,tmp_output)
        results[file] = {"pyang_stderr": pyang_stderr}

    return template('main', results = results,return_code="", versions = versions)

def create_tmp_file_dir(yangdir):
    tmp_file_pyang_output = os.path.join(yangdir, 'pyang_output')
    if not os.path.exists(tmp_file_pyang_output):
        os.mkdir(tmp_file_pyang_output)
    return tmp_file_pyang_output


@route('/validator_full', method="POST")
def pyang_check():
    uploaded_files = request.files.getlist("data")
    if not uploaded_files:
        return template('main', results={}, return_code="209", versions=versions)
    empId = request.forms.get("empId")
    workdir = file_tools.create_temp_workdir(user_data_dir, empId)
    logger.info(empId + "," + workdir)
    check_and_make_dir(workdir)
    yang_dir = os.path.join(workdir, 'yang')
    check_and_make_dir(yang_dir)

    savedfiles = file_tools.parse_upload_files(workdir, yang_dir, uploaded_files)
    if not savedfiles:
        return template('main', results={}, return_code="210", versions=versions)

    yangfile_list = file_tools.get_import_from_deviation_yang(yang_dir, sorted(savedfiles))
    waite_for_check_files, waite_for_check_files_public = get_check_list_with_validator_full(yangfile_list)
    cmd_ini = [pyang_cmd, '--lint']
    cmd_ini_public = [pyang_cmd]

    cmd_tuple = get_check_cmd_tuple(waite_for_check_files, waite_for_check_files_public, cmd_ini_public, cmd_ini)
    results = {}
    i = 0
    for cmd_check in cmd_tuple:
        cmd_vs, cmd, flag_vs, flag_no_vs = diff_yang_and_vs_files(yang_dir, cmd_check)
        if flag_no_vs is True:
            print(cmd)
            pyang_resfile = str(os.path.join(workdir, 'pyang-check-output') + str(i) + '.pres')
            results , check_info= pyang_check_to_result(pyang_resfile,0, yang_dir, cmd, results)
            if check_info:
                return {'code': '202', 'info': check_info, 'result_dir': 'NULL'}
        if flag_vs is True:
            print(cmd_vs)
            pyang_resfile_vs = str(os.path.join(workdir, 'pyang-check-output_vs') + str(i) + '.pres')
            results ,check_info = pyang_check_to_result(pyang_resfile_vs,0, yang_dir, cmd_vs, results)
            if check_info:
                return {'code': '203', 'info': check_info, 'result_dir': 'NULL'}
        i += 1

    pyang_stderr = ''
    for filename in sorted(results.keys()):
        pyang_stderr += results[filename] + '\n'

    results['allfiles'] = {"pyang_stderr": pyang_stderr}
    results_all = {}
    results_all['allfiles'] = results['allfiles']
    return template('main', results = results_all,return_code="", versions=versions)


# Pack only the results corresponding to omsys_config.
def get_omsys_tree_view_result(savedir, omsys_config):
    try:
        file_list = str(omsys_config).split(',')
        zip_file_list = []
        zip_name = os.path.join(savedir, "result.zip")
        for file in file_list:
            pout_file = os.path.join(savedir, "%s.pout" % file)
            if os.path.exists(pout_file):
                zip_file_list.append(pout_file)
        zf = zip.ZipFile(zip_name, "w", zip.zlib.DEFLATED)
        for tar in zip_file_list:
            arcname = tar[len(savedir):]
            zf.write(tar, arcname)
        zf.close()
    except:
        return str(traceback.format_exc())
    return "success"


@route('/tree_view',method="POST")
def tree_view():
    results = {}
    savedir = file_tools.create_temp_workdir(user_data_dir, 'tree_view')
    check_and_make_dir(savedir)
    uploaded_files = request.files.getlist("data")
    omsys_config = request.forms.get("omsys_config")
    # example:huawei-aaa.yang,huawei-acl@2021-04-01.yang
    if not uploaded_files:
        return template('main', results={}, return_code="209", versions=versions)
    savedfiles = file_tools.parse_upload_files(savedir, savedir, uploaded_files)

    if not savedfiles:
        return template('main', results={}, return_code="210", versions=versions)

    for file in savedfiles:
        pyang_output = yangfile_treeview(file, savedir)
        results[file] = {"pyang_output": pyang_output}

    if omsys_config:
        result_info = get_omsys_tree_view_result(savedir, omsys_config)
        if result_info == "success":
            return static_file('result.zip', root=savedir, download='result.zip')
        else:
            return result_info
    return template('main', results=results,return_code="", versions=versions)


def check_yang_files_with_pyang(yang_file_list, yang_dir, workdir, i, results):
    waite_for_check_files, waite_for_check_files_public = get_check_list_with_validator_full(yang_file_list)
    if not waite_for_check_files and not waite_for_check_files_public:
        return results

    cmd_ini = [pyang_cmd]
    cmd_ini_public = copy.deepcopy(cmd_ini)
    cmd_ini.append('--lint')
    cmd_tuple = get_check_cmd_tuple(waite_for_check_files, waite_for_check_files_public, cmd_ini_public, cmd_ini)
    for cmd_check in cmd_tuple:
        cmd_vs, cmd, flag_vs, flag_no_vs = diff_yang_and_vs_files(yang_dir, cmd_check)
        if flag_no_vs is True:
            print(cmd)
            pyang_resfile = str(os.path.join(workdir, 'pyang-check-output') + str(i) + '.pres')
            results, check_info = pyang_check_to_result(pyang_resfile, 0, yang_dir, cmd, results)
            if check_info:
                return {'code': '202', 'info': check_info, 'result_dir': 'NULL'}
        if flag_vs is True:
            print(cmd_vs)
            pyang_resfile_vs = str(os.path.join(workdir, 'pyang-check-output_vs') + str(i) + '.pres')
            results, check_info = pyang_check_to_result(pyang_resfile_vs, 0, yang_dir, cmd_vs, results)
            if check_info:
                return {'code': '203', 'info': check_info, 'result_dir': 'NULL'}
        i += 1
    return results


def deal_result_with_schema(results_schema, results, schema_mount_list):
    for file_name in results_schema.keys():
        if file_name not in schema_mount_list:
            continue
        if file_name not in results.keys():
            results[file_name] = results_schema[file_name]
        else:
            results_schema[file_name] = [message for message in results_schema[file_name]
                                         if message not in results[file_name]]
            results[file_name].extend(results_schema[file_name])
    return results


def check_yang_files_with_schema_mount(schema_mount_dict, yang_dir, workdir, yangfile_list):
    i = 0
    results = {}
    for key, schema_mount_list in schema_mount_dict.items():
        if key == 'global_false':
            continue
        schema_mount_list = [file for file in yangfile_list if file.split('.yang')[0] in schema_mount_list]
        results_schema = check_yang_files_with_pyang(schema_mount_list, yang_dir, workdir, i, {})
        if 'result_dir' in results_schema.keys():
            return results_schema
        results = deal_result_with_schema(results_schema, results, schema_mount_list)
        i += 2
    yang_files_other = [file for file in yangfile_list if file.split('.yang')[0]
                        not in schema_mount_dict['global_false']]
    results = check_yang_files_with_pyang(yang_files_other, yang_dir, workdir, i, results)
    return results


@route('/pyangApi' ,method="POST")
def pyang_check_api():
    request_base_dir = request.forms.get("request_base_dir")
    workdir = os.path.join(user_data_dir, request_base_dir)
    yang_dir_param = request.forms.get("yang_dir")
    request_tag = request.forms.get("request_tag")
    if not request_tag:
        return {'code': '206', 'info': 'the request_tag is None', 'result_dir': 'NULL'}
    yang_dir = os.path.join(workdir,yang_dir_param)
    # create output dir
    output_dir = os.path.join(workdir,'pyang')
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    if not os.path.exists(yang_dir):
        return {'code': '201', 'info': 'directry not exist:dir: %s'% yang_dir, 'result_dir': 'NULL'}

    yangfile_list = file_tools.get_import_from_deviation_yang(yang_dir, sorted(os.listdir(yang_dir)))
    yang_dir_path = os.path.abspath(os.path.join(yang_dir, ".."))
    white_list_json_dir = os.path.join(yang_dir_path, 'yang_white_list')
    schema_mount_dict = None
    if os.path.exists(white_list_json_dir):
        schema_mount_dict = file_tools.parse_white_lists_json(white_list_json_dir)
    if schema_mount_dict:
        results = check_yang_files_with_schema_mount(schema_mount_dict, yang_dir, workdir, yangfile_list)
    else:
        results = check_yang_files_with_pyang(yangfile_list, yang_dir, workdir, 0, {})
    if 'result_dir' in results.keys():
        return results

    #to do 0、do filte   parese white_list.xml  filter
    filter_file = file_tools.get_filter_config(confog_dir, request_tag)
    if filter_file:
        try:
            filter = Report_filter()
            filter.do_filter(filter_file, results, 'pyang')
        except:
            return {'code': '212', 'info': 'Filter failure,maybe your tool not in filter config files'}
    #to do 1、results write to output
    str_results = json.dumps(results)
    write_success = file_tools.write_json_to_output(str_results,output_dir)
    if not write_success:
        return {'code': '204', 'info': 'write result file fail.', 'result_dir': 'NULL'}

    return {'code': '200', 'info': 'success', 'output_dir': 'pyang'}

@route('/pyangAccessApi' ,method="POST")
def pyang_check_dependence():
    request_base_dir = request.forms.get("request_base_dir")
    workdir = os.path.join(user_data_dir, request_base_dir)
    yang_dir_param = request.forms.get("yang_dir")
    request_tag = request.forms.get("request_tag")
    if not request_tag:
        return {'code': '206', 'info': 'the request_tag is None', 'result_dir': 'NULL'}

    #default tag vrp
    # request_tag = 'vrp'
    yang_dir = os.path.join(workdir, yang_dir_param)
    yang_dependence_dir = os.path.join(yang_dir, 'dependence')
    yang_check_dir = os.path.join(yang_dir, 'yang')
    #create output dir
    output_dir = os.path.join(workdir, 'pyang')
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    if not os.path.exists(yang_check_dir):
        return {'code': '201', 'info': 'directry not exist:dir: %s'% yang_check_dir, 'result_dir': 'NULL'}

    waite_for_check_files, waite_for_check_files_public = get_check_list_with_validator_full(os.listdir(yang_check_dir))
    if not waite_for_check_files and not waite_for_check_files_public:
        return {'code': '200', 'info': 'success', 'output_dir': 'pyang'}

    cmd_ini = [pyang_cmd]
    cmd_ini.append('-p')
    cmd_ini.append(yang_dependence_dir)
    cmd_ini_public = copy.deepcopy(cmd_ini)
    cmd_ini.append('--lint')

    cmd_tuple = get_check_cmd_tuple(waite_for_check_files, waite_for_check_files_public, cmd_ini_public, cmd_ini)
    results = {}
    i = 0
    for cmd_check in cmd_tuple:
        cmd_vs, cmd, flag_vs, flag_no_vs = diff_yang_and_vs_files(yang_check_dir, cmd_check)
        if flag_no_vs is True:
            print(cmd)
            pyang_resfile = str(os.path.join(yang_check_dir, 'pyang-check-output') + str(i) + '.pres')
            results, check_info = pyang_check_to_result(pyang_resfile, 0, yang_check_dir, cmd, results)
            if check_info:
                return {'code': '202', 'info': check_info, 'result_dir': 'NULL'}
        if flag_vs is True:
            print(cmd_vs)
            pyang_resfile_vs = str(os.path.join(yang_check_dir, 'pyang-check-output_vs') + str(i) + '.pres')
            results, check_info = pyang_check_to_result(pyang_resfile_vs, 0, yang_check_dir, cmd_vs, results)
            if check_info:
                return {'code': '203', 'info': check_info, 'result_dir': 'NULL'}
        i += 1

    #to do 0、do filte   parese white_list.xml  filter
    filter_file = file_tools.get_filter_config(confog_dir,request_tag)
    if filter_file:
        try:
            filter = Report_filter()
            filter.do_filter(filter_file, results, 'pyang')
        except:
            return {'code': '212', 'info': 'Filter failure,maybe your tool not in filter config files'}
    #to do 1、results write to output
    str_results = json.dumps(results)
    write_success = file_tools.write_json_to_output(str_results,output_dir)
    if not write_success:
        return {'code': '204', 'info': 'write result file fail.', 'result_dir': 'NULL'}

    return {'code': '200', 'info': 'success', 'output_dir': 'pyang'}


@route('/single_pyangApi' ,method="POST")
def pyang_check_api():
    request_base_dir = request.forms.get("request_base_dir")
    print(request_base_dir)
    workdir = os.path.join(user_data_dir, request_base_dir)
    print(workdir)
    yang_dir_param = request.forms.get("yang_dir")
    # request_tag = request.forms.get("request_tag")
    #default tag vrp
    request_tag = 'vrp'
    yang_dir = os.path.join(workdir,yang_dir_param)
    print(yang_dir)
    #create output dir
    output_dir = os.path.join(workdir,'pyang')
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    if not os.path.exists(yang_dir):
        return {'code': '201', 'info': 'directry not exist:dir: %s'% yang_dir, 'result_dir': 'NULL'}

    waite_for_check_files = []
    for file in os.listdir(yang_dir):
        basename = os.path.basename(file)
        if basename.endswith('.yang'):
            waite_for_check_files.append(os.path.basename(file))

    results = {}
    tmp_output = create_tmp_file_dir(yang_dir)
    for file in waite_for_check_files:
        pyang_stderr = validate_yangfile(file, yang_dir,tmp_output)
        if len(pyang_stderr) != 0:
            results[file] = pyang_stderr
    print(results)
    #to do 0、do filte   parese white_list.xml  filter
    filter_file = file_tools.get_filter_config(confog_dir,request_tag)
    try:
        filter = Report_filter()
        filter.do_filter(filter_file, results, 'pyang')
    except:
        return {'code': '212', 'info': 'Filter failure,maybe your tool not in filter config files'}
    #to do 1、results write to output
    str_results = json.dumps(results)
    write_success = file_tools.write_json_to_output(str_results,output_dir)
    if not write_success:
        return {'code': '204', 'info': 'write result file fail.', 'result_dir': 'NULL'}

    return {'code': '200', 'info': 'success', 'output_dir': 'pyang'}

@route('/yangcomyin', method="POST")
def upload_file():
    uploaded_files = request.files.getlist("data")
    if not uploaded_files:
        return template('yangcomyin', results={}, return_code="209",versions=versions)
    workdir = file_tools_for_compare.create_temp_workdir(user_data_dir)
    logger.info(workdir)
    file_tools_for_compare.parse_upload_files(workdir, uploaded_files)
    yang_dir = os.path.join(workdir, 'yang')
    yin_dir = os.path.join(workdir, 'yin')
    rely_dir = os.path.join(workdir, 'dependence')
    out_dir = os.path.join(workdir, 'result_file')
    task_dir = os.path.join(os.path.dirname(yin_dir), 'task')
    request_tag = None
    print(task_dir)
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)
    if not os.path.exists(yang_dir) or not os.listdir(yang_dir):
        return {'code': '201', 'info': 'directry not exist:dir: %s'% yang_dir, 'result_dir': 'NULL'}
    if not os.path.exists(yin_dir) or not os.listdir(yin_dir):
        return {'code': '201', 'info': 'directry not exist:dir: %s'% yin_dir, 'result_dir': 'NULL'}

    os.chdir(abs_dir)
    write_success = os.popen("python3 python_call.py " + yang_dir + " " + out_dir + " " + \
                             yin_dir + " " + task_dir + " " + rely_dir + " " + str(request_tag))
    res = write_success.read()
    for line in res.splitlines():
        if line == 'False':
            return {'code': '204', 'info': 'write result file fail.', 'result_dir': 'NULL'}
    output_file = os.path.join(out_dir,'result.json')
    if not os.path.exists(output_file):
        return {'code': '204', 'info': 'write result file fail.', 'result_dir': 'NULL'}

    result_dir = os.path.join(out_dir, 'result.xml')
    if not os.path.exists(result_dir):
        return {'code': '204', 'info': 'write result file fail.', 'result_dir': 'NULL'}

    results = file_tools_for_compare.read_file_to_json(output_file)
    return template('yangcomyin', results=results, return_code="", versions=versions)


@route('/yinAndYangCompare', method="POST")
def upload_file():
    request_base_dir = request.forms.get("request_base_dir")
    workdir = os.path.join(user_data_dir, request_base_dir)
    yang_dir_param = request.forms.get("yang_dir")
    yin_dir_param = request.forms.get("yin_dir")
    request_tag = request.forms.get("request_tag")
    if not request_tag:
        request_tag = "None"
    yang_dir = os.path.join(workdir, yang_dir_param)
    yin_dir = os.path.join(workdir, yin_dir_param)
    rely_dir = os.path.join(os.path.dirname(os.path.dirname(yin_dir)), 'dependence')
    task_dir = os.path.join(os.path.dirname(os.path.dirname(yin_dir)), 'task')
    print(task_dir)
    out_dir = os.path.join(workdir, 'result_file')
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)
    if not os.path.exists(yang_dir) or not os.listdir(yang_dir):
        return {'code': '201', 'info': 'directry not exist:dir: %s'% yang_dir, 'result_dir': 'NULL'}
    if not os.path.exists(yin_dir) or not os.listdir(yin_dir):
        return {'code': '201', 'info': 'directry not exist:dir: %s'% yin_dir, 'result_dir': 'NULL'}

    os.chdir(abs_dir)
    write_success = os.popen("python3 python_call.py " + yang_dir + " " + out_dir +
                             " " + yin_dir + " " + task_dir + " " + rely_dir + " "+ str(request_tag))
    res = write_success.read()
    for line in res.splitlines():
        if line == 'False':
            return {'code': '204', 'info': 'write result file fail.', 'result_dir': 'NULL'}
    output_file = os.path.join(out_dir,'result.json')
    if not os.path.exists(output_file):
        return {'code': '204', 'info': 'write result file fail.', 'result_dir': 'NULL'}

    result_dir = os.path.join(out_dir, 'result.xml')
    if not os.path.exists(result_dir):
        return {'code': '204', 'info': 'write result file fail.', 'result_dir': 'NULL'}

    return {'code': '200', 'info': 'success', 'output_dir': result_dir}

@route('/about')
def about():
    return(template('about'))

@route('/yangcomyin')
def about():
    return(template('yangcomyin', results={}, return_code="", versions=versions))
@error(404)
def error404(error):
    return 'Nothing here, sorry.'

@route('/static/:path#.+#', name='static')
def static(path):
    return static_file(path, root='static')

if __name__ == '__main__':
    port = 8080

    parser = argparse.ArgumentParser(description='A YANG fetching, extracting and validating web application.')
    parser.add_argument('-p', '--port', dest='port', type=int, help='Port to listen to (default is 8080)')
    parser.add_argument('-d', '--data_dir', dest='data_dir', help='Path to user data')
    parser.add_argument('-c', '--config_dir', dest='config_dir', help='Path to user data')
    args = parser.parse_args()

    if args.port:
        port = args.port

    if args.data_dir:
        user_data_dir = args.data_dir

    if args.config_dir:
        confog_dir = args.config_dir


    install(log_to_logger)

    versions = {"pyang_version": pyang.__version__}

    run(server='cherrypy', host='0.0.0.0', port=port)
