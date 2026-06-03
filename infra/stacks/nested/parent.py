from aws_cdk import Stack
from constructs import Construct

from stacks.nested.vpc import VpcNested
from stacks.nested.sg import SgNested
from stacks.nested.rds import RdsNested
from stacks.nested.efs import EfsNested
from stacks.nested.alb import AlbNested
from stacks.nested.asg import AsgNested
from stacks.nested.s3 import S3PrimaryNested, S3SecondaryNested
from stacks.nested.route53 import Route53Nested


class InfraStack(Stack):
    """
    Stack parent (un par region).

    PRIMARY (is_primary=True, us-east-1) :
        RDS Multi-AZ + EFS (replication read-only vers us-west-2) + ASG + S3 (CRR) + Route53.

    SECONDARY (is_primary=False, us-west-2) - COLD STANDBY, deploye en 2 passes :
        Pass 1 (replica_fs_id absent) : VPC + SG + RDS subnet group + ALB + S3 cible.
        Pass 2 (replica_fs_id fourni) : ajoute EFS (montage du replica) + ASG.
        -> le replica EFS et la DB (restauree) ne servent qu'au failover.

    Contexte fourni au deploy (pas de ref cross-region CDK) :
        alb_dns_secondary : DNS ALB secondaire (pour Route53 failover sur le primary)
        replica_fs_id     : ID du FS EFS replique (pour l'EFS du secondary, pass 2)
    """

    WEB_FQDN = "sub.ynov-infram1-grp1.com"
    _ALB_HZ = {"us-east-1": "Z35SXDOTRQ7X7K", "us-west-2": "Z1H1FL5HABSF5"}

    def __init__(self, scope: Construct, construct_id: str, *,
                 region_kind: str, cidr_prefix: str, azs: list,
                 db_password: str, is_primary: bool, account_id: str,
                 alb_dns_secondary: str | None = None,
                 replica_fs_id: str | None = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        rds_name = "primary" if is_primary else "secondary"

        # 1. VPC
        self.vpc = VpcNested(self, "Vpc",
            cidr_prefix=cidr_prefix, azs=azs, name=region_kind)

        # 2. Security Groups
        self.sg = SgNested(self, "Sg",
            vpc_id=self.vpc.vpc.vpc_id, name=region_kind)

        # 3. RDS : primary = instance Multi-AZ ; secondary = subnet group seul (cold standby)
        self.rds = RdsNested(self, "Rds",
            db_subnet_ids=[self.vpc.db_subnet_1.subnet_id, self.vpc.db_subnet_2.subnet_id],
            db_sg_id=self.sg.rds_sg.ref,
            db_password=db_password,
            name=rds_name, multi_az=is_primary,
            create_instance=is_primary)

        # 4. ALB (toujours - le secondary ALB est requis des la pass 1 pour Route53)
        self.alb = AlbNested(self, "Alb",
            vpc_id=self.vpc.vpc.vpc_id,
            public_subnet_ids=[self.vpc.public_subnet_1.subnet_id, self.vpc.public_subnet_2.subnet_id],
            alb_sg_id=self.sg.alb_sg.ref, name=rds_name)

        # 5. S3 : primaire (CRR) ou secondaire (cible)
        if is_primary:
            self.s3 = S3PrimaryNested(self, "S3", account_id=account_id)
        else:
            self.s3 = S3SecondaryNested(self, "S3", account_id=account_id)

        # 6. EFS + ASG
        #    primary   : EFS avec replication + ASG (toujours)
        #    secondary : seulement en pass 2 (replica_fs_id fourni) -> monte le replica
        create_compute = is_primary or bool(replica_fs_id)
        if create_compute:
            if is_primary:
                self.efs = EfsNested(self, "Efs",
                    web_subnet_ids=[self.vpc.web_subnet_1.subnet_id, self.vpc.web_subnet_2.subnet_id],
                    efs_sg_id=self.sg.efs_sg.ref, name=rds_name,
                    replicate_to_region="us-west-2")
                efs_id = self.efs.file_system_id
                rds_host = self.rds.endpoint
            else:
                # Secondary : monte le FS replique (read-only ; promu au failover)
                self.efs = EfsNested(self, "Efs",
                    web_subnet_ids=[self.vpc.web_subnet_1.subnet_id, self.vpc.web_subnet_2.subnet_id],
                    efs_sg_id=self.sg.efs_sg.ref, name=rds_name,
                    replica_fs_id=replica_fs_id)
                efs_id = replica_fs_id
                rds_host = ""   # DB via secret au failover

            self.asg = AsgNested(self, "Asg",
                web_subnet_ids=[self.vpc.web_subnet_1.subnet_id, self.vpc.web_subnet_2.subnet_id],
                asg_sg_id=self.sg.asg_sg.ref,
                target_group_arn=self.alb.target_group_arn,
                efs_id=efs_id,
                rds_host=rds_host,
                alb_dns=self.alb.alb_dns,
                site_fqdn=self.WEB_FQDN,
                name=rds_name)

        # 7. Route53 (primary uniquement, si l'ALB secondaire est connu)
        if is_primary and alb_dns_secondary:
            self.route53 = Route53Nested(self, "Route53",
                alb_dns_primary=self.alb.alb_dns,
                alb_dns_secondary=alb_dns_secondary,
                alb_zone_id_primary=self._ALB_HZ["us-east-1"],
                alb_zone_id_secondary=self._ALB_HZ["us-west-2"],
                name=rds_name)
            self.route53.add_dependency(self.alb)
