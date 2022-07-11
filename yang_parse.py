__author__ = 'lWX566763'
import re
import io
import logging
import os
import mpyang
import yin_com_yang
from mpyang import error


class mock_opts():
    def __init__(self):
        self.format = 'yang'
        self.yang_remove_unused_imports = False
        self.yang_canonical = True
        self.outfile = None
        self.xx = 0


def initializate_ctx(yang_directory):
    repos = mpyang.FileRepository(yang_directory)
    ctx = mpyang.Context(repos)
    o = mock_opts()
    ctx.opts = o
    ctx.yin_module_map = {}
    return ctx


def get_out_yang_module(yang_directory, yang_name, ctx, mod_pa):

    # yang_name = get_yang_file_name(yang_directory, module_name)
    yang_name_p = os.path.join(yang_directory, yang_name)
    module = parse_yang_module(ctx, yang_name_p)
    if module:
        # logging.info('get out yang module %s success!',yang_name)
        print('get out yang module ', yang_name + ' success!')
        check_module(module, yang_name, mod_pa)
    return module


def get_error_level(error_type):
    error_level = error.err_level(error_type)
    if error.is_error(error_level):
        return 'error'
    else:
        return 'warning'
def check_module(module, file_name, mod_pa):
    module_error = module.i_ctx.errors
    for sub_error in module_error:
        err_message = ''
        for sub_message in sub_error:
            err_message += ',' + str(sub_message)
        if err_message.find(file_name) == -1:
            continue
        else:
            err_message = err_message.split(file_name)[1]
        logging.error("%s:%s", file_name, str(err_message))
        info = str(file_name) + ':' + str(err_message)
        try:
            level = get_error_level(sub_error[1])
        except:
            level = 'error'
        yin_com_yang.add_result_details(mod_pa, '', '', info, 'Grammar', file_name, level)


def parse_yang_module(ctx, filename):
    module = None
    m = None
    fd = None
    text = ''
    r = re.compile(r"^(.*?)(\@(\d{4}-\d{2}-\d{2}))?\.(yang|yin)$")
    try:
        fd = io.open(filename, "r", encoding="utf-8")
        text = fd.read()
        m = r.search(filename)

    except Exception:
        logging.error("can not open the file %s" % filename)
    finally:
        if fd is not None:
            fd.close()
    if m is not None:
        (name, _dummy, rev, format) = m.groups()
        name = os.path.basename(name)
        try:
            module = ctx.add_module(filename, text, format, name, rev,
                                    expect_failure_error=False)
        except:
            print("%s can not be parsed by pyang" % filename)
    else:
        print("%s can not be parsed by pyang" % filename)
    return module



    # def get_yang_namespace(self):
    #     module = self.module
    #     namespace = module.search_one('namespace')
    #     if namespace is None:
    #         return None, None
    #     return namespace.arg , namespace.pos.line