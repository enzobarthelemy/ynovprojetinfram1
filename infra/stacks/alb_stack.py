from aws_cdk import Stack, CfnOutput, aws_elasticloadbalancingv2 as elbv2
from constructs import Construct


class AlbStackPrimary(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ALB public internet-facing dans les subnets publics
        alb = elbv2.CfnLoadBalancer(self, "Alb",
            name="wordpress-alb-primary",
            scheme="internet-facing",
            type="application",
            security_groups=[sg_stack.alb_sg.ref],
            subnets=[
                vpc_stack.public_subnet_1.subnet_id,
                vpc_stack.public_subnet_2.subnet_id,
            ],
        )

        # Target Group pour les instances WordPress (port 80)
        tg = elbv2.CfnTargetGroup(self, "TargetGroup",
            name="wordpress-tg-primary",
            port=80,
            protocol="HTTP",
            vpc_id=vpc_stack.vpc.vpc_id,
            target_type="instance",
            health_check_enabled=True,
            health_check_path="/",
            health_check_protocol="HTTP",
            health_check_interval_seconds=30,
            healthy_threshold_count=2,
            unhealthy_threshold_count=3,
        )

        # Listener HTTP 80 → forward vers le target group
        elbv2.CfnListener(self, "Listener",
            load_balancer_arn=alb.ref,
            port=80,
            protocol="HTTP",
            default_actions=[
                elbv2.CfnListener.ActionProperty(
                    type="forward",
                    target_group_arn=tg.ref,
                )
            ],
        )

        self.target_group_arn = tg.ref
        self.alb_arn = alb.ref
        self.alb_dns = alb.attr_dns_name

        CfnOutput(self, "AlbDnsName", value=alb.attr_dns_name)
        CfnOutput(self, "TargetGroupArn", value=tg.ref)


class AlbStackSecondary(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        alb = elbv2.CfnLoadBalancer(self, "Alb",
            name="wordpress-alb-secondary",
            scheme="internet-facing",
            type="application",
            security_groups=[sg_stack.alb_sg.ref],
            subnets=[
                vpc_stack.public_subnet_1.subnet_id,
                vpc_stack.public_subnet_2.subnet_id,
            ],
        )

        tg = elbv2.CfnTargetGroup(self, "TargetGroup",
            name="wordpress-tg-secondary",
            port=80,
            protocol="HTTP",
            vpc_id=vpc_stack.vpc.vpc_id,
            target_type="instance",
            health_check_enabled=True,
            health_check_path="/",
            health_check_protocol="HTTP",
            health_check_interval_seconds=30,
            healthy_threshold_count=2,
            unhealthy_threshold_count=3,
        )

        elbv2.CfnListener(self, "Listener",
            load_balancer_arn=alb.ref,
            port=80,
            protocol="HTTP",
            default_actions=[
                elbv2.CfnListener.ActionProperty(
                    type="forward",
                    target_group_arn=tg.ref,
                )
            ],
        )

        self.target_group_arn = tg.ref
        self.alb_arn = alb.ref
        self.alb_dns = alb.attr_dns_name

        CfnOutput(self, "AlbDnsName", value=alb.attr_dns_name)
        CfnOutput(self, "TargetGroupArn", value=tg.ref)
