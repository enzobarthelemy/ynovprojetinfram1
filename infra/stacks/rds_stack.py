from aws_cdk import Stack
from constructs import Construct


class RdsStackPrimary(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: RDS MySQL Multi-AZ pour WordPress (port 3306 depuis sg_stack) — us-east-1


class RdsStackSecondary(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: RDS MySQL replica — us-west-2
