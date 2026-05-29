#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_ec2.cdk_ec2_stack import CdkEc2Stack


app = cdk.App()
CdkEc2Stack(app, "CdkEc2Stack",
    env=cdk.Environment(
        account=os.getenv('AWS_ACCOUNT_ID'),
        region='us-east-1'
    ),
    synthesizer=cdk.BootstraplessSynthesizer(
        cloudformation_execution_role_arn=f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/LabRole",
        deploy_role_arn=f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/LabRole",
    ),
    )

app.synth()
