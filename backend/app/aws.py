import boto3
from botocore.exceptions import ClientError
from .config import settings

def get_ec2_client():
    return boto3.client(
        'ec2',
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region
    )

async def create_security_group(ec2_client, group_name):
    try:
        response = ec2_client.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [group_name]}]
        )
        if response['SecurityGroups']:
            return response['SecurityGroups'][0]['GroupId']
    except ClientError:
        pass
    
    vpc_response = ec2_client.describe_vpcs()
    vpc_id = vpc_response['Vpcs'][0]['VpcId'] if vpc_response['Vpcs'] else None
    
    response = ec2_client.create_security_group(
        GroupName=group_name,
        Description='Security group for EC2 deployer application',
        VpcId=vpc_id
    )
    
    group_id = response['GroupId']
    
    ec2_client.authorize_security_group_ingress(
        GroupId=group_id,
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ]
    )
    
    return group_id