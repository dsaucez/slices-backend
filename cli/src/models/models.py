from pydantic import BaseModel, Field, field_serializer
from typing import List, Union, Optional

class HostAccessInfoModel(BaseModel):
    access_ip: str
    name: str
    username: str
    password: str

class FlavorModel(BaseModel):
    vcpu_count: Union[str, int]
    memory_mb: Union[str, int]
    storage_gb: Union[str, int]
    vcpu_type: str = Field("host")
    require_port_security_disabled: bool = Field(False)

    @field_serializer('vcpu_count')
    def serialize_vcpu_count(self, v):
        return str(v)
    @field_serializer('memory_mb')
    def serialize_memory_mb(self, v):
        return str(v)
    @field_serializer('storage_gb')
    def serialize_storage_gb(self, v):
        return str(v)

class VmModel(BaseModel):
    password: str = Field("password")
    mgmt_net: str
    version: str = Field("UBUNTU24")
    data_nets: List[str] = Field([])
    flavor: FlavorModel

class K8sAreaModel(BaseModel):
    area_id: int
    is_master_area: bool = Field(True)
    mgmt_net: str
    additional_networks: List[str] = Field([])
    load_balancer_pools_ips: List [str] = Field([])
    worker_replicas: int = Field(1)
    worker_flavors: FlavorModel

class K8sClusterModel(BaseModel):
    password: str = Field("password")
    master_flavors: FlavorModel
    areas: List[K8sAreaModel]