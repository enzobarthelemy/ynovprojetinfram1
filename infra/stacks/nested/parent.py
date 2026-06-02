from aws_cdk import Stack
from constructs import Construct

from stacks.nested.vpc import VpcNested
from stacks.nested.sg import SgNested
from stacks.nested.rds import RdsNested
from stacks.nested.efs import EfsNested
from stacks.nested.alb import AlbNested
from stacks.nested.asg import AsgNested
from stacks.nested.s3 import S3PrimaryNested, S3SecondaryNested
from stacks.nested.backup import BackupVaultNested, BackupPlanNested
from stacks.nested.route53 import Route53Nested


class InfraStack(Stack):
    """
    Stack parent (un par region) contenant tous les nested stacks.
    CloudFormation ordonne automatiquement via les dependances.

    is_primary=True  -> us-east-1 : RDS Multi-AZ + S3 primary (CRR) + Route53 failover
    is_primary=False -> us-west-2 : RDS standalone + S3 secondary (cible CRR)

    Le site est servi sous le FQDN web.ynov-infram1-grp1.com (Route53 failover),
    identique dans les 2 regions pour permettre la bascule.
    alb_dns_secondary : DNS de l'ALB secondaire, passe au primary (via contexte)
    pour les records Route53 failover. Si absent, Route53 n'est pas cree.
    """

    # FQDN public servi par WordPress (siteurl identique dans les 2 regions)
    WEB_FQDN = "web.ynov-infram1-grp1.com"

    # Hosted Zone IDs fixes des ALB par region (AWS)
    _ALB_HZ = {"us-east-1": "Z35SXDOTRQ7X7K", "us-west-2": "Z1H1FL5HABSF5"}

    def __init__(self, scope: Construct, construct_id: str, *,
                 region_kind: str, cidr_prefix: str, azs: list,
                 db_password: str, is_primary: bool, account_id: str,
                 alb_dns_secondary: str | None = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        rds_name = "primary" if is_primary else "secondary"

        # 1. VPC
        self.vpc = VpcNested(self, "Vpc",
            cidr_prefix=cidr_prefix, azs=azs, name=region_kind)

        # 2. Security Groups
        self.sg = SgNested(self, "Sg",
            vpc_id=self.vpc.vpc.vpc_id, name=region_kind)

        # 3. RDS
        self.rds = RdsNested(self, "Rds",
            db_subnet_ids=[self.vpc.db_subnet_1.subnet_id, self.vpc.db_subnet_2.subnet_id],
            db_sg_id=self.sg.rds_sg.ref,
            db_password=db_password,
            name=rds_name, multi_az=is_primary)

        # 4. EFS (independant par region ; DR cross-region via job AWS Backup)
        self.efs = EfsNested(self, "Efs",
            web_subnet_ids=[self.vpc.web_subnet_1.subnet_id, self.vpc.web_subnet_2.subnet_id],
            efs_sg_id=self.sg.efs_sg.ref, name=rds_name)

        # 5. ALB
        self.alb = AlbNested(self, "Alb",
            vpc_id=self.vpc.vpc.vpc_id,
            public_subnet_ids=[self.vpc.public_subnet_1.subnet_id, self.vpc.public_subnet_2.subnet_id],
            alb_sg_id=self.sg.alb_sg.ref, name=rds_name)

        # 6. ASG (user_data : EFS_ID + RDS_HOST injectes via tokens)
        self.asg = AsgNested(self, "Asg",
            web_subnet_ids=[self.vpc.web_subnet_1.subnet_id, self.vpc.web_subnet_2.subnet_id],
            asg_sg_id=self.sg.asg_sg.ref,
            target_group_arn=self.alb.target_group_arn,
            efs_id=self.efs.file_system_id,
            rds_host=self.rds.endpoint,
            alb_dns=self.alb.alb_dns,
            site_fqdn=self.WEB_FQDN,
            name=rds_name)

        # 7. S3 : primaire (CRR) ou secondaire (cible) selon la region
        if is_primary:
            self.s3 = S3PrimaryNested(self, "S3", account_id=account_id)
        else:
            self.s3 = S3SecondaryNested(self, "S3", account_id=account_id)

        # 8. AWS Backup natif (DR EFS cross-region, gere par AWS - aucun job)
        vault_name = "ynov-efs-vault"
        if is_primary:
            # Plan planifie + copie cross-region vers us-west-2
            self.backup = BackupPlanNested(self, "Backup",
                efs_id=self.efs.file_system_id,
                account_id=account_id,
                vault_name=vault_name,
                secondary_region="us-west-2")
            self.backup.add_dependency(self.efs)
        else:
            # Vault destination (cible de la copie cross-region)
            self.backup = BackupVaultNested(self, "Backup", vault_name=vault_name)

        # 9. Route53 failover (uniquement sur le primary, si l'ALB secondaire est connu)
        #    alb_dns_secondary est fourni au deploy via le contexte CDK (pas de ref cross-region)
        if is_primary and alb_dns_secondary:
            self.route53 = Route53Nested(self, "Route53",
                alb_dns_primary=self.alb.alb_dns,
                alb_dns_secondary=alb_dns_secondary,
                alb_zone_id_primary=self._ALB_HZ["us-east-1"],
                alb_zone_id_secondary=self._ALB_HZ["us-west-2"],
                name=rds_name)
            self.route53.add_dependency(self.alb)
