import requests
import time
from models import HostAccessInfoModel, VmModel
from .common import get_blueprint_details


def new_vm(api_url: str, area: int, info: VmModel):
    url = f"{api_url}/nfvcl/v2/api/blue/ubuntu"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {"area":105} | info.model_dump()

    print (payload)
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    task_id = response.json().get("task_id")

    if not task_id:
        raise RuntimeError("No task_id found in response.")

    return task_id


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
                password=vm['password']
            )
    return hosts


