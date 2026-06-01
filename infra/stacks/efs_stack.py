import os
from aws_cdk import Stack, CfnOutput, CfnParameter, aws_efs as efs
from constructs import Construct


class EfsStackPrimary(Stack):
    """
    EFS Primary en us-east-1 avec réplication vers us-west-2.
    Utilise L1 pour éviter les problèmes de subnet type avec notre VPC.
    """
    def __init__(self, scope, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        web_subnet_1 = CfnParameter(self, "WebSubnet1Id", type="String").value_as_string
        web_subnet_2 = CfnParameter(self, "WebSubnet2Id", type="String").value_as_string
        efs_sg_id    = CfnParameter(self, "EfsSgId", type="String").value_as_string

        # FileSystem EFS chiffré
        fs = efs.CfnFileSystem(self, "PrimaryEFS",
            encrypted=True,
            performance_mode="generalPurpose",
            throughput_mode="bursting",
            lifecycle_policies=[
                efs.CfnFileSystem.LifecyclePolicyProperty(
                    transition_to_ia="AFTER_30_DAYS",
                ),
                efs.CfnFileSystem.LifecyclePolicyProperty(
                    transition_to_primary_storage_class="AFTER_1_ACCESS",
                ),
            ],
            replication_configuration=efs.CfnFileSystem.ReplicationConfigurationProperty(
                destinations=[
                    efs.CfnFileSystem.ReplicationDestinationProperty(
                        region="us-west-2",
                    )
                ]
            ),
        )

        # Mount targets dans chaque subnet privé web
        efs.CfnMountTarget(self, "MountTarget1",
            file_system_id=fs.ref,
            subnet_id=web_subnet_1,
            security_groups=[efs_sg_id],
        )
        efs.CfnMountTarget(self, "MountTarget2",
            file_system_id=fs.ref,
            subnet_id=web_subnet_2,
            security_groups=[efs_sg_id],
        )

        # Access Point WordPress (UID/GID 33 = www-data)
        efs.CfnAccessPoint(self, "WordpressAccessPoint",
            file_system_id=fs.ref,
            root_directory=efs.CfnAccessPoint.RootDirectoryProperty(
                path="/wordpress",
                creation_info=efs.CfnAccessPoint.CreationInfoProperty(
                    owner_uid="33",
                    owner_gid="33",
                    permissions="755",
                ),
            ),
            posix_user=efs.CfnAccessPoint.PosixUserProperty(uid="33", gid="33"),
        )

        self.file_system_id = fs.ref

        CfnOutput(self, "EfsId", value=fs.ref)


class EfsStackSecondary(Stack):
    """
    EFS Secondary en us-west-2.
    Le FileSystem est créé automatiquement par la réplication depuis Primary.
    Ce stack crée uniquement les mount targets et l'access point.
    Nécessite EFS_SECONDARY_ID dans les variables GitLab CI après le premier déploiement Primary.
    """
    def __init__(self, scope, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        web_subnet_1      = CfnParameter(self, "WebSubnet1Id", type="String").value_as_string
        web_subnet_2      = CfnParameter(self, "WebSubnet2Id", type="String").value_as_string
        efs_sg_id         = CfnParameter(self, "EfsSgId", type="String").value_as_string
        secondary_fs_id   = CfnParameter(self, "EfsSecondaryFsId", type="String").value_as_string
        self.file_system_id = secondary_fs_id

        efs.CfnMountTarget(self, "MountTarget1",
            file_system_id=secondary_fs_id,
            subnet_id=web_subnet_1,
            security_groups=[efs_sg_id],
        )
        efs.CfnMountTarget(self, "MountTarget2",
            file_system_id=secondary_fs_id,
            subnet_id=web_subnet_2,
            security_groups=[efs_sg_id],
        )

        efs.CfnAccessPoint(self, "WordpressAccessPoint",
            file_system_id=secondary_fs_id,
            root_directory=efs.CfnAccessPoint.RootDirectoryProperty(
                path="/wordpress",
                creation_info=efs.CfnAccessPoint.CreationInfoProperty(
                    owner_uid="33",
                    owner_gid="33",
                    permissions="755",
                ),
            ),
            posix_user=efs.CfnAccessPoint.PosixUserProperty(uid="33", gid="33"),
        )

        CfnOutput(self, "EfsSecondaryId", value=secondary_fs_id)
