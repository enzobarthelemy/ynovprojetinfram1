from aws_cdk import Stack
from constructs import Construct


class SgStackPrimary(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: SG ALB (HTTPS public), SG Web (depuis ALB), SG RDS (3306 depuis Web) — us-east-1


class SgStackSecondary(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: Mêmes SG que Primary — us-west-2
