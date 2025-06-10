import requests
from models import  VmModel
from .common import get_blueprint_details


def new_vm(api_url: str, area_id: int, info: VmModel):
    url = f"{api_url}/nfvcl/v2/api/blue/ubuntu"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {"area": area_id} | info.model_dump()

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    task_id = response.json().get("task_id")

    if not task_id:
        raise RuntimeError("No task_id found in response.")

    return task_id
