from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DeploymentBase(BaseModel):
    instance_name: str
    instance_type: str
    ami_id: str
    key_name: str

class DeploymentCreate(DeploymentBase):
    pass

class Deployment(DeploymentBase):
    id: int
    instance_id: str
    status: str
    public_ip: Optional[str] = None
    private_ip: Optional[str] = None
    security_group_id: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    az: Optional[str] = None
    launch_time: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DeploymentResponse(BaseModel):
    success: bool
    instance_id: str
    deployment_id: int
    message: str

class HealthCheck(BaseModel):
    status: str
    database: str