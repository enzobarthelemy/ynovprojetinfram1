from aws_cdk import NestedStack, aws_s3 as s3
from constructs import Construct


class S3SecondaryNested(NestedStack):
    """Bucket S3 secondaire (us-west-2) - cible de la CRR. Versioning active."""

    def __init__(self, scope: Construct, construct_id: str, *,
                 account_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.bucket = s3.CfnBucket(self, "SecondaryBucket",
            bucket_name=f"ynov-wordpress-secondary-{account_id}",
            versioning_configuration=s3.CfnBucket.VersioningConfigurationProperty(status="Enabled"),
        )


class S3PrimaryNested(NestedStack):
    """Bucket S3 primaire (us-east-1) + Cross-Region Replication vers le secondaire."""

    def __init__(self, scope: Construct, construct_id: str, *,
                 account_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        lab_role_arn = f"arn:aws:iam::{account_id}:role/LabRole"
        secondary_bucket_arn = f"arn:aws:s3:::ynov-wordpress-secondary-{account_id}"

        self.bucket = s3.CfnBucket(self, "PrimaryBucket",
            bucket_name=f"ynov-wordpress-primary-{account_id}",
            versioning_configuration=s3.CfnBucket.VersioningConfigurationProperty(status="Enabled"),
            replication_configuration=s3.CfnBucket.ReplicationConfigurationProperty(
                role=lab_role_arn,
                rules=[s3.CfnBucket.ReplicationRuleProperty(
                    id="ReplicateToWest2",
                    status="Enabled",
                    destination=s3.CfnBucket.ReplicationDestinationProperty(
                        bucket=secondary_bucket_arn),
                )],
            ),
        )
