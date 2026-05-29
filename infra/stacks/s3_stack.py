import os
from aws_cdk import Stack, CfnOutput, aws_s3 as s3
from constructs import Construct


class S3PrimaryStack(Stack):
    """Bucket S3 principal en us-east-1 avec replication vers us-west-2"""

    def __init__(self, scope: Construct, construct_id: str, secondary_bucket_arn: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account_id = os.getenv("AWS_ACCOUNT_ID")
        lab_role_arn = f"arn:aws:iam::{account_id}:role/LabRole"

        # Bucket secondaire doit exister avant — on passe son ARN en paramètre
        self.bucket = s3.CfnBucket(self, "PrimaryBucket",
            bucket_name=f"ynov-wordpress-primary-{account_id}",
            versioning_configuration=s3.CfnBucket.VersioningConfigurationProperty(
                status="Enabled"
            ),
            replication_configuration=s3.CfnBucket.ReplicationConfigurationProperty(
                role=lab_role_arn,
                rules=[
                    s3.CfnBucket.ReplicationRuleProperty(
                        id="ReplicateToWest2",
                        status="Enabled",
                        destination=s3.CfnBucket.ReplicationDestinationProperty(
                            bucket=secondary_bucket_arn,
                        ),
                    )
                ],
            ),
        )

        CfnOutput(self, "PrimaryBucketName", value=self.bucket.ref)
        CfnOutput(self, "PrimaryBucketArn", value=self.bucket.attr_arn)


class S3SecondaryStack(Stack):
    """Bucket S3 backup en us-west-2"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account_id = os.getenv("AWS_ACCOUNT_ID")

        self.bucket = s3.CfnBucket(self, "SecondaryBucket",
            bucket_name=f"ynov-wordpress-secondary-{account_id}",
            versioning_configuration=s3.CfnBucket.VersioningConfigurationProperty(
                status="Enabled"
            ),
        )

        CfnOutput(self, "SecondaryBucketName", value=self.bucket.ref)
        CfnOutput(self, "SecondaryBucketArn", value=self.bucket.attr_arn)
