from aws_cdk import Stack
from constructs import Construct


class VpcStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: VPC, subnets public/privés, IGW, route tables
