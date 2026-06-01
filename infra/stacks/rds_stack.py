import os
from aws_cdk import Stack, CfnOutput, CfnParameter, aws_rds as rds
from constructs import Construct


class RdsStackPrimary(Stack):
    """
    RDS MySQL Primary avec Multi-AZ :
    - Primary en us-east-1a (écriture)
    - Standby en us-east-1b (failover automatique synchrone)
    """
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        db_subnet_1 = CfnParameter(self, "DbSubnet1Id", type="String").value_as_string
        db_subnet_2 = CfnParameter(self, "DbSubnet2Id", type="String").value_as_string
        db_sg_id    = CfnParameter(self, "DbSgId", type="String").value_as_string
        db_password = CfnParameter(self, "DbPassword", type="String", no_echo=True).value_as_string

        # Subnet group couvrant us-east-1a + us-east-1b (requis pour Multi-AZ)
        subnet_group = rds.CfnDBSubnetGroup(self, "RdsSubnetGroupPrimary",
            db_subnet_group_description="Subnet group RDS WordPress Primary Multi-AZ",
            subnet_ids=[db_subnet_1, db_subnet_2],
            tags=[{"key": "Name", "value": "rds-subnet-group-primary"}],
        )

        # Instance Primary + Standby automatique (Multi-AZ)
        # AWS gère le Standby en us-east-1b de manière transparente
        db = rds.CfnDBInstance(self, "RdsPrimary",
            db_instance_identifier="wordpress-rds-primary",
            db_instance_class="db.t3.micro",
            engine="mysql",
            engine_version="8.0",
            allocated_storage="20",
            storage_type="gp2",
            master_username="admin",
            master_user_password=db_password,
            db_subnet_group_name=subnet_group.ref,
            vpc_security_groups=[db_sg_id],
            multi_az=True,
            publicly_accessible=False,
            monitoring_interval=0,
            deletion_protection=False,
            backup_retention_period=7,
            tags=[{"key": "Name", "value": "wordpress-rds-primary"}],
        )

        CfnOutput(self, "RdsEndpoint", value=db.attr_endpoint_address)
        CfnOutput(self, "RdsPort", value=db.attr_endpoint_port)
        CfnOutput(self, "RdsInstanceId", value=db.ref)


class RdsStackSecondary(Stack):
    """
    RDS Read Replica en us-west-2 :
    - Réplication asynchrone depuis le Primary us-east-1
    - Lecture seule (DR + décharge de lecture)
    - Promotable en Primary en cas de disaster régional
    """
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        db_subnet_1         = CfnParameter(self, "DbSubnet1Id", type="String").value_as_string
        db_subnet_2         = CfnParameter(self, "DbSubnet2Id", type="String").value_as_string
        db_sg_id            = CfnParameter(self, "DbSgId", type="String").value_as_string
        source_db_arn       = CfnParameter(self, "SourceDbArn", type="String").value_as_string

        # Subnet group us-west-2a + us-west-2b
        subnet_group = rds.CfnDBSubnetGroup(self, "RdsSubnetGroupSecondary",
            db_subnet_group_description="Subnet group RDS WordPress Read Replica",
            subnet_ids=[db_subnet_1, db_subnet_2],
            tags=[{"key": "Name", "value": "rds-subnet-group-secondary"}],
        )

        # Read Replica — pointe vers le Primary us-east-1
        db = rds.CfnDBInstance(self, "RdsReadReplica",
            db_instance_identifier="wordpress-rds-replica",
            db_instance_class="db.t3.micro",
            source_db_instance_identifier=source_db_arn,
            db_subnet_group_name=subnet_group.ref,
            vpc_security_groups=[db_sg_id],
            publicly_accessible=False,
            monitoring_interval=0,
            deletion_protection=False,
            tags=[{"key": "Name", "value": "wordpress-rds-replica"}],
        )

        CfnOutput(self, "ReplicaEndpoint", value=db.attr_endpoint_address)
        CfnOutput(self, "ReplicaPort", value=db.attr_endpoint_port)
