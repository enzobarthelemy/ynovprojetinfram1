from aws_cdk import (
    Stack,
    CfnOutput,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2
)

from aws_cdk import Stack, CfnOutput, aws_elasticloadbalancingv2 as elbv2
from constructs import Construct

class AlbStackPrimary(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. On importe et convertit le SG de ton collègue (alb_sg) pour qu'il soit compatible
        sg_alb_l2 = ec2.SecurityGroup.from_security_group_id(
            self, "ImportedSgAlbPrimary",
            security_group_id=sg_stack.alb_sg.ref
        )

        # 2. Création de l'ALB public avec le SG converti
        self.load_balancer = elbv2.ApplicationLoadBalancer(
            self, "AlbPrimary",
            vpc=vpc_stack.vpc_prod,
            internet_facing=True,
            security_group=sg_alb_l2, # <-- Utilisation du SG converti
            vpc_subnets=ec2.SubnetSelection(subnets=[
                vpc_stack.sub_public_1_prod, 
                vpc_stack.sub_public_2_prod
            ])
        )

        # 3. Création du Target Group
        self.target_group = elbv2.ApplicationTargetGroup(
            self, "TargetGroupPrimary",
            vpc=vpc_stack.vpc_prod,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.INSTANCE,
            health_check=elbv2.HealthCheck(
                path="/",
                port="80",
                healthy_http_codes="200-399"
            )
        )

        # 4. Création du Listener
        self.listener = self.load_balancer.add_listener(
            "ListenerPrimary",
            port=80,
            open=True,
            default_target_groups=[self.target_group]
        )

        CfnOutput(self, "AlbPrimaryDns", value=self.load_balancer.load_balancer_dns_name)

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

        # 1. On importe et convertit le SG de secours
        sg_alb_l2_secondary = ec2.SecurityGroup.from_security_group_id(
            self, "ImportedSgAlbSecondary",
            security_group_id=sg_stack.alb_sg.ref
        )

        # 2. Création de l'ALB de secours
        self.load_balancer = elbv2.ApplicationLoadBalancer(
            self, "AlbSecondary",
            vpc=vpc_stack.vpc_backup,
            internet_facing=True,
            security_group=sg_alb_l2_secondary, # <-- Utilisation du SG converti
            vpc_subnets=ec2.SubnetSelection(subnets=[
                vpc_stack.sub_public_1_backup, 
                vpc_stack.sub_public_2_backup
            ])
        )

        # 3. Création du Target Group de secours
        self.target_group = elbv2.ApplicationTargetGroup(
            self, "TargetGroupSecondary",
            vpc=vpc_stack.vpc_backup,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.INSTANCE,
            health_check=elbv2.HealthCheck(
                path="/",
                port="80",
                healthy_http_codes="200-399"
            )
        )

        # 4. Création du Listener de secours
        self.listener = self.load_balancer.add_listener(
            "ListenerSecondary",
            port=80,
            open=True,
            default_target_groups=[self.target_group]
        )

        CfnOutput(self, "AlbSecondaryDns", value=self.load_balancer.load_balancer_dns_name)

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
        