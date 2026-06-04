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
        primary_bucket_name = f"ynov-wordpress-primary-{account_id}"

        self.bucket = s3.CfnBucket(self, "PrimaryBucket",
            bucket_name=primary_bucket_name,
            versioning_configuration=s3.CfnBucket.VersioningConfigurationProperty(status="Enabled"),
            # Desactive le "Bloquer tous les acces publics" pour autoriser la bucket policy publique
            public_access_block_configuration=s3.CfnBucket.PublicAccessBlockConfigurationProperty(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
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

        # Bucket policy : lecture publique des objets (medias WordPress servis sur le web)
        s3.CfnBucketPolicy(self, "PrimaryBucketPolicy",
            bucket=self.bucket.ref,
            policy_document={
                "Version": "2012-10-17",
                "Statement": [{
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{primary_bucket_name}/*",
                }],
            },
        )
