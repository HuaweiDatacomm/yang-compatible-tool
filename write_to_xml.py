__author__ = 'zWX590506'
# -*- coding: utf-8 -*-

import os
import re
import file_tools_for_compare


def result_to_xml_single_message(results, modulefile):
    """
    used to write messages into the output xml
    """
    for file in sorted(results.keys()):
        messages = results[file]
        for message in messages:
            message.info = re.sub('&', '&amp;', message.info)
            message.info = re.sub('<', '&lt;', message.info)
            message.info = re.sub('>', '&gt;', message.info)
            message.info = re.sub("'", '&apos;', message.info)
            message.info = re.sub('"', '&quot;', message.info)
            target_name = message.target
            if ".yin" in target_name:
                target_name = target_name.replace(".yin", ".yang")
            elif ".yang" not in target_name and ".yin" not in target_name:
                target_name = "{}{}".format(target_name, ".yang")
            single_message = '      <message target= "%s"\n' % target_name +\
                             '               line= "%s"\n' % message.line +\
                             '               path= "%s"\n' % message.path +\
                             '               level= "%s"\n' % message.level +\
                             '               attributes= "%s"\n' % message.attributes +\
                             '               tool= "yin_consistency_check"\n' +\
                             '               info= "%s">\n' % message.info +\
                             "      </message>\n"
            modulefile.write(single_message)


def result_to_xml(result_directory, results, task_directory):
    """
    write the top message
    """
    xml_name = os.path.join(result_directory, "result.xml")
    modulefile = file_tools_for_compare.open_xml_file(xml_name)

    modulefile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    if not os.path.isdir(task_directory) or not os.listdir(task_directory):
        modulefile.write\
            ('<!-- The task configuration table is not uploaded. Check by default rules. -->\n')

    modulefile.write('<pyang_details>\n    <pdu pdu-name= "UNKNOWN">\n')
    result_to_xml_single_message(results, modulefile)
    modulefile.write('    </pdu>\n</pyang_details>\n')
    modulefile.close()
