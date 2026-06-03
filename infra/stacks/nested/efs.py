from aws_cdk import NestedStack, aws_efs as efs
from constructs import Construct


class EfsNested(NestedStack):
    """
    EFS par region (CfnFileSystem L1).
    - Resilience intra-region 1a/1b : native (mount targets dans les 2 AZ, meme filesystem).
    - DR cross-region : si replicate_to_region est fourni (region primaire), AWS cree
      automatiquement un filesystem REPLIQUE (read-only) dans la region de destination.
    Expose file_system_id.
    """

    def __init__(self, scope: Construct, construct_id: str, *,
                 web_subnet_ids: list, efs_sg_id: str, name: str,
                 replicate_to_region: str | None = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        fs = efs.CfnFileSystem(self, "Efs",
            encrypted=True,
            performance_mode="generalPurpose",
            throughput_mode="bursting",
            lifecycle_policies=[
                efs.CfnFileSystem.LifecyclePolicyProperty(transition_to_ia="AFTER_30_DAYS"),
                efs.CfnFileSystem.LifecyclePolicyProperty(transition_to_primary_storage_class="AFTER_1_ACCESS"),
            ],
            file_system_tags=[efs.CfnFileSystem.ElasticFileSystemTagProperty(
                key="Name", value=f"efs-wordpress-{name}")],
        )

        # Replication cross-region : AWS cree un FS read-only dans la region cible
        if replicate_to_region:
            fs.replication_configuration = efs.CfnFileSystem.ReplicationConfigurationProperty(
                destinations=[efs.CfnFileSystem.ReplicationDestinationProperty(
                    region=replicate_to_region)]
            )

        # Mount targets : un par subnet web (= un par AZ) => resilience 1a/1b
        for i, subnet_id in enumerate(web_subnet_ids, start=1):
            efs.CfnMountTarget(self, f"MountTarget{i}",
                file_system_id=fs.ref,
                subnet_id=subnet_id,
                security_groups=[efs_sg_id],
            )

        # Access point WordPress (UID/GID 33 = www-data)
        efs.CfnAccessPoint(self, "WordpressAccessPoint",
            file_system_id=fs.ref,
            root_directory=efs.CfnAccessPoint.RootDirectoryProperty(
                path="/wordpress",
                creation_info=efs.CfnAccessPoint.CreationInfoProperty(
                    owner_uid="33", owner_gid="33", permissions="755"),
            ),
            posix_user=efs.CfnAccessPoint.PosixUserProperty(uid="33", gid="33"),
        )

        self.file_system_id = fs.ref
