from pydantic import BaseModel, Field, field_serializer
from typing import List, Union

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