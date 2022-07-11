__author__ = 'zWX590506'
# -*- coding: utf-8 -*-

import logging
import base
import yin_com_yang

def compare_config(yin_attr, yang_module, mod_pa, i_path):
    path = yin_com_yang.i_path_list_to_str(i_path)
    if not yin_attr.arg:
        return
    try:
        yang_value = str(yang_module.i_config).lower()
    except:
        yang_value = None
    if yin_attr.arg.lower() != yang_value:
        info = 'The config is not equal of this node'
        logging.error(info)
        yin_com_yang.add_result_details(mod_pa, yin_attr.pos.line, path,
                                        info, base.config_key, mod_pa.file_name)


def compare_deviations(yin_node, yang_module, mod_pa, i_path, if_yangcom_yin):
    path = yin_com_yang.i_path_list_to_str(i_path[:-1])
    sub_modules = yang_module.search(yin_node.keyword)
    node_list = []
    for sub_node in sub_modules:
        if not sub_node.arg:
            yang_name = sub_node.keyword
        else:
            yang_name = sub_node.arg
        if yang_name == i_path[-1]:
            node_list.append(sub_node)
    if len(node_list) == 1:
        return node_list[0]
    elif len(node_list) > 1:
        for sub_node in node_list[1:]:
            for sub_stmts in sub_node.substmts:
                if sub_stmts not in node_list[0].substmts:
                    node_list[0].substmts.append(sub_stmts)
        return node_list[0]

    if not if_yangcom_yin:
        info = "The " + yin_node.keyword + ": " + i_path[-1] +\
               " exists in the hostyin file and does" +\
               " not exist in the yang file. Path: " +\
               path +". Line is " + str(yin_node.pos.line) + "."
        file_name = mod_pa.file_name + '.yin'
    else:
        info = "The " + yin_node.keyword + ": " + i_path[-1] +\
               " exists in the yang file and does" +\
               " not exist in the hostyin file. Path: " + path +\
               ". Line is " + str(yin_node.pos.line) + "."
        file_name = mod_pa.file_name + '.yang'
    logging.error(info)
    yin_com_yang.add_result_details(mod_pa, yin_node.pos.line,
                                    path, info, yin_node.keyword, file_name)
    return None


def deal_refine_in_uses(sub_use_modules):
    refine_modules = sub_use_modules.search('refine')
    for sub_refine in refine_modules:
        path_node_name = sub_refine.arg.split("/")
        tar_node = sub_use_modules
        for node_name in path_node_name:
            tar_node = search_node_in_uses_with_refine(tar_node, node_name)
        if tar_node:
            for substmts in sub_refine.substmts:
                substmts_in_grouping = tar_node.search_one(substmts.keyword)
                if substmts_in_grouping:
                    substmts_in_grouping.arg_refine = substmts.arg
                else:
                    tar_node.arg_refine_substmts = substmts


def search_node_in_uses_with_refine(pattern_node, node_name):
    try:
        grouping_node = sub_node(node_name, pattern_node.i_grouping.substmts)
    except AttributeError:
        grouping_node = sub_node(node_name, pattern_node.substmts)
    return grouping_node


def sub_node(node_name, subs_list):
    grouping_node = None
    for sub in subs_list:
        if sub.arg == node_name:
            return sub
        elif sub.keyword == 'uses':
            grouping_node = search_node_in_uses_with_refine(sub, node_name)
            if grouping_node:
                return grouping_node
    return grouping_node


def find_in_use(yang_module, yin_node):
    use_modules = yang_module.search(base.uses_key)
    if use_modules:
        for sub_use_modules in use_modules:
            if hasattr(sub_use_modules.i_grouping, "substmts") is not True:
                continue
            deal_refine_in_uses(sub_use_modules)
            sub_modules = sub_use_modules.i_grouping.search(yin_node.keyword)
            for sub_node in sub_modules:
                if not sub_node.arg:
                    yang_name = sub_node.keyword
                else:
                    yang_name = sub_node.arg
                if yang_name == yin_node.arg:
                    return sub_node
            sub_node = find_in_use(sub_use_modules.i_grouping, yin_node)
            if sub_node:
                return sub_node
    return None

# yang上定义leafref、yin上定义基类型string导致白盒，当前机制不支持解析yin文件的leafref，返回空标签,屏蔽
def compare_leafref_and_string(yin_node, yang_module, if_yangcom_yin):
    if yin_node.arg == 'leafref' and if_yangcom_yin:
        yin_type = yang_module.search_one(base.type_key)
        if yin_type and yin_type.arg == 'string':
            return None
    elif yin_node.arg == 'string' and not if_yangcom_yin:
        yang_type = yang_module.search_one(base.type_key)
        if yang_type and yang_type.arg == 'leafref':
            return None
    return True


