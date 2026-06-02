from aws_cdk import Stack
from constructs import Construct

from stacks.nested.vpc import VpcNested


class InfraStack(Stack):
    """
    Stack parent (un par region) contenant les nested stacks.
    Pour l'instant : VPC seulement (preuve de concept nested + no-bootstrap).
    On ajoutera SG, RDS, EFS, ALB, ASG, S3 ensuite.

    region_kind : "Prod" (us-east-1) ou "Backup" (us-west-2)
    """

    def __init__(self, scope: Construct, construct_id: str, *,
                 region_kind: str, cidr_prefix: str, azs: list, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. VPC (nested) — expose vpc, web_subnet_*, db_subnet_*, public_subnet_*
        self.vpc = VpcNested(self, "Vpc",
            cidr_prefix=cidr_prefix,
            azs=azs,
            name=region_kind,
        )

        # TODO etapes suivantes (une fois le VPC valide) :
        # self.sg  = SgNested(self, "Sg", vpc=self.vpc.vpc)
        # self.rds = RdsNested(self, "Rds", db_subnets=[self.vpc.db_subnet_1, self.vpc.db_subnet_2], sg=self.sg.rds_sg, ...)
        # self.efs = EfsNested(self, "Efs", web_subnets=[...], sg=self.sg.efs_sg)
        # self.alb = AlbNested(self, "Alb", vpc=self.vpc.vpc, public_subnets=[...], sg=self.sg.alb_sg)
        # self.asg = AsgNested(self, "Asg", web_subnets=[...], sg=self.sg.web_sg, target_group_arn=self.alb.target_group_arn, efs_id=self.efs.file_system_id)
