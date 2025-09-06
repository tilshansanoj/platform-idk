from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import logging

from .config import settings
from .databases import get_db, init_db
from .models import Deployment
from .schemas import DeploymentCreate, Deployment, DeploymentResponse, HealthCheck
from .aws import get_ec2_client, create_security_group
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EC2 Deployer API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await init_db()
    logger.info("Database initialized")

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "EC2 Deployer API"}

@app.get("/health", response_model=HealthCheck)
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Test database connection
        await db.execute("SELECT 1")
        return HealthCheck(status="healthy", database="connected")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )

@app.post("/api/deploy", response_model=DeploymentResponse)
async def deploy_instance(
    deployment: DeploymentCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        ec2_client = get_ec2_client()
        security_group_id = await create_security_group(ec2_client, f"sg-{deployment.instance_name.lower()}")
        
        # Create deployment record
        db_deployment = Deployment(
            instance_name=deployment.instance_name,
            instance_type=deployment.instance_type,
            ami_id=deployment.ami_id,
            key_name=deployment.key_name,
            status="pending",
            security_group_id=security_group_id
        )
        
        db.add(db_deployment)
        await db.commit()
        await db.refresh(db_deployment)
        
        # Launch EC2 instance
        response = ec2_client.run_instances(
            ImageId=deployment.ami_id,
            InstanceType=deployment.instance_type,
            KeyName=deployment.key_name,
            MinCount=1,
            MaxCount=1,
            SecurityGroupIds=[security_group_id],
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': deployment.instance_name},
                    {'Key': 'DeploymentID', 'Value': str(db_deployment.id)}
                ]
            }]
        )
        
        instance = response['Instances'][0]
        db_deployment.instance_id = instance['InstanceId']
        db_deployment.launch_time = instance.get('LaunchTime', datetime.now(timezone.utc))
        
        # Update instance details
        if 'PublicIpAddress' in instance:
            db_deployment.public_ip = instance['PublicIpAddress']
        if 'PrivateIpAddress' in instance:
            db_deployment.private_ip = instance['PrivateIpAddress']
        if 'SubnetId' in instance:
            db_deployment.subnet_id = instance['SubnetId']
        if 'VpcId' in instance:
            db_deployment.vpc_id = instance['VpcId']
        if 'Placement' in instance:
            db_deployment.az = instance['Placement'].get('AvailabilityZone')
        
        db_deployment.status = "running"
        await db.commit()
        
        logger.info(f"Successfully deployed instance {db_deployment.instance_id}")
        
        return DeploymentResponse(
            success=True,
            instance_id=db_deployment.instance_id,
            deployment_id=db_deployment.id,
            message=f"Instance {db_deployment.instance_id} launched successfully!"
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Deployment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/deployments", response_model=List[Deployment])
async def get_deployments(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Deployment).order_by(Deployment.created_at.desc()))
        deployments = result.scalars().all()
        return deployments
    except Exception as e:
        logger.error(f"Error fetching deployments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/deployments/{deployment_id}", response_model=Deployment)
async def get_deployment(deployment_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found"
            )
            
        return deployment
    except Exception as e:
        logger.error(f"Error fetching deployment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/deployments/{deployment_id}/sync", response_model=Deployment)
async def sync_deployment(deployment_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found"
            )
        
        ec2_client = get_ec2_client()
        response = ec2_client.describe_instances(InstanceIds=[deployment.instance_id])
        
        if response['Reservations'] and response['Reservations'][0]['Instances']:
            instance = response['Reservations'][0]['Instances'][0]
            deployment.status = instance['State']['Name']
            
            if 'PublicIpAddress' in instance:
                deployment.public_ip = instance['PublicIpAddress']
            if 'PrivateIpAddress' in instance:
                deployment.private_ip = instance['PrivateIpAddress']
            
            await db.commit()
            return deployment
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found in AWS"
            )
            
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.delete("/api/deployments/{deployment_id}")
async def terminate_deployment(deployment_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found"
            )
        
        ec2_client = get_ec2_client()
        ec2_client.terminate_instances(InstanceIds=[deployment.instance_id])
        
        deployment.status = "terminating"
        await db.commit()
        
        return {"success": True, "message": "Instance termination initiated"}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Termination error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )