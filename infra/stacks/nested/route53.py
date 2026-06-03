from aws_cdk import (
    NestedStack,
    aws_route53 as route53,
    CfnOutput,
)
from constructs import Construct


class Route53Nested(NestedStack):
    """
    Cree la hosted zone publique ynov-infram1-grp1.com ET la strategie de trafic
    Failover sur sub.ynov-infram1-grp1.com.

    PRIMARY   -> ALB us-east-1
    SECONDARY -> ALB us-west-2
    Health checks HTTP sur chaque ALB : bascule auto vers SECONDARY si PRIMARY unhealthy.
    """

    FQDN = "sub.ynov-infram1-grp1.com"

    def __init__(self, scope: Construct, construct_id: str, *,
                 alb_dns_primary: str, alb_dns_secondary: str,
                 alb_zone_id_primary: str, alb_zone_id_secondary: str,
                 name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Hosted zone publique
        hosted_zone = route53.CfnHostedZone(self, "HostedZone",
            name="ynov-infram1-grp1.com",
            hosted_zone_config=route53.CfnHostedZone.HostedZoneConfigProperty(
                comment=f"Zone publique geree par CDK - stack {name}"),
        )

        # 2. Health checks sur chaque ALB (HTTP 80, path /)
        hc_primary = route53.CfnHealthCheck(self, "HealthCheckPrimary",
            health_check_config=route53.CfnHealthCheck.HealthCheckConfigProperty(
                type="HTTP", fully_qualified_domain_name=alb_dns_primary,
                port=80, resource_path="/", request_interval=10,
                failure_threshold=3, measure_latency=True),
            health_check_tags=[route53.CfnHealthCheck.HealthCheckTagProperty(
                key="Name", value=f"hc-primary-{name}")],
        )
        hc_secondary = route53.CfnHealthCheck(self, "HealthCheckSecondary",
            health_check_config=route53.CfnHealthCheck.HealthCheckConfigProperty(
                type="HTTP", fully_qualified_domain_name=alb_dns_secondary,
                port=80, resource_path="/", request_interval=30,
                failure_threshold=3, measure_latency=True),
            health_check_tags=[route53.CfnHealthCheck.HealthCheckTagProperty(
                key="Name", value=f"hc-secondary-{name}")],
        )

        # 3. Strategie de trafic - enregistrement Failover PRIMARY (Alias ALB us-east-1)
        route53.CfnRecordSet(self, "FailoverRecordPrimary",
            hosted_zone_id=hosted_zone.ref,
            name=self.FQDN,
            type="A",
            alias_target=route53.CfnRecordSet.AliasTargetProperty(
                dns_name=alb_dns_primary, hosted_zone_id=alb_zone_id_primary,
                evaluate_target_health=True),
            failover="PRIMARY",
            set_identifier=f"primary-{name}",
            health_check_id=hc_primary.ref,
        )

        # 4. Strategie de trafic - enregistrement Failover SECONDARY (Alias ALB us-west-2)
        route53.CfnRecordSet(self, "FailoverRecordSecondary",
            hosted_zone_id=hosted_zone.ref,
            name=self.FQDN,
            type="A",
            alias_target=route53.CfnRecordSet.AliasTargetProperty(
                dns_name=alb_dns_secondary, hosted_zone_id=alb_zone_id_secondary,
                evaluate_target_health=True),
            failover="SECONDARY",
            set_identifier=f"secondary-{name}",
            health_check_id=hc_secondary.ref,
        )

        self.hosted_zone_id = hosted_zone.ref
        self.web_fqdn = self.FQDN

        CfnOutput(self, "HostedZoneId", value=hosted_zone.ref)
        CfnOutput(self, "WebRecordFQDN", value=self.FQDN)
        CfnOutput(self, "NameServers",
            value="Voir Route53 console (DelegationSet) - a deleguer chez le registrar")
