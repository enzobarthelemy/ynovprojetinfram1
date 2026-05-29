#!/usr/bin/env python3
import os
import aws_cdk as cdk

from stacks.vpc_stack import VpcStack
from stacks.sg_stack import SgStack
from stacks.ec2_stack import Ec2Stack
from stacks.alb_stack import AlbStack
from stacks.asg_stack import AsgStack
from stacks.s3_stack import S3PrimaryStack, S3SecondaryStack
from stacks.rds_stack import RdsStack

app = cdk.App()

account_id = os.getenv("AWS_ACCOUNT_ID")

env_east = cdk.Environment(account=account_id, region="us-east-1")
env_west = cdk.Environment(account=account_id, region="us-west-2")

synthesizer_east = cdk.BootstraplessSynthesizer(
    cloud_formation_execution_role_arn=f"arn:aws:iam::{account_id}:role/LabRole",
    deploy_role_arn=f"arn:aws:iam::{account_id}:role/LabRole",
)

synthesizer_west = cdk.BootstraplessSynthesizer(
    cloud_formation_execution_role_arn=f"arn:aws:iam::{account_id}:role/LabRole",
    deploy_role_arn=f"arn:aws:iam::{account_id}:role/LabRole",
)

# 1. VPC — base de toute l'infra
vpc_stack = VpcStack(app, "VpcStack", env=env_east, synthesizer=synthesizer_east)

# 2. Security Groups — dépend du VPC
sg_stack = SgStack(app, "SgStack", vpc_stack=vpc_stack, env=env_east, synthesizer=synthesizer_east)
sg_stack.add_dependency(vpc_stack)

# 3. EC2 — instances WordPress + WooCommerce (Docker)
ec2_stack = Ec2Stack(app, "Ec2Stack", vpc_stack=vpc_stack, sg_stack=sg_stack, env=env_east, synthesizer=synthesizer_east)
ec2_stack.add_dependency(sg_stack)

# 4. ALB — Load Balancer public
alb_stack = AlbStack(app, "AlbStack", vpc_stack=vpc_stack, sg_stack=sg_stack, env=env_east, synthesizer=synthesizer_east)
alb_stack.add_dependency(sg_stack)

# 5. ASG — Auto Scaling Group (stress test)
asg_stack = AsgStack(app, "AsgStack", vpc_stack=vpc_stack, sg_stack=sg_stack, alb_stack=alb_stack, env=env_east, synthesizer=synthesizer_east)
asg_stack.add_dependency(alb_stack)

# 6. S3 secondaire en us-west-2 (backup) — doit être créé AVANT le primaire
s3_secondary = S3SecondaryStack(app, "S3SecondaryStack", env=env_west, synthesizer=synthesizer_west)

# 7. S3 primaire en us-east-1 avec replication vers us-west-2
s3_primary = S3PrimaryStack(app, "S3PrimaryStack",
    secondary_bucket_arn=f"arn:aws:s3:::ynov-wordpress-secondary-{account_id}",
    env=env_east,
    synthesizer=synthesizer_east,
)
s3_primary.add_dependency(s3_secondary)

# 8. RDS — base de données MySQL WordPress (Multi-AZ)
rds_stack = RdsStack(app, "RdsStack", vpc_stack=vpc_stack, sg_stack=sg_stack, env=env_east, synthesizer=synthesizer_east)
rds_stack.add_dependency(sg_stack)

app.synth()
