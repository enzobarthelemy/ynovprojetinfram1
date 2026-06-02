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

        # ------------------------------------------------------------------
        # AJOUTS RESEAU : NAT Gateway et S3 Endpoint (Primary)
        # ------------------------------------------------------------------
        
        # 1. Création de l'EIP et du NAT Gateway
        eip_prod = ec2.CfnEIP(self, "EipPrimary")
        nat_prod = ec2.CfnNatGateway(self, "NatPrimary",
            allocation_id=eip_prod.attr_allocation_id,
            subnet_id=self.sub_public_1_prod.subnet_id
        )

        # 2. Routes des sous-réseaux Web (EC2) vers le NAT Gateway
        self.sub_private_1_prod.add_route("NatRouteWebPrimary1",
            router_id=nat_prod.ref,
            router_type=ec2.RouterType.NAT_GATEWAY,
            destination_cidr_block="0.0.0.0/0"
        )
        self.sub_private_2_prod.add_route("NatRouteWebPrimary2",
            router_id=nat_prod.ref,
            router_type=ec2.RouterType.NAT_GATEWAY,
            destination_cidr_block="0.0.0.0/0"
        )

        # 3. Endpoint S3 
        self.vpc_prod.add_gateway_endpoint(
            "S3EndpointPrimary",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnets=[self.sub_private_1_prod, self.sub_private_2_prod])]
        )
        
        # ------------------------------------------------------------------
        # RESOLUTION DU CONFLIT GIT : Export des variables pour les collègues
        # ------------------------------------------------------------------
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

        # ------------------------------------------------------------------
        # AJOUTS RESEAU : NAT Gateway et S3 Endpoint (Secondary)
        # ------------------------------------------------------------------
        
        # 1. Création de l'EIP et du NAT Gateway
        eip_backup = ec2.CfnEIP(self, "EipSecondary")
        nat_backup = ec2.CfnNatGateway(self, "NatSecondary",
            allocation_id=eip_backup.attr_allocation_id,
            subnet_id=self.sub_public_1_backup.subnet_id
        )

        # 2. Routes des sous-réseaux Web (EC2) vers le NAT Gateway
        self.sub_private_1_backup.add_route("NatRouteWebSecondary1",
            router_id=nat_backup.ref,
            router_type=ec2.RouterType.NAT_GATEWAY,
            destination_cidr_block="0.0.0.0/0"
        )
        self.sub_private_2_backup.add_route("NatRouteWebSecondary2",
            router_id=nat_backup.ref,
            router_type=ec2.RouterType.NAT_GATEWAY,
            destination_cidr_block="0.0.0.0/0"
        )

        # 3. Endpoint S3
        self.vpc_backup.add_gateway_endpoint(
            "S3EndpointSecondary",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnets=[self.sub_private_1_backup, self.sub_private_2_backup])]
        )

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