def get_node_with_arg(sub_modules, yin_node_name, yin_node):
    if yin_node.keyword in ('augment', 'type'):
        index = 1 if yin_node.keyword == 'augment' else 0
        for sub_node in sub_modules:
            if not sub_node.arg:
                yang_name = sub_node.keyword
            else:
                yang_name = sub_node.arg
            try:
                if sub_node.substmts[index] and yin_node.substmts[index]:
                    if yang_name == yin_node_name and sub_node.substmts[index].keyword == yin_node.substmts[index].keyword and\
                                    sub_node.substmts[index].arg == yin_node.substmts[index].arg:
                        return sub_node
            except IndexError:
                pass
        return find_sub_node(sub_modules, yin_node_name)
    else:
        return find_sub_node(sub_modules, yin_node_name)
    return None

    
def find_sub_node(sub_modules, yin_node_name):
    for sub_node in sub_modules:
        if not sub_node.arg:
            yang_name = sub_node.keyword
        else:
            yang_name = sub_node.arg
        if yang_name == yin_node_name:
            return sub_node
        elif hasattr(sub_node, "arg_refine") is True:
            if sub_node.arg_refine == yin_node_name:
                return sub_node


def find_in_yang(mod_pa, yang_module, i_path, yin_node, if_yangcom_yin):
    path = yin_com_yang.i_path_list_to_str(i_path[:-1])
    sub_modules = yang_module.search(yin_node.keyword)
    #默认值
    if yin_node.keyword == base.yang_version_key and not sub_modules:
        if yin_node.arg == base.yang_version_def:
            return None
    elif yin_node.keyword == base.description_key:
        if not sub_modules and not yin_node.arg:
            return None
        if yin_node.parent.keyword != yang_module.keyword:
            return None
    elif yin_node.keyword == base.type_key:
        if not compare_leafref_and_string(yin_node, yang_module, if_yangcom_yin):
            return None

    sub_node = get_node_with_arg(sub_modules, i_path[-1], yin_node)
    if sub_node:
        return sub_node

    if hasattr(yin_node, "arg_refine") is True:
        yin_node_name = yin_node.arg_refine
        sub_node = get_node_with_arg(sub_modules, yin_node_name, yin_node)
        if sub_node:
            return sub_node

    sub_node = find_in_use(yang_module, yin_node)
    if sub_node:
        return sub_node

    if hasattr(yang_module, "arg_refine_substmts") is True:
        if yang_module.arg_refine_substmts.arg == yin_node.arg:
            sub_node = yang_module.arg_refine_substmts
            return sub_node

    if yin_node.keyword == base.uses_key:
        compare_substmts(mod_pa, yang_module, yin_node.i_grouping, i_path, if_yangcom_yin)
        return None

    if not if_yangcom_yin:
        info = "The " + yin_node.keyword + ": " + i_path[-1] +\
               " exists in the hostyin file and does" +\
               " not exist in the yang file. Path: " + path +\
               ". Line is " + str(yin_node.pos.line) + "."
        file_name = mod_pa.file_name + '.yin'
    else:
        info = "The " + yin_node.keyword + ": " + i_path[-1] +\
               " exists in the yang file and does" +\
               " not exist in the hostyin file. Path: " + path +\
               ". Line is " + str(yin_node.pos.line) + "."
        file_name = mod_pa.file_name + '.yang'
    if yin_node.keyword in (base.description_key, base.revision_key,
                            base.contact_key, base.organization_key):
        logging.warning(info)
        yin_com_yang.add_result_details(mod_pa, yin_node.pos.line, path,
                                        info, yin_node.keyword, file_name, 'warning')
        return None
    logging.error(info)
    yin_com_yang.add_result_details(mod_pa, yin_node.pos.line,
                                    path, info, yin_node.keyword, file_name)
    return None


def check_if_key(leaf_node, if_yin):
    try:
        if if_yin:
            check_list = base.check_list_key_default_yin
        else:
            check_list = base.check_list_key_default_yang
        if str(leaf_node.arg) in check_list:
            return True
        return False
    except:
        return False


def is_leaf_key(leaf_node, if_yin=False):
    try:
        if leaf_node.i_is_key is True:
            return True
    except Exception:
        if check_if_key(leaf_node, if_yin) is True:
            return True
        return False
    return False


def get_yang_support_f(yang_module):
    """
    yang：leaf节点定义了support-filter=true或为key节点，support-filter值为true，其余情况为false
    """
    support_f_sub = yang_module.search_one(base.support_f_key)
    if support_f_sub:
        yang_support_f = support_f_sub.arg
    elif is_leaf_key(yang_module) is True:
        yang_support_f = 'true'
    else:
        yang_support_f = 'false'
    return yang_support_f



