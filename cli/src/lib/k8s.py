from models import *
import requests


def new_cluster(api_url: str, info: K8sClusterModel):
    url = f"{api_url}/nfvcl/v2/api/blue/k8s"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = info.model_dump()

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    task_id = response.json().get("task_id")

    if not task_id:
        raise RuntimeError("No task_id found in response.")

    return task_id

def get_kubeconfig(api_url: str, blueprint_id: str) -> str:
    url = f"{api_url}/nfvcl/v2/api/blue/k8s/root_kubeconfig?blue_id={blueprint_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.text