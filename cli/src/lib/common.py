import requests
import time

def get_blueprint_id(api_url, task_id):
    status_url = f"{api_url}/v2/utils/get_task_status?task_id={task_id}"

    while True:
        status_response = requests.get(status_url)
        status_response.raise_for_status()
        status_data = status_response.json()
        if status_data.get("status") == "done":
            blueprint_id = status_data.get("result")
            print ()
            return blueprint_id
        print('.', end="", flush=True)
        time.sleep(1)  # wait before polling again


def get_blueprint_details(api_url: str, blueprint_id: str):
  url = f"{api_url}/nfvcl/v2/api/blue/{blueprint_id}?detailed=true"
  response = requests.get(url)
  response.raise_for_status()
  return response.json()
