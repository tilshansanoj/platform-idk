from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class Deployment(Base):
    __tablename__ = "deployments"
    
    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(String(50), unique=True, index=True, nullable=False)
    instance_name = Column(String(100), nullable=False)
    instance_type = Column(String(20), nullable=False)
    ami_id = Column(String(50), nullable=False)
    key_name = Column(String(100), nullable=False)
    status = Column(String(20), default="pending")
    public_ip = Column(String(45), nullable=True)
    private_ip = Column(String(45), nullable=True)
    security_group_id = Column(String(50), nullable=True)
    vpc_id = Column(String(50), nullable=True)
    subnet_id = Column(String(50), nullable=True)
    az = Column(String(50), nullable=True)
    launch_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))