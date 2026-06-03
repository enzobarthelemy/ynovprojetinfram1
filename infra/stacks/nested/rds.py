from aws_cdk import NestedStack, CfnOutput, aws_rds as rds
from constructs import Construct


class RdsNested(NestedStack):
    """
    RDS MySQL en NestedStack.
    name      : "primary" ou "secondary"
    multi_az  : True (primary) ou False
    create_instance :
        True  (primary)   -> cree le subnet group + l'instance RDS.
        False (secondary) -> cree UNIQUEMENT le subnet group (cold standby).
                             L'instance arrive au failover (restore du snapshot).

    Nom du subnet group :
        secondary -> nom FIXE (wordpress-rds-subnet-secondary) pour que le job
                     failover puisse le referencer lors de la restauration.
        primary   -> nom AUTO-genere. Lui imposer un nom forcerait le remplacement
                     du subnet group, donc de l'instance RDS (DBSubnetGroupName =
                     update requires replacement) -> bloque par le nom custom de
                     l'instance + perte de donnees. On laisse donc CloudFormation
                     gerer le nom.
    """

    def __init__(self, scope: Construct, construct_id: str, *,
                 db_subnet_ids: list, db_sg_id: str, name: str,
                 db_password: str | None = None, multi_az: bool = False,
                 create_instance: bool = True, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Nom fixe uniquement pour le SECONDARY (cold standby, retrouve au failover).
        # Le primary garde TOUJOURS un nom auto-genere (normal ET failback) : sinon
        # CloudFormation renommerait le subnet group alors que la DB de failback l'utilise
        # -> DELETE_FAILED. Le job failback-rds retrouve ce subnet group via l'instance.
        fixed_name = f"wordpress-rds-subnet-{name}" if name == "secondary" else None
        subnet_group = rds.CfnDBSubnetGroup(self, "RdsSubnetGroup",
            db_subnet_group_name=fixed_name,
            db_subnet_group_description=f"Subnet group RDS WordPress {name}",
            subnet_ids=db_subnet_ids,
            tags=[{"key": "Name", "value": f"wordpress-rds-subnet-{name}"}],
        )
        self.subnet_group_name = fixed_name or subnet_group.ref
        self.endpoint = None

        # Instance creee uniquement en primary (le secondary est cold standby)
        if create_instance:
            self.db = rds.CfnDBInstance(self, "Rds",
                db_instance_identifier=f"wordpress-rds-{name}",
                db_name="wordpress",
                db_instance_class="db.t3.micro",
                engine="mysql",
                engine_version="8.0",
                allocated_storage="20",
                storage_type="gp2",
                master_username="admin",
                master_user_password=db_password,
                db_subnet_group_name=subnet_group.ref,
                vpc_security_groups=[db_sg_id],
                multi_az=multi_az,
                publicly_accessible=False,
                monitoring_interval=0,
                deletion_protection=False,
                backup_retention_period=7,
                tags=[{"key": "Name", "value": f"wordpress-rds-{name}"}],
            )
            self.endpoint = self.db.attr_endpoint_address

        CfnOutput(self, "DbSubnetGroupName", value=self.subnet_group_name)
