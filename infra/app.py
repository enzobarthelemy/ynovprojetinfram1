#!/usr/bin/env python3
"""
Point d'entree CDK - architecture nested stacks.
Un stack parent par region (InfraPrimaryStack / InfraSecondaryStack),
chacun contenant les nested stacks (VPC, SG, RDS, EFS, ALB, ASG, S3, Backup).
CloudFormation gere l'ordre de deploiement automatiquement.
"""
import os
import aws_cdk as cdk

from stacks.nested.parent import InfraStack

app = cdk.App()

account_id = os.getenv("AWS_ACCOUNT_ID")
db_password = os.getenv("DB_PASSWORD", "ChangeMe1234")

# CliCredentialsStackSynthesizer : utilise les creds du CI (pas de bootstrap)
# + bucket d'assets pour les templates des nested stacks.
def make_synth(bucket: str):
    return cdk.CliCredentialsStackSynthesizer(file_assets_bucket_name=bucket)

InfraStack(app, "InfraPrimaryStack",
    region_kind="Prod",
    cidr_prefix="10.0",
    azs=["us-east-1a", "us-east-1b"],
    db_password=db_password,
    is_primary=True,
    account_id=account_id,
    env=cdk.Environment(account=account_id, region="us-east-1"),
    synthesizer=make_synth(f"ynov-cdk-assets-{account_id}-use1"),
)

InfraStack(app, "InfraSecondaryStack",
    region_kind="Backup",
    cidr_prefix="10.1",
    azs=["us-west-2a", "us-west-2b"],
    db_password=db_password,
    is_primary=False,
    account_id=account_id,
    env=cdk.Environment(account=account_id, region="us-west-2"),
    synthesizer=make_synth(f"ynov-cdk-assets-{account_id}-usw2"),
)

app.synth()
