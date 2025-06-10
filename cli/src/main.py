from lib.vm import *
from lib.k8s import *
from lib.common import *

from models import HostAccessInfoModel, FlavorModel, VmModel
from functools import partial
import argparse

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

def new_blueprint(api_url: str, func):
  task_id = func(api_url=api_url)
  blueprint_id = get_blueprint_id(api_url=api_url, task_id=task_id)   

  return blueprint_id


def new_vm(area_id:int, flavor_name: str, password: str ='password'):
  my_vm = VmModel(mgmt_net="vlan69", password=password, flavor=flavors[flavor_name])
  func = partial(new_vm, area=area_id, info=my_vm)

  blueprint_id = new_blueprint(api_url=api_url, func=func)
  return blueprint_id
   
def new_single_cluster(area_id: int, flavor_name: str, password: str = 'password'):
  area = K8sAreaModel(
    area_id=area_id,
    is_master_area=True,
    mgmt_net="vlan69",
    additional_networks= [],
    load_balancer_pools_ips= [],
    worker_replicas= 1,
    worker_flavors=flavors['xlarge']
  )

  cluster=K8sClusterModel(
    password=password,
    master_flavors=flavors[flavor_name],
    areas=[area]
  )
  func = partial(new_cluster, info=cluster)

  blueprint_id = new_blueprint(api_url=api_url, func=func)
  return blueprint_id

def main():
  parser = argparse.ArgumentParser(
      description="Create K8s clusters or VMs.",
      epilog="For more information, see the documentation or use --help with subcommands."
  )
  subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-commands")

  # K8s subcommand
  k8s_parser = subparsers.add_parser(
      "k8s",
      help="Create a new K8s cluster",
      description="Create a new Kubernetes cluster in the specified area."
  )
  k8s_parser.add_argument("area_id", type=int, help="Area ID where the cluster will be created")
  k8s_parser.add_argument("flavor_name", type=str, help="Flavor name for the master node")
  k8s_parser.add_argument("--password", type=str, default="password", help="Password for the cluster (default: password)")

  # VM subcommand
  vm_parser = subparsers.add_parser(
      "vm",
      help="Create a new VM",
      description="Create a new Virtual Machine in the specified area."
  )
  vm_parser.add_argument("area_id", type=int, help="Area ID where the VM will be created")
  vm_parser.add_argument("flavor_name", type=str, help="Flavor name for the VM")
  vm_parser.add_argument("--password", type=str, default="password", help="Password for the VM (default: password)")

  args = parser.parse_args()

  if args.command == "k8s":
    blueprint_id = new_single_cluster(args.area_id, args.flavor_name, args.password)
    print(blueprint_id)
  elif args.command == "vm":
    blueprint_id = new_vm(args.area_id, args.flavor_name, args.password)
    print(blueprint_id)

if __name__ == '__main__':
   main()