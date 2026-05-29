from aws_cdk import Stack
from constructs import Construct


class Ec2Stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: 2-3 EC2 Linux t2.micro + Docker WordPress/WooCommerce