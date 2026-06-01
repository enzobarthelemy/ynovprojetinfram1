from aws_cdk import (
    Stack,
    CfnOutput,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2
)
from constructs import Construct

class AlbStackPrimary(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Création de l'ALB public en ciblant les variables des autres stacks
        self.load_balancer = elbv2.ApplicationLoadBalancer(
            self, "AlbPrimary",
            vpc=vpc_stack.ec2.Vpc,
            internet_facing=True,
            security_group=sg_stack.sg_alb,
            # On place l'ALB spécifiquement dans les subnets publics nommés
            vpc_subnets=ec2.SubnetSelection(subnets=[
                vpc_stack.sub_public_1_prod, 
                vpc_stack.sub_public_2_prod
            ])
        )

        # 2. Création du Target Group (Cible) pour l'Auto Scaling Group
        self.target_group = elbv2.ApplicationTargetGroup(
            self, "TargetGroupPrimary",
            vpc=vpc_stack.ec2.Vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.INSTANCE,
            health_check=elbv2.HealthCheck(
                path="/",
                port="80",
                healthy_http_codes="200-399"
            )
        )

        # 3. Création du Listener
        self.listener = self.load_balancer.add_listener(
            "ListenerPrimary",
            port=80,
            open=True,
            default_target_groups=[self.target_group]
        )

        CfnOutput(self, "AlbPrimaryDns", value=self.load_balancer.load_balancer_dns_name)


class AlbStackSecondary(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Création de l'ALB de secours
        self.load_balancer = elbv2.ApplicationLoadBalancer(
            self, "AlbSecondary",
            vpc=vpc_stack.vpc_backup,
            internet_facing=True,
            security_group=sg_stack.sg_alb,
            vpc_subnets=ec2.SubnetSelection(subnets=[
                vpc_stack.sub_public_1_backup, 
                vpc_stack.sub_public_2_backup
            ])
        )

        # 2. Création du Target Group de secours
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

        # 3. Création du Listener de secours
        self.listener = self.load_balancer.add_listener(
            "ListenerSecondary",
            port=80,
            open=True,
            default_target_groups=[self.target_group]
        )

        CfnOutput(self, "AlbSecondaryDns", value=self.load_balancer.load_balancer_dns_name)