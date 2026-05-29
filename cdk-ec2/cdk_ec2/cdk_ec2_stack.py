import os
from aws_cdk import Stack, CfnOutput, aws_ec2 as ec2
from constructs import Construct


class CdkEc2Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.CfnVPC(self, "Vpc", cidr_block="10.0.0.0/16")

        igw = ec2.CfnInternetGateway(self, "IGW")
        ec2.CfnVPCGatewayAttachment(self, "IGWAttach",
            vpc_id=vpc.ref,
            internet_gateway_id=igw.ref,
        )

        subnet = ec2.CfnSubnet(self, "Subnet",
            vpc_id=vpc.ref,
            cidr_block="10.0.1.0/24",
            availability_zone="us-east-1a",
            map_public_ip_on_launch=True,
        )

        rt = ec2.CfnRouteTable(self, "RT", vpc_id=vpc.ref)
        ec2.CfnRoute(self, "DefaultRoute",
            route_table_id=rt.ref,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=igw.ref,
        )
        ec2.CfnSubnetRouteTableAssociation(self, "RTAssoc",
            subnet_id=subnet.ref,
            route_table_id=rt.ref,
        )

        sg = ec2.CfnSecurityGroup(self, "SG",
            vpc_id=vpc.ref,
            group_description="Allow SSH and HTTP",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=22, to_port=22, cidr_ip="0.0.0.0/0",
                ),
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=80, to_port=80, cidr_ip="0.0.0.0/0",
                ),
            ],
        )

        ami_id = os.getenv("AMI_ID", "ami-0c02fb55956c7d316")

        instance = ec2.CfnInstance(self, "EC2",
            instance_type="t2.micro",
            image_id=ami_id,
            subnet_id=subnet.ref,
            security_group_ids=[sg.ref],
        )

        CfnOutput(self, "PublicIP",
            value=instance.attr_public_ip,
            description="EC2 Public IP",
        )
