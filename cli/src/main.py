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


def _new_vm(area_id:int, flavor_name: str, password: str):
  my_vm = VmModel(mgmt_net="vlan69", password=password, flavor=flavors[flavor_name])
  func = partial(new_vm, area=area_id, info=my_vm)

  blueprint_id = new_blueprint(api_url=api_url, func=func)
  return blueprint_id
   
def _new_single_cluster(area_id: int, flavor_name: str, password: str):
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
  subparsers = parser.add_subparsers(dest="resource", required=True, help="Resource type")

  # K8s resource
  k8s_parser = subparsers.add_parser(
      "k8s",
      help="Kubernetes cluster operations",
      description="Operations for Kubernetes clusters."
  )
  k8s_subparsers = k8s_parser.add_subparsers(dest="action", required=True, help="K8s actions")

  k8s_create_parser = k8s_subparsers.add_parser(
      "create",
      help="Create a new K8s cluster",
      description="Create a new Kubernetes cluster in the specified area."
  )
  k8s_create_parser.add_argument("area_id", type=int, help="Area ID where the cluster will be created")
  k8s_create_parser.add_argument("flavor_name", type=str, help="Flavor name for the master node")
  k8s_create_parser.add_argument("--password", type=str, default="password", help="Password for the cluster (default: password)")

  # VM resource
  vm_parser = subparsers.add_parser(
      "vm",
      help="Virtual machine operations",
      description="Operations for Virtual Machines."
  )
  vm_subparsers = vm_parser.add_subparsers(dest="action", required=True, help="VM actions")

  vm_create_parser = vm_subparsers.add_parser(
      "create",
      help="Create a new VM",
      description="Create a new Virtual Machine in the specified area."
  )
  vm_create_parser.add_argument("area_id", type=int, help="Area ID where the VM will be created")
  vm_create_parser.add_argument("flavor_name", type=str, help="Flavor name for the VM")
  vm_create_parser.add_argument("--password", type=str, default="password", help="Password for the VM (default: password)")

  # Flavor resource
  flavor_parser = subparsers.add_parser(
      "flavor",
      help="Flavor operations",
      description="Operations for Flavors."
  )
  flavor_subparsers = flavor_parser.add_subparsers(dest="action", required=True, help="Flavor actions")

  flavor_list_parser = flavor_subparsers.add_parser(
      "list",
      help="List available flavors",
      description="List all available flavors in a table."
  )

  args = parser.parse_args()

  if args.resource == "k8s" and args.action == "create":
    blueprint_id = _new_single_cluster(area_id=args.area_id, flavor_name=args.flavor_name, password=args.password)
    print(blueprint_id)
  elif args.resource == "vm" and args.action == "create":
    blueprint_id = _new_vm(area_id=args.area_id, flavor_name=args.flavor_name, password=args.password)
    print(blueprint_id)
  elif args.resource == "flavor" and args.action == "list":
    flavors = get_flavors()
    print(f"{'Name':<10} {'vCPUs':<6} {'Memory(MB)':<12} {'Storage(GB)':<11}")
    print("-" * 41)
    for name, flavor in flavors.items():
      print(f"{name:<10} {flavor.vcpu_count:<6} {flavor.memory_mb:<12} {flavor.storage_gb:<11}")

if __name__ == '__main__':
   main()