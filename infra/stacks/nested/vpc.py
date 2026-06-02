from aws_cdk import NestedStack, aws_ec2 as ec2
from constructs import Construct


class VpcNested(NestedStack):
    """
    VPC en NestedStack. Expose les subnets/vpc comme attributs Python
    pour que les autres nested stacks les recoivent directement (pas de CfnParameter).

    cidr_prefix : "10.0" (prod) ou "10.1" (backup)
    azs         : ["us-east-1a", "us-east-1b"] ou ["us-west-2a", "us-west-2b"]
    name        : "Prod" ou "Backup"
    """

    def __init__(self, scope: Construct, construct_id: str, *,
                 cidr_prefix: str, azs: list, name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self, f"Vpc{name}",
            vpc_name=f"Vpc{name}",
            ip_addresses=ec2.IpAddresses.cidr(f"{cidr_prefix}.0.0/16"),
            availability_zones=azs,
            subnet_configuration=[],
        )

        igw = ec2.CfnInternetGateway(self, f"{name}IGW")
        ec2.CfnVPCGatewayAttachment(self, f"{name}IGWAttach",
            vpc_id=self.vpc.vpc_id,
            internet_gateway_id=igw.attr_internet_gateway_id,
        )

        # Subnets publics
        self.public_subnet_1 = ec2.PublicSubnet(self, f"{name}PublicAZ1",
            vpc_id=self.vpc.vpc_id, availability_zone=azs[0],
            cidr_block=f"{cidr_prefix}.1.0/24", map_public_ip_on_launch=True)
        self.public_subnet_2 = ec2.PublicSubnet(self, f"{name}PublicAZ2",
            vpc_id=self.vpc.vpc_id, availability_zone=azs[1],
            cidr_block=f"{cidr_prefix}.2.0/24", map_public_ip_on_launch=True)

        self.public_subnet_1.add_route(f"{name}PublicRoute1",
            router_id=igw.attr_internet_gateway_id, router_type=ec2.RouterType.GATEWAY)
        self.public_subnet_2.add_route(f"{name}PublicRoute2",
            router_id=igw.attr_internet_gateway_id, router_type=ec2.RouterType.GATEWAY)

        # Subnets web prives
        self.web_subnet_1 = ec2.PrivateSubnet(self, f"{name}WebAZ1",
            vpc_id=self.vpc.vpc_id, availability_zone=azs[0],
            cidr_block=f"{cidr_prefix}.11.0/24")
        self.web_subnet_2 = ec2.PrivateSubnet(self, f"{name}WebAZ2",
            vpc_id=self.vpc.vpc_id, availability_zone=azs[1],
            cidr_block=f"{cidr_prefix}.12.0/24")

        # Subnets DB prives
        self.db_subnet_1 = ec2.PrivateSubnet(self, f"{name}DbAZ1",
            vpc_id=self.vpc.vpc_id, availability_zone=azs[0],
            cidr_block=f"{cidr_prefix}.21.0/24")
        self.db_subnet_2 = ec2.PrivateSubnet(self, f"{name}DbAZ2",
            vpc_id=self.vpc.vpc_id, availability_zone=azs[1],
            cidr_block=f"{cidr_prefix}.22.0/24")

        # NAT Gateway + EIP
        eip = ec2.CfnEIP(self, f"{name}NatEip", domain="vpc")
        nat = ec2.CfnNatGateway(self, f"NAT{name.upper()}",
            subnet_id=self.public_subnet_1.subnet_id,
            allocation_id=eip.attr_allocation_id,
            tags=[{"key": "Name", "value": f"NAT{name.upper()}"}],
        )
        self.web_subnet_1.add_default_nat_route(nat.ref)
        self.web_subnet_2.add_default_nat_route(nat.ref)

        # Endpoint S3 (Gateway) pour les subnets web prives
        self.vpc.add_gateway_endpoint(f"{name}S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnets=[self.web_subnet_1, self.web_subnet_2])],
        )
