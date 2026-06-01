from aws_cdk import (
    Stack,
    CfnOutput,
    aws_ec2 as ec2,
)
from constructs import Construct

# v2 - ajout outputs subnets
class VpcStackPrimary(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ------------------------------------------------------------------
        # VPC 1 : PRODUCTION (10.0.0.0/16)         
        # ------------------------------------------------------------------
        self.vpc_prod = ec2.Vpc(
            self, "VpcProduction",
            vpc_name="VpcProduction",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            availability_zones=["us-east-1a", "us-east-1b"],
            subnet_configuration=[]
        )
            
        igw_prod = ec2.CfnInternetGateway(self, "ProdIGW")
        ec2.CfnVPCGatewayAttachment(
            self, "ProdIGWAttachment",
            vpc_id=self.vpc_prod.vpc_id,
            internet_gateway_id=igw_prod.attr_internet_gateway_id
        )

        sub_public_1_prod = ec2.PublicSubnet(
            self, "ProdPublicSubnetAZ1",
            vpc_id=self.vpc_prod.vpc_id,
            availability_zone="us-east-1a",
            cidr_block="10.0.1.0/24",
            map_public_ip_on_launch=True
        )
        sub_public_2_prod = ec2.PublicSubnet(
            self, "ProdPublicSubnetAZ2",
            vpc_id=self.vpc_prod.vpc_id,
            availability_zone="us-east-1b",
            cidr_block="10.0.2.0/24",
            map_public_ip_on_launch=True
        )
        
        sub_public_1_prod.add_route(
            "ProdPublicRoute1",
            router_id=igw_prod.attr_internet_gateway_id,
            router_type=ec2.RouterType.GATEWAY
        )
        sub_public_2_prod.add_route(
            "ProdPublicRoute2",
            router_id=igw_prod.attr_internet_gateway_id,
            router_type=ec2.RouterType.GATEWAY
        )
        
        sub_private_1_prod = ec2.PrivateSubnet(
            self, "ProdPrivateSubnetWebAZ1",
            vpc_id=self.vpc_prod.vpc_id,
            availability_zone="us-east-1a",
            cidr_block="10.0.11.0/24"
        )
        sub_private_2_prod = ec2.PrivateSubnet(
            self, "ProdPrivateSubnetWebAZ2",
            vpc_id=self.vpc_prod.vpc_id,
            availability_zone="us-east-1b",
            cidr_block="10.0.12.0/24"
        )
        sub_private_3_prod = ec2.PrivateSubnet(
            self, "ProdPrivateSubnetDBAZ1",
            vpc_id=self.vpc_prod.vpc_id,
            availability_zone="us-east-1a",
            cidr_block="10.0.21.0/24"
        )
        sub_private_4_prod = ec2.PrivateSubnet(
            self, "ProdPrivateSubnetDBAZ2",
            vpc_id=self.vpc_prod.vpc_id,
            availability_zone="us-east-1b",
            cidr_block="10.0.22.0/24"
        )

        self.vpc = self.vpc_prod
        self.web_subnet_1 = sub_private_1_prod
        self.web_subnet_2 = sub_private_2_prod
        self.public_subnet_1 = sub_public_1_prod
        self.public_subnet_2 = sub_public_2_prod

        CfnOutput(self, "VpcId", value=self.vpc_prod.vpc_id)
        CfnOutput(self, "DbSubnet1Id", value=sub_private_3_prod.subnet_id)
        CfnOutput(self, "DbSubnet2Id", value=sub_private_4_prod.subnet_id)
        CfnOutput(self, "WebSubnet1Id", value=sub_private_1_prod.subnet_id)
        CfnOutput(self, "WebSubnet2Id", value=sub_private_2_prod.subnet_id)
        CfnOutput(self, "PublicSubnet1Id", value=sub_public_1_prod.subnet_id)
        CfnOutput(self, "PublicSubnet2Id", value=sub_public_2_prod.subnet_id)


class VpcStackSecondary(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ------------------------------------------------------------------
        # VPC 2 : BACKUP (10.1.0.0/16)   
        # ------------------------------------------------------------------
        self.vpc_backup = ec2.Vpc(
            self, "VpcBackup",
            vpc_name="VpcBackup",
            ip_addresses=ec2.IpAddresses.cidr("10.1.0.0/16"),
            availability_zones=["us-west-2a", "us-west-2b"],
            subnet_configuration=[]
        )
            
        igw_backup = ec2.CfnInternetGateway(self, "BackupIGW")
        ec2.CfnVPCGatewayAttachment(
            self, "BackupIGWAttachment",
            vpc_id=self.vpc_backup.vpc_id,
            internet_gateway_id=igw_backup.attr_internet_gateway_id
        )

        sub_public_1_backup = ec2.PublicSubnet(
            self, "BackupPublicSubnetAZ1",
            vpc_id=self.vpc_backup.vpc_id, # Corrigé
            availability_zone="us-west-2a",
            cidr_block="10.1.1.0/24",
            map_public_ip_on_launch=True
        )
        sub_public_2_backup = ec2.PublicSubnet(
            self, "BackupPublicSubnetAZ2",
            vpc_id=self.vpc_backup.vpc_id, # Corrigé
            availability_zone="us-west-2b",
            cidr_block="10.1.2.0/24",
            map_public_ip_on_launch=True
        )
            
        sub_public_1_backup.add_route(
            "BackupPublicRoute1",
            router_id=igw_backup.attr_internet_gateway_id,
            router_type=ec2.RouterType.GATEWAY
        )
        sub_public_2_backup.add_route(
            "BackupPublicRoute2",
            router_id=igw_backup.attr_internet_gateway_id,
            router_type=ec2.RouterType.GATEWAY
        )
        
        sub_private_1_backup = ec2.PrivateSubnet(
            self, "BackupPrivateSubnetWebAZ1",
            vpc_id=self.vpc_backup.vpc_id, # Corrigé
            availability_zone="us-west-2a",
            cidr_block="10.1.11.0/24"
        )
        sub_private_2_backup = ec2.PrivateSubnet(
            self, "BackupPrivateSubnetWebAZ2",
            vpc_id=self.vpc_backup.vpc_id, # Corrigé
            availability_zone="us-west-2b",
            cidr_block="10.1.12.0/24"
        )
        sub_private_3_backup = ec2.PrivateSubnet(
            self, "BackupPrivateSubnetDBAZ1",
            vpc_id=self.vpc_backup.vpc_id, # Corrigé
            availability_zone="us-west-2a",
            cidr_block="10.1.21.0/24"
        )
        sub_private_4_backup = ec2.PrivateSubnet(
            self, "BackupPrivateSubnetDBAZ2",
            vpc_id=self.vpc_backup.vpc_id,
            availability_zone="us-west-2b",
            cidr_block="10.1.22.0/24"
        )

        self.vpc = self.vpc_backup
        self.web_subnet_1 = sub_private_1_backup
        self.web_subnet_2 = sub_private_2_backup
        self.public_subnet_1 = sub_public_1_backup
        self.public_subnet_2 = sub_public_2_backup

        CfnOutput(self, "VpcId", value=self.vpc_backup.vpc_id)
        CfnOutput(self, "DbSubnet1Id", value=sub_private_3_backup.subnet_id)
        CfnOutput(self, "DbSubnet2Id", value=sub_private_4_backup.subnet_id)
        CfnOutput(self, "WebSubnet1Id", value=sub_private_1_backup.subnet_id)
        CfnOutput(self, "WebSubnet2Id", value=sub_private_2_backup.subnet_id)
        CfnOutput(self, "PublicSubnet1Id", value=sub_public_1_backup.subnet_id)
        CfnOutput(self, "PublicSubnet2Id", value=sub_public_2_backup.subnet_id)