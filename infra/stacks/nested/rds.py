from aws_cdk import NestedStack, aws_rds as rds
from constructs import Construct


class RdsNested(NestedStack):
    """
    RDS MySQL en NestedStack. Recoit les subnets DB + le SG + le password directement.
    name      : "primary" ou "secondary"
    multi_az  : True (primary) ou False (secondary)
    """

    def __init__(self, scope: Construct, construct_id: str, *,
                 db_subnet_ids: list, db_sg_id: str, db_password: str,
                 name: str, multi_az: bool, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        subnet_group = rds.CfnDBSubnetGroup(self, "RdsSubnetGroup",
            db_subnet_group_description=f"Subnet group RDS WordPress {name}",
            subnet_ids=db_subnet_ids,
            tags=[{"key": "Name", "value": f"rds-subnet-group-{name}"}],
        )

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
