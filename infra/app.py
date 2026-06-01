#!/usr/bin/env python3
import os
import aws_cdk as cdk

from stacks.vpc_stack import VpcStackPrimary, VpcStackSecondary
from stacks.sg_stack import SgStackPrimary, SgStackSecondary
from stacks.ec2_stack import Ec2StackPrimary, Ec2StackSecondary
from stacks.alb_stack import AlbStackPrimary, AlbStackSecondary
from stacks.efs_stack import EfsStackPrimary, EfsStackSecondary
from stacks.asg_stack import AsgStackPrimary, AsgStackSecondary
from stacks.s3_stack import S3StackPrimary, S3StackSecondary
from stacks.rds_stack import RdsStackPrimary, RdsStackSecondary

app = cdk.App()

account_id = os.getenv("AWS_ACCOUNT_ID")

env_east = cdk.Environment(account=account_id, region=os.getenv("AWS_PRIMARY_REGION", "us-east-1"))
env_west = cdk.Environment(account=account_id, region=os.getenv("AWS_SECONDARY_REGION", "us-west-2"))

synthesizer_east = cdk.BootstraplessSynthesizer(
    cloud_formation_execution_role_arn=f"arn:aws:iam::{account_id}:role/LabRole",
    deploy_role_arn=f"arn:aws:iam::{account_id}:role/LabRole",
)
synthesizer_west = cdk.BootstraplessSynthesizer(
    cloud_formation_execution_role_arn=f"arn:aws:iam::{account_id}:role/LabRole",
    deploy_role_arn=f"arn:aws:iam::{account_id}:role/LabRole",
)

# 1. VPC
vpc_primary = VpcStackPrimary(app, "VpcStackPrimary", env=env_east, synthesizer=synthesizer_east)
vpc_secondary = VpcStackSecondary(app, "VpcStackSecondary", env=env_west, synthesizer=synthesizer_west)

# 2. Security Groups
sg_primary = SgStackPrimary(app, "SgStackPrimary", env=env_east, synthesizer=synthesizer_east)
sg_primary.add_dependency(vpc_primary)
sg_secondary = SgStackSecondary(app, "SgStackSecondary", env=env_west, synthesizer=synthesizer_west)
sg_secondary.add_dependency(vpc_secondary)

# 3. EC2 — WordPress + WooCommerce (Docker)
ec2_primary = Ec2StackPrimary(app, "Ec2StackPrimary", vpc_stack=vpc_primary, sg_stack=sg_primary, env=env_east, synthesizer=synthesizer_east)
ec2_primary.add_dependency(sg_primary)
ec2_secondary = Ec2StackSecondary(app, "Ec2StackSecondary", vpc_stack=vpc_secondary, sg_stack=sg_secondary, env=env_west, synthesizer=synthesizer_west)
ec2_secondary.add_dependency(sg_secondary)

# 4. ALB
alb_primary = AlbStackPrimary(app, "AlbStackPrimary", vpc_stack=vpc_primary, sg_stack=sg_primary, env=env_east, synthesizer=synthesizer_east)
alb_primary.add_dependency(sg_primary)
alb_secondary = AlbStackSecondary(app, "AlbStackSecondary", vpc_stack=vpc_secondary, sg_stack=sg_secondary, env=env_west, synthesizer=synthesizer_west)
alb_secondary.add_dependency(sg_secondary)

# 5. EFS — stockage partagé WordPress avec réplication cross-region
efs_primary = EfsStackPrimary(app, "EfsStackPrimary", env=env_east, synthesizer=synthesizer_east)
efs_primary.add_dependency(sg_primary)
efs_secondary = EfsStackSecondary(app, "EfsStackSecondary", env=env_west, synthesizer=synthesizer_west)
efs_secondary.add_dependency(sg_secondary)

# 6. ASG — Auto Scaling Group avec EFS + Secrets Manager
asg_primary = AsgStackPrimary(app, "AsgStackPrimary", vpc_stack=vpc_primary, sg_stack=sg_primary, alb_stack=alb_primary, env=env_east, synthesizer=synthesizer_east)
asg_primary.add_dependency(efs_primary)
asg_primary.add_dependency(alb_primary)
asg_secondary = AsgStackSecondary(app, "AsgStackSecondary", vpc_stack=vpc_secondary, sg_stack=sg_secondary, alb_stack=alb_secondary, env=env_west, synthesizer=synthesizer_west)
asg_secondary.add_dependency(efs_secondary)
asg_secondary.add_dependency(alb_secondary)

# 7. S3 — Secondary d'abord (Cross-Region Replication)
s3_secondary = S3StackSecondary(app, "S3StackSecondary", env=env_west, synthesizer=synthesizer_west)
s3_primary = S3StackPrimary(app, "S3StackPrimary",
    secondary_bucket_arn=f"arn:aws:s3:::ynov-wordpress-secondary-{account_id}",
    env=env_east,
    synthesizer=synthesizer_east,
)
s3_primary.add_dependency(s3_secondary)

# 8. RDS — MySQL Multi-AZ Primary + Read Replica cross-region
rds_primary = RdsStackPrimary(app, "RdsStackPrimary", env=env_east, synthesizer=synthesizer_east)
rds_primary.add_dependency(sg_primary)
rds_secondary = RdsStackSecondary(app, "RdsStackSecondary", env=env_west, synthesizer=synthesizer_west)
rds_secondary.add_dependency(sg_secondary)

app.synth()
