#!/usr/bin/env python3
"""
Point d'entree NESTED (prototype). Ne remplace pas app.py tant que valide.
Synth : cdk synth --app "python nested_app.py"
"""
import os
import aws_cdk as cdk

from stacks.nested.parent import InfraStack

app = cdk.App()

account_id = os.getenv("AWS_ACCOUNT_ID")

# Synthesizer avec bucket d'assets (requis pour les templates des nested stacks).
# CliCredentialsStackSynthesizer : utilise les creds du CI directement (pas de bootstrap)
# et permet de specifier le bucket d'assets.
def make_synth(bucket: str):
    return cdk.CliCredentialsStackSynthesizer(
        file_asset_bucket_name=bucket,
    )

InfraStack(app, "InfraPrimaryStack",
    region_kind="Prod",
    cidr_prefix="10.0",
    azs=["us-east-1a", "us-east-1b"],
    env=cdk.Environment(account=account_id, region="us-east-1"),
    synthesizer=make_synth("ynov-cdk-assets-882885448709-use1"),
)

InfraStack(app, "InfraSecondaryStack",
    region_kind="Backup",
    cidr_prefix="10.1",
    azs=["us-west-2a", "us-west-2b"],
    env=cdk.Environment(account=account_id, region="us-west-2"),
    synthesizer=make_synth("ynov-cdk-assets-882885448709-usw2"),
)

app.synth()
