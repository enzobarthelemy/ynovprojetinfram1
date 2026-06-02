from aws_cdk import (
    Stack,
    CfnOutput,
    aws_ec2 as ec2,
)
from constructs import Construct


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

        self.sub_public_1_prod = ec2.PublicSubnet(
            self, "ProdPublicSubnetAZ1",
            vpc_id=self.vpc_prod.vpc_id,
            availability_zone="us-east-1a",
            cidr_block="10.0.1.0/24",
            map_public_ip_on_launch=True
        )
        self.sub_public_2_prod = ec2.PublicSubnet(
            self, "ProdPublicSubnetAZ2",
            vpc_id=self.vpc_prod.vpc_id,
            availability_zone="us-east-1b",
            cidr_block="10.0.2.0/24",
            map_public_ip_on_launch=True
        )

        self.sub_public_1_prod.add_route(
            "ProdPublicRoute1",
            router_id=igw_prod.attr_internet_gateway_id,
            router_type=ec2.RouterType.GATEWAY
        )
        self.sub_public_2_prod.add_route(
            "ProdPublicRoute2",
            router_id=igw_prod.attr_internet_gateway_id,
            router_type=ec2.RouterType.GATEWAY
        )

        self.sub_private_1_prod = ec2.PrivateSubnet(
            self, "ProdPrivateSubnetWebAZ1",
            vpc_id=self.vpc_prod.vpc_id,
            availability_zone="us-east-1a",
            cidr_block="10.0.11.0/24"
        )
        self.sub_private_2_prod = ec2.PrivateSubnet(
            self, "ProdPrivateSubnetWebAZ2",
            vpc_id=self.vpc_prod.vpc_id,
            availability_zone="us-east-1b",
            cidr_block="10.0.12.0/24"
        )
        self.sub_private_3_prod = ec2.PrivateSubnet(
            self, "ProdPrivateSubnetDBAZ1",
            vpc_id=self.vpc_prod.vpc_id,
            availability_zone="us-east-1a",
            cidr_block="10.0.21.0/24"
        )
        self.sub_private_4_prod = ec2.PrivateSubnet(
            self, "ProdPrivateSubnetDBAZ2",
            vpc_id=self.vpc_prod.vpc_id,
            availability_zone="us-east-1b",
            cidr_block="10.0.22.0/24"
        )

        # NAT Gateway primaire (dans un subnet public) + EIP
        eip_prod = ec2.CfnEIP(self, "NatEipPrimary", domain="vpc")
        nat_prod = ec2.CfnNatGateway(self, "NATPRIMARY",
            subnet_id=self.sub_public_1_prod.subnet_id,
            allocation_id=eip_prod.attr_allocation_id,
            tags=[{"key": "Name", "value": "NATPRIMARY"}],
        )

        # Route 0.0.0.0/0 -> NATPRIMARY sur les subnets web privés
        self.sub_private_1_prod.add_default_nat_route(nat_prod.ref)
        self.sub_private_2_prod.add_default_nat_route(nat_prod.ref)

        # Endpoint S3 (Gateway) pour les sous-réseaux web privés
        self.vpc_prod.add_gateway_endpoint(
            "S3EndpointPrimary",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnets=[self.sub_private_1_prod, self.sub_private_2_prod])]
        )

        # Alias pour les autres stacks (SG, EFS, ASG, ALB)
        self.vpc = self.vpc_prod
        self.web_subnet_1 = self.sub_private_1_prod
        self.web_subnet_2 = self.sub_private_2_prod
        self.public_subnet_1 = self.sub_public_1_prod
        self.public_subnet_2 = self.sub_public_2_prod

        CfnOutput(self, "VpcId", value=self.vpc_prod.vpc_id)
        CfnOutput(self, "DbSubnet1Id", value=self.sub_private_3_prod.subnet_id)
        CfnOutput(self, "DbSubnet2Id", value=self.sub_private_4_prod.subnet_id)
        CfnOutput(self, "WebSubnet1Id", value=self.sub_private_1_prod.subnet_id)
        CfnOutput(self, "WebSubnet2Id", value=self.sub_private_2_prod.subnet_id)
        CfnOutput(self, "PublicSubnet1Id", value=self.sub_public_1_prod.subnet_id)
        CfnOutput(self, "PublicSubnet2Id", value=self.sub_public_2_prod.subnet_id)


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

        self.sub_public_1_backup = ec2.PublicSubnet(
            self, "BackupPublicSubnetAZ1",
            vpc_id=self.vpc_backup.vpc_id,
            availability_zone="us-west-2a",
            cidr_block="10.1.1.0/24",
            map_public_ip_on_launch=True
        )
        self.sub_public_2_backup = ec2.PublicSubnet(
            self, "BackupPublicSubnetAZ2",
            vpc_id=self.vpc_backup.vpc_id,
            availability_zone="us-west-2b",
            cidr_block="10.1.2.0/24",
            map_public_ip_on_launch=True
        )

        self.sub_public_1_backup.add_route(
            "BackupPublicRoute1",
            router_id=igw_backup.attr_internet_gateway_id,
            router_type=ec2.RouterType.GATEWAY
        )
        self.sub_public_2_backup.add_route(
            "BackupPublicRoute2",
            router_id=igw_backup.attr_internet_gateway_id,
            router_type=ec2.RouterType.GATEWAY
        )

        self.sub_private_1_backup = ec2.PrivateSubnet(
            self, "BackupPrivateSubnetWebAZ1",
            vpc_id=self.vpc_backup.vpc_id,
            availability_zone="us-west-2a",
            cidr_block="10.1.11.0/24"
        )
        self.sub_private_2_backup = ec2.PrivateSubnet(
            self, "BackupPrivateSubnetWebAZ2",
            vpc_id=self.vpc_backup.vpc_id,
            availability_zone="us-west-2b",
            cidr_block="10.1.12.0/24"
        )
        self.sub_private_3_backup = ec2.PrivateSubnet(
            self, "BackupPrivateSubnetDBAZ1",
            vpc_id=self.vpc_backup.vpc_id,
            availability_zone="us-west-2a",
            cidr_block="10.1.21.0/24"
        )
        self.sub_private_4_backup = ec2.PrivateSubnet(
            self, "BackupPrivateSubnetDBAZ2",
            vpc_id=self.vpc_backup.vpc_id,
            availability_zone="us-west-2b",
            cidr_block="10.1.22.0/24"
        )

        # NAT Gateway secondaire (dans un subnet public) + EIP
        eip_backup = ec2.CfnEIP(self, "NatEipSecondary", domain="vpc")
        nat_backup = ec2.CfnNatGateway(self, "NATSECONDARY",
            subnet_id=self.sub_public_1_backup.subnet_id,
            allocation_id=eip_backup.attr_allocation_id,
            tags=[{"key": "Name", "value": "NATSECONDARY"}],
        )

        # Route 0.0.0.0/0 -> NATSECONDARY sur les subnets web privés
        self.sub_private_1_backup.add_default_nat_route(nat_backup.ref)
        self.sub_private_2_backup.add_default_nat_route(nat_backup.ref)

        # Endpoint S3 (Gateway) pour les sous-réseaux web privés
        self.vpc_backup.add_gateway_endpoint(
            "S3EndpointSecondary",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnets=[self.sub_private_1_backup, self.sub_private_2_backup])]
        )

        # Alias pour les autres stacks (SG, EFS, ASG, ALB)
        self.vpc = self.vpc_backup
        self.web_subnet_1 = self.sub_private_1_backup
        self.web_subnet_2 = self.sub_private_2_backup
        self.public_subnet_1 = self.sub_public_1_backup
        self.public_subnet_2 = self.sub_public_2_backup

        CfnOutput(self, "VpcId", value=self.vpc_backup.vpc_id)
        CfnOutput(self, "DbSubnet1Id", value=self.sub_private_3_backup.subnet_id)
        CfnOutput(self, "DbSubnet2Id", value=self.sub_private_4_backup.subnet_id)
        CfnOutput(self, "WebSubnet1Id", value=self.sub_private_1_backup.subnet_id)
        CfnOutput(self, "WebSubnet2Id", value=self.sub_private_2_backup.subnet_id)
        CfnOutput(self, "PublicSubnet1Id", value=self.sub_public_1_backup.subnet_id)
        CfnOutput(self, "PublicSubnet2Id", value=self.sub_public_2_backup.subnet_id)