def get_yin_support_f(yin_module, mod_pa, i_path):
    """
    #若在module级别定义了一个全局的support-filter且定义为true，提示报错；
    #若在module级别定义了一个全局的support-filter且定义为false，leaf节点存在自定义时，
    按照leaf节点的自定义取值，否则取module的定义值；
    #若module级别没有定义全局的support-filter，leaf节点自定义为false时，取值false；
    自定义为true时，提示报错；没有自定义时，默认取值true。
    """
    path = yin_com_yang.i_path_list_to_str(i_path)
    if base.support_f_def_yin == 'true':
        return ''
    elif is_leaf_key(yin_module, True) is True:
        return 'true'
    support_f_sub = yin_module.search_one(base.support_f_key)
    if support_f_sub:
        #module级别没有定义support-filter，leaf定义了true，提示报错
        if not base.support_f_def_yin and support_f_sub.arg == 'true':
            info = "The support-filter of node " + i_path[-1] +\
                   " should not be defined with value 'true'," \
                   " that the module not define the value."\
                   + " Path: " + path + ". Line is " + str(yin_module.pos.line) + "."
            file_name = mod_pa.file_name + '.yin'
            logging.error(info)
            yin_com_yang.add_result_details(mod_pa, yin_module.pos.line,
                                            path, info, 'support-filter', file_name)
            return ''
        else:
            return support_f_sub.arg
    elif base.support_f_def_yin:
        return base.support_f_def_yin
    else:
        return 'true'


def compare_support_f(yin_module, yang_module, mod_pa, i_path):
    path = yin_com_yang.i_path_list_to_str(i_path)
    yin_support_f = get_yin_support_f(yin_module, mod_pa, i_path)
    if not yin_support_f:
        return
    yang_support_f = get_yang_support_f(yang_module)
    if yin_support_f != yang_support_f:
        info = "The support-filter of node " + i_path[-1] +\
               " are not equal in yin file and yang file."\
               + " Path: " + path + ". Line is " + str(yin_module.pos.line) + "."
        file_name = mod_pa.file_name + '.yin'
        logging.error(info)
        yin_com_yang.add_result_details(mod_pa, yin_module.pos.line,
                                        path, info, 'support-filter', file_name)


def get_list_key(yang_module, yin_module):
    yang_list_key = yang_module.search_one('key')
    yin_list_key = yin_module.search_one('key')
    if yang_list_key:
        base.check_list_key_default_yang = yang_list_key.arg.split(' ')
    else:
        base.check_list_key_default_yang = []
    if yin_list_key:
        base.check_list_key_default_yin = yin_list_key.arg.split(' ')
    else:
        base.check_list_key_default_yin = []


def get_contact_param_after(contact_before):
    contact_param_after = ''
    contact_param_list = contact_before.split('\n')
    for sub_contact in contact_param_list:
        if sub_contact:
            sub_contact = sub_contact.strip()
            contact_param_after += sub_contact + '\n'
    return contact_param_after


def compare_comtact(sub_attr, yang_module, check_key):
    yin_contact = get_contact_param_after(sub_attr.arg)
    yang_contact_sub = yang_module.search_one(check_key)
    if yang_contact_sub:
        yang_contact = get_contact_param_after(yang_contact_sub.arg)
        if yin_contact == yang_contact:
            return True
    return False


def compare_order_with_nodes(sub_yang, sub_yin, i_path, mod_pa):
    """
    裁剪和augment不进行比较
    """
    if not hasattr(sub_yang, 'i_children') or not hasattr(sub_yin, 'i_children'):
        return
    yang_compare_list = [sub_mod for sub_mod in sub_yang.i_children if sub_yin.search_one(sub_mod.keyword, sub_mod.arg, sub_yin.i_children)]
    yin_compare_list = [sub_mod for sub_mod in sub_yin.i_children if sub_yang.search_one(sub_mod.keyword, sub_mod.arg, sub_yang.i_children)]
    for i, yang_node in enumerate(yang_compare_list):
        for j, yin_node in enumerate(yin_compare_list):
            if yin_node.arg == yang_node.arg and yin_node.keyword == yang_node.keyword and i != j:
                file_name = ''.join([mod_pa.file_name, '.yin'])
                if str(yin_node.pos).find(file_name) != -1:
                    i_path.append(str(yang_node.arg))
                    path = yin_com_yang.i_path_list_to_str(i_path)
                    info = ''.join(["The order of node ", i_path[-1],
                                   " are not equal in yin file and yang file.",
                                    " Path: ", path, ". Line is ", str(yin_node.pos.line), "."])

                    logging.error(info)
                    yin_com_yang.add_result_details(mod_pa, yin_node.pos.line,
                                                    path, info, 'node_order', file_name)
                    del i_path[-1]
                break


