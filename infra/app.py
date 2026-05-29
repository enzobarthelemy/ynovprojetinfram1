#!/usr/bin/env python3
import os
import aws_cdk as cdk

from stacks.vpc_stack import VpcStack
from stacks.sg_stack import SgStack
from stacks.ec2_stack import Ec2Stack
from stacks.alb_stack import AlbStack
from stacks.asg_stack import AsgStack
from stacks.s3_stack import S3Stack
from stacks.rds_stack import RdsStack

app = cdk.App()

env = cdk.Environment(
    account=os.getenv("AWS_ACCOUNT_ID"),
    region="us-east-1",
)

synthesizer = cdk.BootstraplessSynthesizer(
    cloud_formation_execution_role_arn=f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/LabRole",
    deploy_role_arn=f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/LabRole",
)

# 1. VPC — base de toute l'infra
vpc_stack = VpcStack(app, "VpcStack", env=env, synthesizer=synthesizer)

# 2. Security Groups — dépend du VPC
sg_stack = SgStack(app, "SgStack", vpc_stack=vpc_stack, env=env, synthesizer=synthesizer)
sg_stack.add_dependency(vpc_stack)

# 3. EC2 — instances WordPress + WooCommerce (Docker)
ec2_stack = Ec2Stack(app, "Ec2Stack", vpc_stack=vpc_stack, sg_stack=sg_stack, env=env, synthesizer=synthesizer)
ec2_stack.add_dependency(sg_stack)

# 4. ALB — Load Balancer public
alb_stack = AlbStack(app, "AlbStack", vpc_stack=vpc_stack, sg_stack=sg_stack, env=env, synthesizer=synthesizer)
alb_stack.add_dependency(sg_stack)

# 5. ASG — Auto Scaling Group (stress test)
asg_stack = AsgStack(app, "AsgStack", vpc_stack=vpc_stack, sg_stack=sg_stack, alb_stack=alb_stack, env=env, synthesizer=synthesizer)
asg_stack.add_dependency(alb_stack)

# 6. S3 — fichiers statiques WordPress
s3_stack = S3Stack(app, "S3Stack", env=env, synthesizer=synthesizer)

# 7. RDS — base de données MySQL WordPress (Multi-AZ)
rds_stack = RdsStack(app, "RdsStack", vpc_stack=vpc_stack, sg_stack=sg_stack, env=env, synthesizer=synthesizer)
rds_stack.add_dependency(sg_stack)

app.synth()
