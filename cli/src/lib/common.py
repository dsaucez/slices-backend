from models import HostAccessInfoModel
import requests
import time
import sys
import json
import os


def register_vm(blueprint_id: str):

    register_url = f"http://localhost:8123/register_vm/{blueprint_id}"
    jwt = os.getenv("SLICES_JWT")

    headers = {
        "Authorization": f"Bearer {jwt}"
    }
    response = requests.post(register_url, headers=headers)
    
    return response.status_code

def get_blueprint_id(api_url, task_id):
    status_url = f"{api_url}/v2/utils/get_task_status?task_id={task_id}"

    while True:
        status_response = requests.get(status_url)
        status_response.raise_for_status()
        status_data = status_response.json()
        if status_data.get("status") == "done":
            blueprint_id = status_data.get("result")
            print (file=sys.stderr)
            return blueprint_id
        print('.', end="", file=sys.stderr, flush=True)
        time.sleep(1)  # wait before polling again


def get_blueprint_details(api_url: str, blueprint_id: str):
  url = f"{api_url}/nfvcl/v2/api/blue/{blueprint_id}?detailed=true"
  response = requests.get(url)
  response.raise_for_status()
  return response.json()


def get_mac(network_interfaces, ip):
  mac = next(
      (iface["fixed"]["mac"]
       for interfaces in network_interfaces.values()
       for iface in interfaces
       if iface.get("fixed", {}).get("ip") == ip),
      None  # default if not found
  )
  return mac

def get_access_details(api_url: str, blueprint_id: str) -> dict[str, HostAccessInfoModel]:
    details = get_blueprint_details(api_url=api_url, blueprint_id=blueprint_id)

    hosts = {}
    for key, obj in details['registered_resources'].items():
        if obj['type'] == "nfvcl_core_models.resources.VmResource":
            vm = obj['value']

            hosts[vm['name']] = HostAccessInfoModel(
                access_ip=vm['access_ip'],
                name=vm['name'],
                username=vm['username'],
                password=vm['password'],
                mac=get_mac(network_interfaces=vm['network_interfaces'], ip=vm['access_ip'])
            )
    return hosts
