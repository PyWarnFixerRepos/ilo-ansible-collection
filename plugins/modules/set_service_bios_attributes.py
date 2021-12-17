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

DOCUMENTATION = r"""
---
module: set_service_bios_attributes
description: This module configures service BIOS settings in the servers
requirements:
    - "python >= 3.6"
    - "ansible >= 2.11"
author:
    - "Gayathiri Devi Ramasamy (@Gayathirideviramasamy)"
options:
  baseuri:
    description:
      - iLO IP of the server
    type: str
    default: NONE
    required: true
  username:
    description:
      - Username of the server for authentication
    type: str
    default: NONE
    required: true
  password:
    description:
      - Password of the server for authentication
    type: str
    default: NONE
    required: true
  service_attributes:
    description:
      - BIOS service attributes that needs to be configured in the given server
    type: dict
    default: NONE
    required: true
  http_schema:
    description:
      - http or https Protocol
    type: str
    default: https
    required: false
"""

EXAMPLES = r"""
- name: Set service BIOS options
  set_service_bios_attributes:
    service_attributes:
      ProcMonitorMwait: "Disabled"
      MemPreFailureNotification": "Enabled"
    baseuri: "***.***.***.***"
    username: "abcxyz"
    password: "*****"
"""

RETURN = r"""
  expected_result 1:
    description: Service BIOS settings applied
    returned: Service BIOS settings applied. System Reset required.
    type: str
  expected_result 2:
    description: Already Service BIOS attributes are set on the server
    returned: Service BIOS attributes already set
    type: str
  failure case 1:
    description: Redfish Package is not installed
    returned: Failed to import the required Python library (redfish)
    corrective_action: Install python3-redfish package
    type: str
  failure case 2:
    description: Incorrect/Unreachable server IP address(baseuri) is provided
    returned: RetriesExhaustedError
    corrective_action: Provide the correct IP address of the server
    type: str
  failure case 3:
    description: Credentials not valid
    returned: InvalidCredentialsError
    corrective_action: Validate the credentials
    type: str
  failure case 4:
    description: Getting server data failed
    returned: GET on /redfish/v1/systems/1/ Failed, Status <Status code>, Response <API response>
    corrective_action: Verify the response in the output message
    type: str
  failure case 5:
    description: Getting bios URI failed
    returned: Getting BIOS URI Failed, Key Bios not found in /redfish/v1/systems/1/ response
    corrective_action: BIOS API not found in the server details returned. Verify server details in the server
    type: str
  failure case 6:
    description: Getting Service settings failed
    returned: GET on /redfish/v1/systems/1/bios/service/settings/ Failed, Status <Status code>, Response <API response> (or) GET on /redfish/v1/systems/1/bios/oem/hpe/service/settings/ Failed, Status <Status code>, Response <API response>
    corrective_action: Verify the response in the output message
    type: str
  failure case 7:
    description: Input paramaters validation failed
    returned: Incorrect attributes
    corrective_action: check if the input parameters are correct
    type: str
  failure case 8:
    description: Applying Service BIOS attributes failed
    returned: Applying Service BIOS attributes Failed, Status <Status code>, Response <API response>
    corrective_action: Verify the response in the output message
    type: str
"""

import json

try:
    from redfish import redfish_client

    HAS_REDFISH = True
except ImportError:
    HAS_REDFISH = False

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

base_uri = "/redfish/v1/"
system_uri = "systems/1/"


def logout(redfishClient, module):
    redfishClient.logout()


def error_msg(module, method, uri, status, response):
    # Print error message
    module.fail_json(
        msg="%s on %s Failed, Status: %s, Response: %s"
        % (str(method), str(uri), str(status), str(response))
    )


def validate_input_attributes(module, service_bios, attributes):
    # Make a copy of the attributes dict
    attrs_to_patch = dict(attributes)
    # List to hold attributes not found
    attrs_bad = {}

    # Check the attributes
    for attr_name, attr_value in attributes.items():
        # Check if attribute exists
        if attr_name not in service_bios["Attributes"]:
            # Remove and proceed to next attribute if this isn't valid
            attrs_bad.update({attr_name: attr_value})
            del attrs_to_patch[attr_name]
            continue

        # If already set to requested value, remove it from PATCH payload
        if service_bios["Attributes"][attr_name] == attributes[attr_name]:
            del attrs_to_patch[attr_name]

    if attrs_bad:
        module.fail_json(msg="Incorrect attributes: %s" % str(attrs_bad))

    # Return success with changed=False if no attrs need to be changed
    if not attrs_to_patch:
        module.exit_json(changed=False, msg="Service BIOS attributes already set")


def get_service_bios_attributes(redfishClient, module, bios_uri):
    # GET service settings
    service_uri = bios_uri + "service/settings/"
    response = redfishClient.get(service_uri)
    # Check if service API doesn't support
    if response.status == 404:
        # call different API if response is 404
        service_uri = bios_uri + "oem/hpe/service/settings/"
        response = redfishClient.get(service_uri)
    # Fail if GET response is not 200
    if response.status != 200:
        error_msg(module, "GET", service_uri, response.status, response.text)
    server_service_bios = json.loads(response.text)
    return service_uri, server_service_bios


def set_service_bios_attributes(redfishClient, module):
    # define variables
    service_attributes = module.params["service_attributes"]
    uri = base_uri + system_uri
    server_data = redfishClient.get(uri)
    if server_data.status != 200:
        error_msg(module, "GET", uri, server_data.status, server_data.text)
    server_details = json.loads(server_data.text)
    if "Bios" not in server_details:
        module.fail_json(
            msg="Getting BIOS URI Failed, Key 'Bios' not found in %s response: %s"
            % (uri, str(server_details))
        )
    bios_uri = server_details["Bios"]["@odata.id"]

    # GET service BIOS URI and service BIOS attributes in the server
    service_uri, server_service_bios = get_service_bios_attributes(
        redfishClient, module, bios_uri
    )
    # validate input attributes
    validate_input_attributes(module, server_service_bios, service_attributes)

    body = {"Attributes": service_attributes}
    # PATCH service settings
    response = redfishClient.patch(service_uri, body=body)
    # Fail if PATCH response is not 200
    if response.status != 200:
        module.fail_json(
            msg="Applying Service BIOS attributes Failed, status: %s, response: %s, API: %s"
            % (str(response.status), str(response.text), service_uri)
        )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            baseuri=dict(required=True, type="str"),
            service_attributes=dict(required=True, type="dict"),
            username=dict(required=True, type="str"),
            password=dict(required=True, type="str", no_log=True),
            http_schema=dict(required=False, default="https", type="str"),
        )
    )

    if not HAS_REDFISH:
        module.fail_json(msg=missing_required_lib("redfish"))

    baseuri = module.params["baseuri"]
    username = module.params["username"]
    password = module.params["password"]
    http_schema = module.params["http_schema"]

    base_url = "{}://{}".format(http_schema, baseuri)
    redfishClient = redfish_client(
        base_url=base_url, username=username, password=password
    )
    redfishClient.login()

    set_service_bios_attributes(redfishClient, module)
    logout(redfishClient, module)
    module.exit_json(
        changed=True, msg="Service BIOS settings applied. System Reset required."
    )


if __name__ == "__main__":
    main()