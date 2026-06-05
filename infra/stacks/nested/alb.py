from aws_cdk import NestedStack, aws_elasticloadbalancingv2 as elbv2
from constructs import Construct


class AlbNested(NestedStack):
    """
    ALB public (L1) + Target Group + Listener HTTP 80.
    Recoit vpc_id, public_subnet_ids, alb_sg_id directement.
    Expose target_group_arn et alb_dns.
    """

    def __init__(self, scope: Construct, construct_id: str, *,
                 vpc_id: str, public_subnet_ids: list, alb_sg_id: str,
                 name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        alb = elbv2.CfnLoadBalancer(self, "Alb",
            name=f"wp-alb-{name}",
            scheme="internet-facing",
            type="application",
            security_groups=[alb_sg_id],
            subnets=public_subnet_ids,
        )

        tg = elbv2.CfnTargetGroup(self, "TargetGroup",
            name=f"wp-tg-{name}",
            port=80,
            protocol="HTTP",
            vpc_id=vpc_id,
            target_type="instance",
            health_check_enabled=True,
            health_check_path="/",
            health_check_protocol="HTTP",
            health_check_interval_seconds=5,
            health_check_timeout_seconds=2,   # doit etre < a l'intervalle (5s)
            healthy_threshold_count=2,
            unhealthy_threshold_count=2,
        )

        elbv2.CfnListener(self, "Listener",
            load_balancer_arn=alb.ref,
            port=80,
            protocol="HTTP",
            default_actions=[elbv2.CfnListener.ActionProperty(
                type="forward", target_group_arn=tg.ref)],
        )

        self.target_group_arn = tg.ref
        self.alb_dns = alb.attr_dns_name
