from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_efs as efs,
    aws_ec2 as ec2,
)
from constructs import Construct


class EfsStackPrimary(Stack):
    def __init__(self, scope, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # vpc_stack.vpc = alias vers vpc_stack.vpc_prod (us-east-1)
        self.fs = efs.FileSystem(
            self, "PrimaryEFS",
            vpc=vpc_stack.vpc,
            security_group=sg_stack.efs_sg,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
            lifecycle_policy=efs.LifecyclePolicy.AFTER_30_DAYS,
            out_of_infrequent_access_policy=efs.OutOfInfrequentAccessPolicy.AFTER_1_ACCESS,
            encrypted=True,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Access point WordPress (UID/GID 33 = www-data)
        self.access_point = self.fs.add_access_point(
            "WordpressAccessPoint",
            path="/wordpress",
            create_acl=efs.Acl(owner_uid="33", owner_gid="33", permissions="755"),
            posix_user=efs.PosixUser(uid="33", gid="33"),
        )

        # Réplication vers us-west-2
        cfn_fs = self.fs.node.default_child
        cfn_fs.replication_configuration = {
            "destinations": [{"region": "us-west-2"}]
        }


class EfsStackSecondary(Stack):
    def __init__(self, scope, construct_id: str, vpc_stack, sg_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        import os
        secondary_fs_id = os.environ.get("EFS_SECONDARY_ID", "fs-PLACEHOLDER")

        # Le FS secondaire est créé automatiquement par la réplication EFS Primary
        # EFS_SECONDARY_ID doit être renseigné dans les variables GitLab CI
        # après le premier déploiement du Primary
        self.fs = efs.FileSystem.from_file_system_attributes(
            self, "SecondaryEFS",
            file_system_id=secondary_fs_id,
            security_group=sg_stack.efs_sg,
        )

        self.access_point = self.fs.add_access_point(
            "WordpressAccessPoint",
            path="/wordpress",
            create_acl=efs.Acl(owner_uid="33", owner_gid="33", permissions="755"),
            posix_user=efs.PosixUser(uid="33", gid="33"),
        )
