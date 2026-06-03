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

    FAILBACK (primary_replica_fs_id fourni au primary) :
        Le primary monte le FS replique en sens INVERSE (us-west-2 -> us-east-1)
        au lieu de creer son propre EFS. Permet de rapatrier les donnees ecrites
        pendant le failover, sans SSM (que des API AWS + CDK).

    Contexte fourni au deploy (pas de ref cross-region CDK) :
        alb_dns_secondary     : DNS ALB secondaire (pour Route53 failover sur le primary)
        replica_fs_id         : ID du FS EFS replique (pour l'EFS du secondary, pass 2)
        primary_replica_fs_id : ID du FS EFS replique INVERSE (pour le primary au failback)
    """

    WEB_FQDN = "sub.ynov-infram1-grp1.com"
    _ALB_HZ = {"us-east-1": "Z35SXDOTRQ7X7K", "us-west-2": "Z1H1FL5HABSF5"}

    def __init__(self, scope: Construct, construct_id: str, *,
                 region_kind: str, cidr_prefix: str, azs: list,
                 db_password: str, is_primary: bool, account_id: str,
                 alb_dns_secondary: str | None = None,
                 replica_fs_id: str | None = None,
                 primary_replica_fs_id: str | None = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        rds_name = "primary" if is_primary else "secondary"

        # 1. VPC
        self.vpc = VpcNested(self, "Vpc",
            cidr_prefix=cidr_prefix, azs=azs, name=region_kind)

        # 2. Security Groups
        self.sg = SgNested(self, "Sg",
            vpc_id=self.vpc.vpc.vpc_id, name=region_kind)

        # 3. RDS :
        #    primary normal   = instance Multi-AZ (wordpress-rds-primary)
        #    primary failback = PAS d'instance : la DB active est wordpress-rds-failback
        #                       (restauree par le job failback-rds, pointee par le secret).
        #                       CDK supprime alors wordpress-rds-primary -> 1 seule DB en east.
        #    secondary        = subnet group seul (cold standby)
        create_db_instance = is_primary and not primary_replica_fs_id
        self.rds = RdsNested(self, "Rds",
            db_subnet_ids=[self.vpc.db_subnet_1.subnet_id, self.vpc.db_subnet_2.subnet_id],
            db_sg_id=self.sg.rds_sg.ref,
            db_password=db_password,
            name=rds_name, multi_az=is_primary,
            create_instance=create_db_instance)

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
        #    primary normal   : cree l'EFS (replication read-only vers us-west-2) + ASG
        #    primary failback : monte le replica INVERSE (primary_replica_fs_id) + ASG
        #    secondary pass 1 : pas de compute (cold standby)
        #    secondary pass 2 : monte le replica (replica_fs_id) + ASG
        web_subnet_ids = [self.vpc.web_subnet_1.subnet_id, self.vpc.web_subnet_2.subnet_id]
        if is_primary:
            create_compute = True
            if primary_replica_fs_id:
                # FAILBACK : monte le FS replique en sens inverse (us-west-2 -> us-east-1).
                # Read-only jusqu'a la promotion, puis writable (comme le secondary au failover).
                self.efs = EfsNested(self, "Efs",
                    web_subnet_ids=web_subnet_ids,
                    efs_sg_id=self.sg.efs_sg.ref, name=rds_name,
                    replica_fs_id=primary_replica_fs_id)
                efs_id = primary_replica_fs_id
            else:
                # Normal : cree l'EFS avec replication read-only vers us-west-2
                self.efs = EfsNested(self, "Efs",
                    web_subnet_ids=web_subnet_ids,
                    efs_sg_id=self.sg.efs_sg.ref, name=rds_name,
                    replicate_to_region="us-west-2")
                efs_id = self.efs.file_system_id
            # Normal : token RDS de wordpress-rds-primary. Failback : pas d'instance CDK,
            # la DB (wordpress-rds-failback) est resolue via le secret .host de la region.
            rds_host = self.rds.endpoint or ""
        else:
            create_compute = bool(replica_fs_id)
            if create_compute:
                # Secondary : monte le FS replique (read-only ; promu au failover)
                self.efs = EfsNested(self, "Efs",
                    web_subnet_ids=web_subnet_ids,
                    efs_sg_id=self.sg.efs_sg.ref, name=rds_name,
                    replica_fs_id=replica_fs_id)
                efs_id = replica_fs_id
                rds_host = ""   # DB via secret au failover

        if create_compute:
            self.asg = AsgNested(self, "Asg",
                web_subnet_ids=web_subnet_ids,
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
