from aws_cdk import Stack
from constructs import Construct

from stacks.nested.vpc import VpcNested
from stacks.nested.sg import SgNested
from stacks.nested.rds import RdsNested
from stacks.nested.efs import EfsNested
from stacks.nested.alb import AlbNested
from stacks.nested.asg import AsgNested
from stacks.nested.s3 import S3PrimaryNested, S3SecondaryNested


class InfraStack(Stack):
    """
    Stack parent (un par region) contenant tous les nested stacks.
    CloudFormation ordonne automatiquement via les dependances.

    is_primary=True  -> us-east-1 : RDS Multi-AZ + S3 primary (CRR)
    is_primary=False -> us-west-2 : RDS standalone + S3 secondary (cible CRR)
    """

    def __init__(self, scope: Construct, construct_id: str, *,
                 region_kind: str, cidr_prefix: str, azs: list,
                 db_password: str, is_primary: bool, account_id: str, **kwargs) -> None:
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
            name=rds_name)

        # 7. S3 : primaire (CRR) ou secondaire (cible) selon la region
        if is_primary:
            self.s3 = S3PrimaryNested(self, "S3", account_id=account_id)
        else:
            self.s3 = S3SecondaryNested(self, "S3", account_id=account_id)
