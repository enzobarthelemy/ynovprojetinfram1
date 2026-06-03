from aws_cdk import NestedStack, aws_efs as efs
from constructs import Construct


class EfsNested(NestedStack):
    """
    EFS par region (CfnFileSystem L1). Deux modes :

    - CREATION (primary) : cree le filesystem. Si replicate_to_region est fourni,
      AWS cree automatiquement un FS REPLIQUE read-only dans la region cible.

    - MONTAGE D'UN REPLICA (secondary) : si replica_fs_id est fourni, ne cree PAS
      de filesystem. Cree uniquement les mount targets sur le replica existant
      pour que les EC2 du secondary puissent le monter (read-only tant que la
      replication est active ; writable apres promotion au failover).

    Expose file_system_id.
    """

    def __init__(self, scope: Construct, construct_id: str, *,
                 web_subnet_ids: list, efs_sg_id: str, name: str,
                 replicate_to_region: str | None = None,
                 replica_fs_id: str | None = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if replica_fs_id:
            # --- Mode MONTAGE du replica existant ---
            fs_id = replica_fs_id
            # Pas d'access point (le replica est read-only ; le user_data monte la racine)
        else:
            # --- Mode CREATION d'un nouveau filesystem ---
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
            if replicate_to_region:
                fs.replication_configuration = efs.CfnFileSystem.ReplicationConfigurationProperty(
                    destinations=[efs.CfnFileSystem.ReplicationDestinationProperty(
                        region=replicate_to_region)]
                )
            fs_id = fs.ref

            efs.CfnAccessPoint(self, "WordpressAccessPoint",
                file_system_id=fs_id,
                root_directory=efs.CfnAccessPoint.RootDirectoryProperty(
                    path="/wordpress",
                    creation_info=efs.CfnAccessPoint.CreationInfoProperty(
                        owner_uid="33", owner_gid="33", permissions="755"),
                ),
                posix_user=efs.CfnAccessPoint.PosixUserProperty(uid="33", gid="33"),
            )

        # Mount targets : un par subnet web (= un par AZ)
        for i, subnet_id in enumerate(web_subnet_ids, start=1):
            efs.CfnMountTarget(self, f"MountTarget{i}",
                file_system_id=fs_id,
                subnet_id=subnet_id,
                security_groups=[efs_sg_id],
            )

        self.file_system_id = fs_id