def deal_with_Escape_in_pattern(sub_attr, yang_module):
    """
    //和/做匹配 默认一致
    """
    if sub_attr.arg.find('\\\\') != -1:
        sub_attr.arg = sub_attr.arg.replace('\\\\', '\\')
    yang_patterns = yang_module.search(base.pattern_key)
    for yang_pattern in yang_patterns:
        if yang_pattern.arg.find('\\\\') != -1:
            yang_pattern.arg = yang_pattern.arg.replace('\\\\', '\\')


# 获取节点的type定义，符合检查要求的返回True
def check_password_in_leaf(yin_module, password_check):
    try:
        type_stmt = yin_module.search_one('type')
        if not type_stmt:
            return password_check
        if type_stmt.arg == 'leafref':
            password_check = check_password_in_leaf(type_stmt.i_type_spec.i_target_node, password_check)
        if type_stmt.i_typedef:
            if type_stmt.i_typedef.arg in base.password_type:
                return True
            if type_stmt.i_typedef.search_one('type'):
                password_check = check_password_in_leaf(type_stmt.i_typedef, password_check)
    except:
        logging.error("get type of node %s failed in file %s line %s." %
                      (str(yin_module.arg),  yin_module.pos.ref, str(yin_module.pos.line)))
    return password_check


# 若YANG中leaf节点的数据类型是密码类型(typedef password、typedef password-extend、typedef one-input-password-extend)
# yin对应的节点必须使用<mimext:password/>或者节点数据类型必须为password（名称和id都可以）
# mimext:datatype   mimext:datatype-id
# PASSWORD          33
# SYS_PASSWORD      45
# PASSWORD_EX       36
# PASSWORD_TEXT     291
def check_type_with_password(yin_module, mod_pa, i_path):
    if check_password_in_leaf(yin_module, False):
        mimext_password = yin_module.search_one(('huawei-mim-extensions', 'password'))
        if mimext_password:
            return

        mimext_datatype = yin_module.search_one(('huawei-mim-extensions', 'datatype'))
        if mimext_datatype and mimext_datatype.arg in base.password_datatype:
            return

        mimext_datatype_id = yin_module.search_one(('huawei-mim-extensions', 'datatype-id'))
        if mimext_datatype_id and mimext_datatype_id.arg in base.password_datatype_id:
            return

        path = yin_com_yang.i_path_list_to_str(i_path)
        info = ''.join(["The type of node: ", i_path[-1],
                        " belongs to password, it needs to "
                        "define the relevant implementation in yin file. Path: ",
                        path, ". Line is ", str(yin_module.pos.line), '.'])
        file_name = mod_pa.file_name + '.yang'
        logging.error(info)
        yin_com_yang.add_result_details(mod_pa, yin_module.pos.line,
                                        path, info, 'password_type', file_name)

def compare_substmts(mod_pa, yang_module, yin_module, i_path, if_yangcom_yin=False):
    """
    比较各个属性的入口
    """
    if hasattr(yin_module, "substmts") is not True:
        return

    if not if_yangcom_yin:
        if yang_module.arg =='huawei-anyflow':
            print("########################test1")
        if yin_module.keyword == base.list_key:
            get_list_key(yang_module, yin_module)
        elif yin_module.keyword == base.leaf_key:
            compare_support_f(yin_module, yang_module, mod_pa, i_path)

        if yin_module.keyword in (base.leaf_key, base.leaf_list_key):
            check_type_with_password(yin_module, mod_pa, i_path)

        compare_order_with_nodes(yang_module, yin_module, i_path, mod_pa)

    for sub_attr in yin_module.substmts:
        if sub_attr.pos.line ==212 :
            print("########test2")
        if sub_attr.keyword in (base.deviation_key, base.deviate_key):
            i_path.append(sub_attr.arg)
            yang_node = compare_deviations(sub_attr, yang_module, mod_pa, i_path, if_yangcom_yin)
            if yang_node:
                compare_substmts(mod_pa, yang_node, sub_attr, i_path, if_yangcom_yin)
                # yang_module.substmts.remove(yang_node)
            del i_path[-1]
            continue
        elif sub_attr.keyword in (base.contact_key, base.description_key):
            if compare_comtact(sub_attr, yang_module, sub_attr.keyword):
                continue
        elif sub_attr.keyword == base.pattern_key:
            deal_with_Escape_in_pattern(sub_attr, yang_module)
        elif sub_attr.keyword in base.list_not_need_compared:
            continue
        elif isinstance(sub_attr.keyword, tuple):
            continue
        elif sub_attr.keyword == base.uses_key:
            deal_refine_in_uses(sub_attr)

        if sub_attr.arg:
            i_path.append(str(sub_attr.arg))
        else:
            i_path.append(str(sub_attr.keyword))

        yang_node = find_in_yang(mod_pa, yang_module, i_path, sub_attr, if_yangcom_yin)

        if yang_node:
            compare_substmts(mod_pa, yang_node, sub_attr, i_path, if_yangcom_yin)

        del i_path[-1]
