from aws_cdk import Stack
from constructs import Construct


class AlbStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: ALB + Target Group + Listener HTTPS
