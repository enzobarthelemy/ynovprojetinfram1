from aws_cdk import Stack
from constructs import Construct


class VpcStackPrimary(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: VPC us-east-1 (10.0.0.0/16), subnets public/privés, IGW, route tables


class VpcStackSecondary(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: VPC us-west-2 (10.1.0.0/16), subnets public/privés, IGW, route tables
