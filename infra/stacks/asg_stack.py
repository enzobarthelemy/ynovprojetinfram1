from aws_cdk import Stack
from constructs import Construct


class AsgStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, sg_stack, alb_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: Auto Scaling Group + politiques de scaling + stress test
