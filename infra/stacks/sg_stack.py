from aws_cdk import Stack
from constructs import Construct


class SgStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: SG ALB (HTTPS public), SG Web (depuis ALB), SG RDS (MySQL depuis Web)
