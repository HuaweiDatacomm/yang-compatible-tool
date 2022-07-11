__author__ = 'zWX590506'

xpath_prefix = '/'

module_key = 'module'
submod_key = 'submodule'

yang_version_key = 'yang-version'
yang_version_def = '1'
namespace_key = 'namespace'
prefix_key = 'prefix'
belongto_key = 'belongs-to'
import_key = 'import'
include_key = 'include'
revision_key = 'revision'
revision_data_key = 'revision-data'
list_import_to_revision = [import_key,include_key,revision_key]


container_key = 'container'
list_key = 'list'
leaf_list_key = 'leaf-list'
leaf_key = 'leaf'

status_key = 'status'
status_def = 'current'

orderedby_key = 'ordered-by'
orderedby_def = 'system'

mandatory_key = 'mandatory'
mandatory_def = 'false'

min_key = 'min-elements'
min_def = '0'

max_key = 'max-elements'
max_def = 'unbounded'

key_key = 'key'
unique_key = 'unique'
default_key = 'default'

presence_key = 'presence'
iffeature_key = 'if-feature'

config_key = 'config'
config_def = 'true'

typedef_key = 'typedef'
type_key = 'type'
fraction_digits_key = 'fraction-digits'
path_key = 'path'
require_instance_key = 'require-instance'
require_instance_def = 'true'
base_key = 'base'

range_key = 'range'
length_key = 'length'
length_min = '0'
length_max = '18446744073709551615'
error_app_tag_key = 'error-app-tag'
error_message_key = 'error-message'

enum_key = 'enum'
value_key = 'value'
bit_key = 'bit'
position_key = 'position'
pattern_key = 'pattern'
modifier_key = 'modifier'

deviation_key = 'deviation'
deviate_key = 'deviate'

choice_key = 'choice'
case_key = 'case'

rpc_key = 'rpc'
action_key = 'action'
input_key = 'input'
output_key = 'output'

arguement_key = 'augment'
notification_key = 'notification'
feature_key = 'feature'
identity_key = 'identity'

description_key = 'description'
uses_key = 'uses'
grouping_key = 'grouping'
contact_key = 'contact'
organization_key = 'organization'


list_rpc= [rpc_key,action_key,input_key,output_key]
list_rpc_no_typedef = [rpc_key,action_key,choice_key,case_key,notification_key]
list_container = [container_key,list_key,leaf_list_key,leaf_key,notification_key]

list_presence_and_others = [presence_key,default_key,key_key,status_key,orderedby_key,mandatory_key,min_key,max_key,config_key]
list_iffeature_and_unique = [iffeature_key,unique_key]

list_type_substatement = [require_instance_key,fraction_digits_key]
list_type_sub_for_have_sub = [base_key,bit_key,type_key,pattern_key,enum_key,length_key,range_key]

list_type_range_length = [length_key,range_key]
list_pattern_bit_enum_in_type = [pattern_key,bit_key,enum_key,type_key]
list_sub_in_type_sub = [modifier_key,position_key,value_key,error_app_tag_key,error_message_key,status_key]

list_fea_iden = [feature_key,identity_key]

list_not_need_compared = [import_key, grouping_key]

task_name_key_yin = ('huawei-mim-extensions', 'aaa-task')
task_name_id_key_yin = ('huawei-mim-extensions', 'aaa-task-id')
task_name_key_yang = ('huawei-extension', 'task-name')

support_f_key = ('huawei-extension', 'support-filter')
support_f_def_yin = ''
support_f_def_yang = 'false'
need_compare_key = [support_f_key]
check_list_key_default_yang = []
check_list_key_default_yin = []
task_name_no_need_check_list = ('huawei-extension', 'huawei-pub-type')

# mimext:datatype ȡֵ��Χ
password_datatype = ('PASSWORD', 'SYS_PASSWORD', 'PASSWORD_EX', 'PASSWORD_TEXT')
# mimext:datatype_id ȡֵ��Χ ����16����
password_datatype_id = ('33', '45', '36', '291', '0x21', '0x2d', '0x2D', '0x24', '0x123')
# ��������(typedef password��typedef password-extend��typedef one-input-password-extend)
password_type = ('password', 'password-extend', 'one-input-password-extend')