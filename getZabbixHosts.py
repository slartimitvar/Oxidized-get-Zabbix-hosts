#
# Oliver Jackson: 8 July 2025
# Tested with Zabbix v7.4.0
#
# This script will connect to the Zabbix server via API
# It will return data for the hosts to run config backups from
# and store the dave in the default router.db file with the following map:
#
#   map:
#     name: 0
#     ip: 1
#     model: 2
#     username: 3
#     password: 4
#   vars_map
#     enable: 5
#
# router.db should end up with this format:
#
#  hostname:ipaddress:model:username:password:enablesecret
#

import requests
import json

# Zabbix API details
zabbix_api_url = "https://zabbixServerFQDN/api_jsonrpc.php"
zabbix_auth_token = "yourSecretTokenGoesHere"

# Oxidized router.db file
router_db_file = "/oxidised/router.db"

# Function to get devices from Zabbix API
def get_devices_from_zabbix():
    headers = {"Authorization": f"Bearer {zabbix_auth_token}",
               'Content-Type': 'application/json'}
    data = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": [
                "hostid",
                "host",
                "interfaces"
            ],
            "selectInterfaces": ["ip", "type"],
            "selectTags": ["tag", "value"],
            "evaltype": 0,
            "tags": [
                {
                    "tag": "oxidized",
                    "value": "1",
                    "operator": 1
                }
            ],
            "inheritedTags": True,
            "selectMacros": ["macro", "value"],
            "selectParentTemplates": [
                "templateid",
                "name"
        ]

        },
        "id": 1
    }
    response = requests.post(zabbix_api_url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json()['result']
    else:
        print(f"Error fetching data from Zabbix: {response.status_code}")
        return None

# Function to get macro values for device from Zabbix API
def get_device_macros_from_zabbix(id):
    headers = {"Authorization": f"Bearer {zabbix_auth_token}",
               'Content-Type': 'application/json'}
    data = {
        "jsonrpc": "2.0",
        "method": "usermacro.get",
        "params": {
            "output": "extend",
            "hostids": id,
            "search": {
                "macro": "OXIDIZED"
            }
        },
        "id": 1
    }
    templateresponse = requests.post(zabbix_api_url, headers=headers, data=json.dumps(data))
    if templateresponse.status_code == 200:
        return templateresponse.json()['result']
    else:
        print(f"Error fetching data from Zabbix: {response.status_code}")
        return None

# Function to transform data and update router.db
def update_oxidized_config(devices):
    if devices:
        with open(router_db_file, "w") as f:
            for device in devices:
                # Set default user, pass and os
                deviceuser = "UNKNOWN"
                devicepass = "UNKNOWN"
                deviceos = "UNKNOWN"
                # Get hostname and ID
                hostname = device['host']
                hostid = device['hostid']
                # Assuming the first interface is the relevant one
                ip_address = device['interfaces'][0]['ip']
                # Get OS from tag
                for tag in device['tags']:
                    if tag['tag'] == "oxidizedos":
                        deviceos = tag['value']
                # Get credentials from device macros if set at the device level
                for macro in device['macros']:
                    if macro['macro'] == "{$OXIDIZED_USERNAME}":
                        deviceuser = macro['value']
                    if macro['macro'] == "{$OXIDIZED_PASSWORD}":
                        devicepass = macro['value']
                # Get credentials from template if not set already from device
                if deviceuser == "UNKNOWN" and devicepass == "UNKNOWN":
                    # Get template with Oxidized in its name
                    for template in device['parentTemplates']:
                        if "Oxidized" in template['name']:
                            # Get credential macro values from template
                            templates = get_device_macros_from_zabbix(template['templateid'])
                            if templates:
                                for templatemacro in templates:
                                    if templatemacro['macro'] == "{$OXIDIZED_USERNAME}":
                                        deviceuser = templatemacro['value']
                                    if templatemacro['macro'] == "{$OXIDIZED_PASSWORD}":
                                        devicepass = templatemacro['value']
                # Write out to file
                f.write(f"{hostname}:{ip_address}:{deviceos}:{deviceuser}:{devicepass}:enableNOTimplemented\n")
        print(f"Oxidized config file updated successfully at {router_db_file}")

# Main execution
devices = get_devices_from_zabbix()
if devices:
    update_oxidized_config(devices)
