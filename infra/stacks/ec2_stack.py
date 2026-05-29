from aws_cdk import Stack
from constructs import Construct


class Ec2StackPrimary(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: 2 EC2 Linux t2.micro + Docker WordPress/WooCommerce — us-east-1


class Ec2StackSecondary(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: 2 EC2 Linux t2.micro + Docker WordPress/WooCommerce — us-west-2
