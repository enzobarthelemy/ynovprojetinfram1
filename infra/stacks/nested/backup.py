from aws_cdk import (
    NestedStack,
    Duration,
    aws_backup as backup,
    aws_events as events,
    aws_iam as iam,
)
from constructs import Construct


class BackupVaultNested(NestedStack):
    """
    Vault de destination (us-west-2) pour la copie cross-region.
    Cree cote secondary - doit exister avant que le plan primary copie dedans.
    """
    def __init__(self, scope: Construct, construct_id: str, *, vault_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.vault = backup.BackupVault(self, "Vault", backup_vault_name=vault_name)


class BackupPlanNested(NestedStack):
    """
    AWS Backup Plan natif (cote primary us-east-1) :
    - vault local
    - regle planifiee (quotidienne) qui sauvegarde l'EFS
    - copie cross-region automatique vers le vault us-west-2 (DR)
    Tout est gere par le service AWS Backup - aucun job pipeline.
    """
    def __init__(self, scope: Construct, construct_id: str, *,
                 efs_id: str, account_id: str, vault_name: str,
                 secondary_region: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Vault local (us-east-1)
        local_vault = backup.BackupVault(self, "LocalVault", backup_vault_name=vault_name)

        # ARN du vault destination en us-west-2 (cree par BackupVaultNested cote secondary)
        dest_vault_arn = f"arn:aws:backup:{secondary_region}:{account_id}:backup-vault:{vault_name}"
        dest_vault = backup.BackupVault.from_backup_vault_arn(self, "DestVault", dest_vault_arn)

        # Plan : sauvegarde quotidienne + copie cross-region vers us-west-2
        plan = backup.BackupPlan(self, "EfsBackupPlan",
            backup_plan_name="efs-wordpress-dr",
            backup_vault=local_vault,
        )
        plan.add_rule(backup.BackupPlanRule(
            rule_name="DailyWithCrossRegionCopy",
            schedule_expression=events.Schedule.cron(hour="3", minute="0"),  # 03:00 UTC chaque jour
            delete_after=Duration.days(14),
            copy_actions=[backup.BackupPlanCopyActionProps(
                destination_backup_vault=dest_vault,
                delete_after=Duration.days(14),
            )],
        ))

        # Selection : l'EFS a sauvegarder (role LabRole pour AWS Student)
        lab_role = iam.Role.from_role_arn(self, "LabRole",
            f"arn:aws:iam::{account_id}:role/LabRole", mutable=False)
        efs_arn = f"arn:aws:elasticfilesystem:{self.region}:{account_id}:file-system/{efs_id}"

        plan.add_selection("EfsSelection",
            resources=[backup.BackupResource.from_arn(efs_arn)],
            role=lab_role,
        )
