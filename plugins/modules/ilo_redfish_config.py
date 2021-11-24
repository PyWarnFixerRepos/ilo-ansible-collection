#!/usr/bin/python
# -*- coding: utf-8 -*-
###
# Copyright (2021) Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
---
module: ilo_redfish_config
short_description: Sets or updates configuration attributes on HPE iLO with Redfish OEM extensions
version_added: 4.1.0
description:
    - Builds Redfish URIs locally and sends them to remote OOB controllers to
    set or update a configuration attribute.
    - For use with HPE iLO operations that require Redfish OEM extensions
options:
  category:
    required: true
    type: str
    description:
      - Command category to execute on iLO.
    choices: ['Manager']
  command:
    required: true
    description:
      - List of commands to execute on iLO.
    type: list
    elements: str
  baseuri:
    required: true
    description:
      - Base URI of iLO.
    type: str
  username:
    description:
      - User for authentication with iLO.
    type: str
  password:
    description:
      - Password for authentication with iLO.
    type: str
  auth_token:
    description:
      - Security token for authentication with OOB controller.
    type: str
  timeout:
    description:
      - Timeout in seconds for URL requests to iLO controller.
    default: 10
    type: int
  attribute_name:
    required: true
    description:
      - Name of the attribute.
    type: str
  attribute_value:
    required: false
    description:
      - Value of the attribute.
    type: str
requirements:
    - "python >= 3.8"
    - "ansible >= 3.2"
author:
    - "Bhavya B (@bhavya06)"
'''

EXAMPLES = '''
  - name: Disable WINS Registration
    community.general.ilo_redfish_config:
      category: Manager
      command: SetWINSReg
      baseuri: 15.X.X.X
      username: Admin
      password: Testpass123
      attribute_name: WINSRegistration

  - name: Set Time Zone
    community.general.ilo_redfish_config:
      category: Manager
      command: SetTimeZone
      baseuri: 15.X.X.X
      username: Admin
      password: Testpass123
      attribute_name: TimeZone
      attribute_value: Chennai
'''

CATEGORY_COMMANDS_ALL = {
    "Manager": ["SetTimeZone", "SetDNSserver", "SetDomainName", "SetNTPServers", "SetWINSReg"]
}

from ansible_collections.community.general.plugins.module_utils.ilo_redfish_utils import iLORedfishUtils
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native


def main():
    result = {}
    module = AnsibleModule(
        argument_spec=dict(
            category=dict(required=True, choices=list(
                CATEGORY_COMMANDS_ALL.keys())),
            command=dict(required=True, type='list', elements='str'),
            baseuri=dict(required=True),
            username=dict(),
            password=dict(no_log=True),
            auth_token=dict(no_log=True),
            attribute_name=dict(required=True),
            attribute_value=dict(),
            timeout=dict(type='int', default=10)
        ),
        required_together=[
            ('username', 'password'),
        ],
        required_one_of=[
            ('username', 'auth_token'),
        ],
        mutually_exclusive=[
            ('username', 'auth_token'),
        ],
        supports_check_mode=False
    )

    category = module.params['category']
    command_list = module.params['command']

    creds = {"user": module.params['username'],
             "pswd": module.params['password'],
             "token": module.params['auth_token']}

    timeout = module.params['timeout']

    root_uri = "https://" + module.params['baseuri']
    rf_utils = iLORedfishUtils(creds, root_uri, timeout, module)
    mgr_attributes = {'mgr_attr_name': module.params['attribute_name'],
                      'mgr_attr_value': module.params['attribute_value']}

    offending = [
        cmd for cmd in command_list if cmd not in CATEGORY_COMMANDS_ALL[category]]

    if offending:
        module.fail_json(msg=to_native("Invalid Command(s): '%s'. Allowed Commands = %s" % (
            offending, CATEGORY_COMMANDS_ALL[category])))

    if category == "Manager":
        resource = rf_utils._find_managers_resource()
        if not resource['ret']:
            module.fail_json(msg=to_native(resource['msg']))

        dispatch = dict(
            SetTimeZone=rf_utils.set_time_zone,
            SetDNSserver=rf_utils.set_dns_server,
            SetDomainName=rf_utils.set_domain_name,
            SetNTPServers=rf_utils.set_ntp_server,
            SetWINSReg=rf_utils.set_wins_registration
        )

        for command in command_list:
            result = dispatch[command](mgr_attributes)

    if result['ret']:
        module.exit_json(changed=result.get('changed'),
                         msg=to_native(result.get('msg')))
    else:
        module.fail_json(msg=to_native(result['msg']))


if __name__ == '__main__':
    main()
