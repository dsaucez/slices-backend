from lib.vm import *
from models import HostAccessInfoModel, FlavorModel, VmModel

api_url="http://nfvcl.sopnode.slices-ri.eu:5002"

flavors = {
        'nano':    FlavorModel(vcpu_count=2,  memory_mb=4*1*1024,  storage_gb=2*10),
        'micro':   FlavorModel(vcpu_count=2,  memory_mb=4*2*1024,  storage_gb=2*10),
        'small':   FlavorModel(vcpu_count=2,  memory_mb=4*2*1024,  storage_gb=2*10),
        'medium':  FlavorModel(vcpu_count=4,  memory_mb=4*4*1024,  storage_gb=4*10),
        'large':   FlavorModel(vcpu_count=4,  memory_mb=4*4*1024,  storage_gb=4*10),
        'xlarge':  FlavorModel(vcpu_count=8,  memory_mb=4*8*1024,  storage_gb=8*10),
        '2xlarge': FlavorModel(vcpu_count=16, memory_mb=4*16*1024, storage_gb=16*10),
        '3xlarge': FlavorModel(vcpu_count=32, memory_mb=4*32*1024, storage_gb=32*10)
        }

def get_flavors() -> dict[str, FlavorModel]:
    return flavors

if __name__ == '__main__':
  print (get_flavors())

  my_vm = VmModel(mgmt_net="vlan69", flavor=flavors["nano"])
  task_id = new_vm(api_url=api_url, area=105, info=my_vm)
  blueprint_id = get_blueprint_id(api_url=api_url, task_id=task_id)
  print(f"Blueprint ID: {blueprint_id}")

  details = get_blueprint_details(api_url=api_url, blueprint_id=blueprint_id)
  print (details)

  access = get_access_details(api_url=api_url, blueprint_id=blueprint_id)
  print (access)

  blueprint_id = "GMQEBH"
  print (get_kubeconfig(api_url=api_url, blueprint_id=blueprint_id))